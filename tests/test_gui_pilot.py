import unittest
import contextlib
import io
import pathlib
import sys
import tempfile
import types
import zipfile
from unittest.mock import patch

from PIL import Image

from gui_pilot import ACTION_CLICK, ACTION_OPEN, AgentInput, GuiPilotAgent, GuiPilotConfig, UsageInfo
from gui_pilot.deep.arbiter import ActionArbiter
from gui_pilot.deep.critic import CandidateCritic
from gui_pilot.deep.cropper import VisualCropper
from gui_pilot.deep.planner import TaskPlanner
from gui_pilot.deep.sampler import ActionCandidate
from gui_pilot.parser import parse_vlm_output
from gui_pilot.profiles.lite import LiteAgent
from gui_pilot.schema import ACTION_COMPLETE, AgentOutput, BaseAgent, ConfigTamperError
from gui_pilot.task_parser import extract_app_name, extract_comment_text
from tools import check_submission


class GuiPilotSmokeTest(unittest.TestCase):
    def make_image(self):
        return Image.new("RGB", (1080, 2400), "white")

    def test_lite_profile_opens_named_app_without_vlm(self):
        agent = GuiPilotAgent(profile="lite")
        output = agent.act(AgentInput(instruction="打开爱奇艺", current_image=self.make_image(), step_count=1))
        self.assertEqual(output.action, ACTION_OPEN)
        self.assertEqual(output.parameters, {"app_name": "爱奇艺"})
        self.assertEqual(output.usage.total_tokens, 0)

    def test_deep_profile_opens_named_app_and_adds_trace(self):
        agent = GuiPilotAgent(config=GuiPilotConfig(profile="deep", candidate_count=2))
        output = agent.act(AgentInput(instruction="打开爱奇艺", current_image=self.make_image(), step_count=1))
        self.assertEqual(output.action, ACTION_OPEN)
        self.assertEqual(output.parameters, {"app_name": "爱奇艺"})
        self.assertIn("[DeepTrace]", output.raw_output)

    def test_unknown_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            GuiPilotAgent(profile="missing")

    def test_workflow_prior_flag_disables_lite_workflow_path(self):
        agent = GuiPilotAgent(config=GuiPilotConfig(profile="lite", enable_workflow_prior=False))
        input_data = AgentInput(
            instruction="打开爱奇艺的评论区，发布评论：真是太好看了",
            current_image=self.make_image(),
            step_count=2,
        )
        with patch.object(agent._impl, "_vlm_decide") as decide:
            decide.return_value = AgentOutput(
                action=ACTION_CLICK,
                parameters={"point": [111, 222]},
                raw_output="mock_vlm",
                usage=UsageInfo(input_tokens=1, output_tokens=1, total_tokens=2),
            )
            output = agent.act(input_data)

        self.assertEqual(output.action, ACTION_CLICK)
        self.assertEqual(output.parameters, {"point": [111, 222]})
        decide.assert_called_once()

    def test_deep_reflection_flag_disables_memory_write(self):
        agent = GuiPilotAgent(config=GuiPilotConfig(profile="deep", candidate_count=1, enable_reflection=False))
        output = agent.act(AgentInput(instruction="打开爱奇艺", current_image=self.make_image(), step_count=1))
        self.assertIn('"reflection_enabled": false', output.raw_output)
        self.assertEqual(agent._impl.memory.recent(), [])

    def test_invalid_type_history_does_not_trigger_completion_guard(self):
        agent = GuiPilotAgent(profile="lite")
        input_data = AgentInput(
            instruction="写一段评价",
            current_image=self.make_image(),
            step_count=3,
            history_actions=[
                {"step": 2, "action": "TYPE", "parameters": {"text": "这个商品质量很好值得推荐"}, "is_valid": False}
            ],
        )
        with patch.object(agent._impl, "_vlm_decide") as decide:
            decide.return_value = AgentOutput(action=ACTION_CLICK, parameters={"point": [500, 500]}, raw_output="fallback")
            output = agent.act(input_data)

        self.assertEqual(output.action, ACTION_CLICK)
        decide.assert_called_once()

    def test_base_agent_passes_safe_kwargs_and_rejects_config_tampering(self):
        captured = {}

        class FakeCompletions:
            def create(self, **kwargs):
                captured.update(kwargs)
                return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))])

        class FakeOpenAI:
            def __init__(self, **kwargs):
                captured["client"] = kwargs
                self.chat = types.SimpleNamespace(completions=FakeCompletions())

        class FakeAgent(BaseAgent):
            def act(self, input_data):
                raise NotImplementedError

        fake_module = types.SimpleNamespace(OpenAI=FakeOpenAI)
        with patch.dict(sys.modules, {"openai": fake_module}):
            agent = FakeAgent()
            agent._call_api([{"role": "user", "content": "hello"}], temperature=0, top_p=0.7)
            self.assertEqual(captured["temperature"], 0)
            self.assertEqual(captured["top_p"], 0.7)
            with self.assertRaises(ConfigTamperError):
                agent._call_api([], api_key="bad")
            agent._api_key = "tampered"
            with self.assertRaises(ConfigTamperError):
                agent._call_api([])

    def test_lite_parser_rejects_malformed_parameters_without_crashing(self):
        agent = LiteAgent()
        cases = [
            ('Thought: x\nAction: CLICK\nParameters: {"point": 5}', "打开爱奇艺"),
            ('Thought: x\nAction: CLICK\nParameters: {"point": "500,80"}', "打开爱奇艺"),
            ('Thought: x\nAction: CLICK\nParameters: {"point": ["x", "y"]}', "打开爱奇艺"),
            ('Thought: x\nAction: SCROLL\nParameters: {"start_point": [500], "end_point": [500, 300]}', "打开爱奇艺"),
            ('Thought: x\nAction: OPEN\nParameters: {"app_name": ""}', "做点什么"),
        ]
        for content, instruction in cases:
            with self.subTest(content=content):
                action, params = agent._parse_vlm_output(content, instruction)
                self.assertEqual(action, ACTION_COMPLETE)
                self.assertEqual(params, {})

    def test_public_parser_helpers_are_available(self):
        action, params = parse_vlm_output('Thought: x\nAction: CLICK\nParameters: {"point": [500, 80]}')
        self.assertEqual(action, ACTION_CLICK)
        self.assertEqual(params, {"point": [500, 80]})
        self.assertEqual(extract_app_name("打开爱奇艺"), "爱奇艺")
        self.assertEqual(extract_comment_text("发布评论：很好看"), "很好看")


class DeepComponentsTest(unittest.TestCase):
    def test_planner_extracts_search_and_comment_steps(self):
        plan = TaskPlanner().plan("在爱奇艺搜索狂飙并发布评论")
        names = [step.name for step in plan]
        self.assertIn("focus_search", names)
        self.assertIn("finish_or_submit", names)

    def test_cropper_returns_named_regions(self):
        image = Image.new("RGB", (1000, 2000), "white")
        regions = VisualCropper().propose_regions(image)
        self.assertEqual([region.name for region in regions], ["top_bar", "center_content", "bottom_bar", "right_actions"])
        self.assertEqual(regions[0].box, (0, 0, 1000, 360))

    def test_critic_and_arbiter_choose_higher_score(self):
        input_data = AgentInput(
            instruction="发布评论：很好看",
            current_image=Image.new("RGB", (1000, 2000), "white"),
            step_count=3,
            history_actions=[{"action": "TYPE", "parameters": {"text": "很好看"}, "is_valid": True}],
        )
        click = ActionCandidate(AgentOutput(action="CLICK", parameters={"point": [900, 920]}, raw_output="click"), "click")
        scroll = ActionCandidate(AgentOutput(action="SCROLL", parameters={"start_point": [500, 700], "end_point": [500, 300]}, raw_output="scroll"), "scroll")
        critic = CandidateCritic()
        reviewed = [critic.score(input_data, click), critic.score(input_data, scroll)]
        selected = ActionArbiter().choose(reviewed)
        self.assertEqual(selected.source, "click")

    def test_invalid_candidate_count_is_rejected(self):
        with self.assertRaises(ValueError):
            GuiPilotConfig(profile="deep", candidate_count=0)

    def test_deep_profile_reports_total_candidate_usage(self):
        agent = GuiPilotAgent(config=GuiPilotConfig(profile="deep", candidate_count=2))

        candidates = [
            ActionCandidate(
                AgentOutput(
                    action="CLICK",
                    parameters={"point": [500, 500]},
                    raw_output="first",
                    usage=UsageInfo(input_tokens=2, output_tokens=3, total_tokens=5),
                ),
                "first",
            ),
            ActionCandidate(
                AgentOutput(
                    action="CLICK",
                    parameters={"point": [800, 900]},
                    raw_output="second",
                    usage=UsageInfo(input_tokens=7, output_tokens=11, total_tokens=18),
                ),
                "second",
            ),
        ]
        agent._impl.sampler.sample = lambda input_data, count: candidates
        output = agent.act(AgentInput(instruction="点击确认", current_image=Image.new("RGB", (1000, 2000), "white"), step_count=2))
        self.assertEqual(output.usage.input_tokens, 9)
        self.assertEqual(output.usage.output_tokens, 14)
        self.assertEqual(output.usage.total_tokens, 23)


class SubmissionCheckerTest(unittest.TestCase):
    def make_bad_zip(self, zip_path: pathlib.Path) -> None:
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("doc/algorithm_design.md", "bad")
            zf.writestr("src/agent.py", "def broken(:\n")
            zf.writestr("src/agent_base.py", "class BaseAgent: pass\n")
            zf.writestr("src/requirements.txt", "not a valid requirement ===\n")

    def make_bad_action_zip(self, zip_path: pathlib.Path) -> None:
        agent_base = """
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class AgentInput:
    instruction: str
    current_image: Any
    step_count: int
    history_messages: List[Dict[str, Any]] = field(default_factory=list)
    history_actions: List[Dict[str, Any]] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentOutput:
    action: str
    parameters: Dict[str, Any]

class BaseAgent:
    pass
"""
        agent = """
from agent_base import AgentOutput

class Agent:
    def act(self, input_data):
        return AgentOutput(action="BAD", parameters={})
"""
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("doc/algorithm_design.md", "bad action")
            zf.writestr("src/agent.py", agent)
            zf.writestr("src/agent_base.py", agent_base)
            zf.writestr("src/requirements.txt", "pillow>=10.0.0\n")

    def run_checker(self, *args: str) -> int:
        with patch.object(sys, "argv", ["check_submission.py", *args]):
            with contextlib.redirect_stdout(io.StringIO()):
                return check_submission.main()

    def test_checker_validates_zip_contents_not_just_source_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = pathlib.Path(tmp) / "bad.zip"
            self.make_bad_zip(zip_path)
            code = self.run_checker(
                "--submission-dir",
                "examples/competition_submission",
                "--zip",
                str(zip_path),
            )
        self.assertEqual(code, 1)

    def test_checker_calls_agent_and_validates_action_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = pathlib.Path(tmp) / "bad_action.zip"
            self.make_bad_action_zip(zip_path)
            code = self.run_checker(
                "--submission-dir",
                "examples/competition_submission",
                "--zip",
                str(zip_path),
            )
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
