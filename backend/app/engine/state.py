"""Short-term memory for detectors: sliding windows and cooldowns.

In process and bounded. Losing it on restart costs at most one window of
history, which is acceptable for rate-style detection; nothing here is a
record of truth (that's the database).
"""

from __future__ import annotations

from collections import OrderedDict, deque
from datetime import datetime, timedelta

MAX_KEYS = 50_000


class WindowStore:
    def __init__(self, max_keys: int = MAX_KEYS) -> None:
        self._windows: OrderedDict[str, deque[tuple[datetime, str]]] = OrderedDict()
        self._cooldowns: OrderedDict[str, datetime] = OrderedDict()
        self._max_keys = max_keys

    def _touch(self, store: OrderedDict, key: str) -> None:
        store.move_to_end(key)
        while len(store) > self._max_keys:
            store.popitem(last=False)

    def add(self, key: str, at: datetime, window_seconds: float, value: str = "") -> list[tuple[datetime, str]]:
        """Record a hit and return everything still inside the window (including it)."""
        window = self._windows.setdefault(key, deque())
        window.append((at, value))
        cutoff = at - timedelta(seconds=window_seconds)
        while window and window[0][0] <= cutoff:
            window.popleft()
        self._touch(self._windows, key)
        return list(window)

    def clear(self, key: str) -> None:
        self._windows.pop(key, None)

    def cooling_down(self, key: str, at: datetime) -> bool:
        until = self._cooldowns.get(key)
        return until is not None and at < until

    def start_cooldown(self, key: str, at: datetime, seconds: float) -> None:
        self._cooldowns[key] = at + timedelta(seconds=seconds)
        self._touch(self._cooldowns, key)
