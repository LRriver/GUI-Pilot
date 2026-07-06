"""Configuration objects for GUI-Pilot profiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ProfileName = Literal["lite", "deep"]


@dataclass
class GuiPilotConfig:
    """Runtime configuration for `GuiPilotAgent`.

    The profile controls the top-level decision pipeline. Extra knobs are kept
    conservative so the public API stays stable while the internals evolve.
    """

    profile: ProfileName = "lite"
    candidate_count: int = 3
    enable_cropping: bool = True
    enable_reflection: bool = True
    enable_workflow_prior: bool = True


def normalize_profile(profile: str) -> ProfileName:
    """Validate and normalize a profile name."""
    normalized = profile.strip().lower()
    if normalized not in {"lite", "deep"}:
        raise ValueError(f"unknown GUI-Pilot profile: {profile!r}; expected 'lite' or 'deep'")
    return normalized  # type: ignore[return-value]
