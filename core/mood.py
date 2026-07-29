"""
心情 / 愉悦值：随时间下降，投递包裹后恢复。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from config import (
    MOOD_DECREASE_PER_TICK,
    MOOD_LOW_THRESHOLD,
    MOOD_MAX,
    MOOD_RESTORE_AMOUNT,
    MOOD_TICK_SECONDS,
)


Listener = Callable[[int, bool], None]  # (mood, is_low)


@dataclass
class MoodSystem:
    mood: int = MOOD_MAX
    tick_seconds: int = MOOD_TICK_SECONDS
    decrease_per_tick: int = MOOD_DECREASE_PER_TICK
    low_threshold: int = MOOD_LOW_THRESHOLD
    max_value: int = MOOD_MAX
    _seconds_accum: float = 0.0
    _listeners: list[Listener] = field(default_factory=list)

    def add_listener(self, callback: Listener) -> None:
        self._listeners.append(callback)

    def _notify(self) -> None:
        low = self.is_low
        for cb in self._listeners:
            try:
                cb(self.mood, low)
            except Exception:
                pass

    @property
    def is_low(self) -> bool:
        return self.mood <= self.low_threshold

    def advance(self, dt_seconds: float = 1.0) -> None:
        self._seconds_accum += dt_seconds
        changed = False
        while self._seconds_accum >= self.tick_seconds:
            self._seconds_accum -= self.tick_seconds
            old = self.mood
            self.mood = max(0, self.mood - self.decrease_per_tick)
            if self.mood != old:
                changed = True
        if changed:
            self._notify()

    def deliver_package(self, amount: int | None = None) -> int:
        """投递包裹：恢复愉悦值，返回实际增加值。"""
        before = self.mood
        add = MOOD_RESTORE_AMOUNT if amount is None else max(0, int(amount))
        self.mood = min(self.max_value, before + add)
        self._seconds_accum = 0.0
        gained = self.mood - before
        self._notify()
        return gained

    def restore_full(self) -> int:
        before = self.mood
        self.mood = self.max_value
        self._seconds_accum = 0.0
        self._notify()
        return self.mood - before

    def set_mood(self, value: int) -> None:
        self.mood = max(0, min(self.max_value, value))
        self._notify()
