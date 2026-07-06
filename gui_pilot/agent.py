"""Main public Agent facade."""

from __future__ import annotations

from typing import Optional

from gui_pilot.config import GuiPilotConfig, normalize_profile
from gui_pilot.schema import AgentInput, AgentOutput, BaseAgent


class GuiPilotAgent(BaseAgent):
    """Profile-selecting facade for GUI-Pilot.

    Parameters
    ----------
    profile:
        `lite` is the default stable profile. `deep` enables the high-budget
        planning and review pipeline.
    config:
        Optional explicit `GuiPilotConfig`. When provided, it overrides the
        `profile` argument.
    """

    def __init__(self, profile: str = "lite", config: Optional[GuiPilotConfig] = None):
        self.gui_config = config or GuiPilotConfig(profile=normalize_profile(profile))
        super().__init__()

    def _initialize(self):
        if self.gui_config.profile == "lite":
            from gui_pilot.profiles.lite import LiteAgent

            self._impl = LiteAgent()
        elif self.gui_config.profile == "deep":
            from gui_pilot.profiles.deep import DeepAgent

            self._impl = DeepAgent(self.gui_config)
        else:
            raise ValueError(f"unsupported profile: {self.gui_config.profile}")

    def reset(self):
        self._impl.reset()

    def act(self, input_data: AgentInput) -> AgentOutput:
        return self._impl.act(input_data)
