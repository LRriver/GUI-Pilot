"""Public package interface for GUI-Pilot."""

from gui_pilot.agent import GuiPilotAgent
from gui_pilot.config import GuiPilotConfig
from gui_pilot.schema import (
    ACTION_CLICK,
    ACTION_COMPLETE,
    ACTION_OPEN,
    ACTION_SCROLL,
    ACTION_TYPE,
    AgentInput,
    AgentOutput,
    BaseAgent,
    UsageInfo,
)

__all__ = [
    "GuiPilotAgent",
    "GuiPilotConfig",
    "AgentInput",
    "AgentOutput",
    "BaseAgent",
    "UsageInfo",
    "ACTION_CLICK",
    "ACTION_SCROLL",
    "ACTION_TYPE",
    "ACTION_OPEN",
    "ACTION_COMPLETE",
]
