"""VLM adapter boundary.

`BaseAgent` in `gui_pilot.schema` provides the OpenAI-compatible API call used
by both public profiles. This module exists as the extension point for custom
model clients.
"""

from gui_pilot.schema import BaseAgent, UsageInfo

__all__ = ["BaseAgent", "UsageInfo"]
