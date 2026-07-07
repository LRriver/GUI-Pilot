"""High-budget GUI Pilot profile."""

from __future__ import annotations

import json

from gui_pilot.config import GuiPilotConfig
from gui_pilot.deep.arbiter import ActionArbiter
from gui_pilot.deep.critic import CandidateCritic
from gui_pilot.deep.cropper import VisualCropper
from gui_pilot.deep.memory import ReflectionMemory
from gui_pilot.deep.planner import TaskPlanner
from gui_pilot.deep.sampler import CandidateSampler
from gui_pilot.profiles.lite import LiteAgent
from gui_pilot.schema import AgentInput, AgentOutput, BaseAgent


class DeepAgent(BaseAgent):
    """Research-oriented profile with planning, sampling, review, and memory."""

    def __init__(self, config: GuiPilotConfig):
        self.gui_config = config
        super().__init__()

    def _initialize(self):
        self.planner = TaskPlanner()
        self.cropper = VisualCropper()
        self.critic = CandidateCritic()
        self.arbiter = ActionArbiter()
        self.memory = ReflectionMemory()
        self.sampler = CandidateSampler(lambda: LiteAgent(enable_workflow_prior=self.gui_config.enable_workflow_prior))

    def reset(self):
        self.memory.clear()

    def act(self, input_data: AgentInput) -> AgentOutput:
        plan = self.planner.plan(input_data.instruction)
        regions = self.cropper.propose_regions(input_data.current_image) if self.gui_config.enable_cropping else []
        candidates = self.sampler.sample(input_data, self.gui_config.candidate_count)
        reviewed = [self.critic.score(input_data, candidate) for candidate in candidates]
        selected = self.arbiter.choose(reviewed)

        if self.gui_config.enable_reflection:
            self.memory.add(
                step=str(input_data.step_count),
                plan=">".join(step.name for step in plan[:6]),
                regions=",".join(region.name for region in regions[:4]),
                selected=selected.source,
                action=selected.output.action,
            )

        output = selected.output
        trace = {
            "profile": "deep",
            "plan": [step.name for step in plan],
            "regions": [region.name for region in regions],
            "candidates": [
                {
                    "source": candidate.source,
                    "action": candidate.output.action,
                    "parameters": candidate.output.parameters,
                    "score": candidate.score,
                    "note": candidate.note,
                }
                for candidate in reviewed
            ],
            "selected": selected.source,
            "reflection_enabled": self.gui_config.enable_reflection,
        }
        output.raw_output = f"{output.raw_output}\n\n[DeepTrace] {json.dumps(trace, ensure_ascii=False)}"
        return output
