"""Lightweight planner used by the deep profile."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List


@dataclass
class PlanStep:
    """A coarse subgoal for GUI execution."""

    name: str
    status: str = "pending"


class TaskPlanner:
    """Create coarse task plans from natural-language instructions."""

    def plan(self, instruction: str) -> List[PlanStep]:
        steps: List[PlanStep] = []
        if re.search(r"搜索|查找|查询", instruction):
            steps.extend([PlanStep("focus_search"), PlanStep("type_query"), PlanStep("confirm_search")])
        if re.search(r"播放|打开.*视频|第\s*[一二三四五六七八九十\d]+\s*[集期]", instruction):
            steps.append(PlanStep("open_content"))
        if re.search(r"评论|留言|回复|评价|晒单|追评|点评", instruction):
            steps.extend([PlanStep("open_text_entry"), PlanStep("type_text"), PlanStep("finish_or_submit")])
        if re.search(r"购买|下单|外卖", instruction):
            steps.extend([PlanStep("select_store_or_item"), PlanStep("add_to_cart"), PlanStep("stop_before_payment")])
        if re.search(r"打车|航班|酒店|路线|导航", instruction):
            steps.extend([PlanStep("fill_form"), PlanStep("select_result")])
        if not steps:
            steps.append(PlanStep("inspect_and_act"))
        return steps
