"""Post-processing guard documentation module.

Text-input completion guards and submit guards are implemented by
`profiles.lite.LiteAgent` and reused by the deep profile.
"""

from gui_pilot.profiles.lite import REVIEW_TEXT_RE, SUBMIT_RE

__all__ = ["REVIEW_TEXT_RE", "SUBMIT_RE"]
