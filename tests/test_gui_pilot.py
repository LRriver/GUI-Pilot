import unittest

from PIL import Image

from gui_pilot import ACTION_OPEN, AgentInput, GuiPilotAgent, GuiPilotConfig
from gui_pilot.deep.arbiter import ActionArbiter
from gui_pilot.deep.critic import CandidateCritic
from gui_pilot.deep.cropper import VisualCropper
from gui_pilot.deep.planner import TaskPlanner
from gui_pilot.deep.sampler import ActionCandidate
from gui_pilot.schema import AgentOutput


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


if __name__ == "__main__":
    unittest.main()
