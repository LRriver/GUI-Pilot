"""Candidate generation for the deep profile."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import List, Set, Tuple

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
        count = int(count)
        if count < 1:
            raise ValueError("candidate count must be >= 1")
        candidates: List[ActionCandidate] = []
        seen: Set[Tuple[str, str]] = set()
        for index in range(count):
            agent = self.agent_factory()
            output = agent.act(input_data)
            signature = (output.action, json.dumps(output.parameters, sort_keys=True, ensure_ascii=False))
            if signature in seen:
                continue
            seen.add(signature)
            candidates.append(ActionCandidate(output=output, source=f"sample_{index + 1}"))
            if output.usage and output.usage.total_tokens == 0:
                break
        return candidates
