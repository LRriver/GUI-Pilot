"""Task parsing helpers.

The stable parsing implementation currently lives in `profiles.lite` to keep
the proven profile behavior unchanged. This module is the public home for
future reusable task parsers.
"""

from gui_pilot.profiles.lite import _extract_app_name, _extract_comment_text, _infer_search_keyword

__all__ = ["_extract_app_name", "_extract_comment_text", "_infer_search_keyword"]
