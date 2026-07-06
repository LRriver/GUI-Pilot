"""Candidate arbitration for the deep profile."""

from __future__ import annotations

from typing import Iterable

from gui_pilot.deep.sampler import ActionCandidate


class ActionArbiter:
    """Select the highest-scoring candidate while preserving deterministic ties."""

    def choose(self, candidates: Iterable[ActionCandidate]) -> ActionCandidate:
        candidate_list = list(candidates)
        if not candidate_list:
            raise ValueError("no action candidates to arbitrate")
        return max(enumerate(candidate_list), key=lambda item: (item[1].score, -item[0]))[1]
