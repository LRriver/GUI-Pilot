"""Candidate generation for the deep profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from gui_pilot.schema import AgentInput, AgentOutput


@dataclass
class ActionCandidate:
    """A sampled GUI action candidate."""

    output: AgentOutput
    source: str
    score: float = 0.0
    note: str = ""


class CandidateSampler:
    """Generate multiple candidates using a provided agent factory."""

    def __init__(self, agent_factory):
        self.agent_factory = agent_factory

    def sample(self, input_data: AgentInput, count: int) -> List[ActionCandidate]:
        count = max(1, int(count))
        candidates: List[ActionCandidate] = []
        for index in range(count):
            agent = self.agent_factory()
            output = agent.act(input_data)
            candidates.append(ActionCandidate(output=output, source=f"sample_{index + 1}"))
        return candidates
