"""Reflection memory for deep-profile traces."""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List


class ReflectionMemory:
    """Small bounded memory for high-level plans and selected actions."""

    def __init__(self, max_items: int = 20):
        self._items: Deque[Dict[str, str]] = deque(maxlen=max_items)

    def add(self, **item: str) -> None:
        self._items.append({key: str(value) for key, value in item.items()})

    def clear(self) -> None:
        self._items.clear()

    def recent(self) -> List[Dict[str, str]]:
        return list(self._items)
