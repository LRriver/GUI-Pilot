"""Model-output parsing utilities.

The production parser is currently implemented on `LiteAgent` because it is
state-aware. This module marks the public parser boundary for future extraction.
"""

from gui_pilot.profiles.lite import LiteAgent

__all__ = ["LiteAgent"]
