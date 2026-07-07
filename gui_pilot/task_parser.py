"""Task parsing helpers."""

from gui_pilot.profiles.lite import _extract_app_name, _extract_comment_text, _infer_search_keyword


def extract_app_name(instruction: str):
    """Extract a known app name from an instruction."""
    return _extract_app_name(instruction)


def extract_comment_text(instruction: str) -> str:
    """Extract explicit comment/review text from an instruction."""
    return _extract_comment_text(instruction)


def infer_search_keyword(instruction: str, app_name: str) -> str:
    """Infer the main search keyword for common app workflows."""
    return _infer_search_keyword(instruction, app_name)


__all__ = [
    "extract_app_name",
    "extract_comment_text",
    "infer_search_keyword",
    "_extract_app_name",
    "_extract_comment_text",
    "_infer_search_keyword",
]
