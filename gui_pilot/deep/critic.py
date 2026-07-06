"""Heuristic reviewer for deep-profile action candidates."""

from __future__ import annotations

import re

from gui_pilot.deep.sampler import ActionCandidate
from gui_pilot.schema import ACTION_CLICK, ACTION_COMPLETE, ACTION_SCROLL, ACTION_TYPE, AgentInput


class CandidateCritic:
    """Score candidates using task-stage and action-risk heuristics."""

    def score(self, input_data: AgentInput, candidate: ActionCandidate) -> ActionCandidate:
        output = candidate.output
        score = 1.0
        instruction = input_data.instruction
        last_action = ""
        if input_data.history_actions:
            last_action = str(input_data.history_actions[-1].get("action") or "")

        if output.action == ACTION_CLICK:
            point = output.parameters.get("point") or [500, 500]
            x, y = point
            if 0 <= x <= 1000 and 0 <= y <= 1000:
                score += 0.2
            if re.search(r"搜索|发送|提交|发布|确认", instruction) and (y <= 180 or y >= 850):
                score += 0.2
        elif output.action == ACTION_TYPE:
            if last_action == "CLICK":
                score += 0.2
            if last_action == "TYPE":
                score -= 0.5
        elif output.action == ACTION_COMPLETE:
            if last_action == "TYPE" and not re.search(r"发布|发送|提交|下单|支付", instruction):
                score += 0.4
            elif len(input_data.history_actions or []) <= 1:
                score -= 0.6
        elif output.action == ACTION_SCROLL:
            if last_action == "TYPE":
                score -= 0.4

        candidate.score = score
        candidate.note = f"heuristic_score={score:.2f}"
        return candidate
