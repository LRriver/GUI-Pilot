"""Model-output parsing utilities."""

from gui_pilot.profiles.lite import LiteAgent


def parse_vlm_output(content: str, instruction: str = ""):
    """Parse a VLM response into `(action, parameters)` using the stable parser."""
    return LiteAgent()._parse_vlm_output(content, instruction)


__all__ = ["parse_vlm_output", "LiteAgent"]
