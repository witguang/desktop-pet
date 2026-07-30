"""
饥饿值系统：随时间增长，喂食后重置。
"""
from __future__ import annotations


from collections.abc import Callable
from dataclasses import dataclass, field


from config import (
    HUNGER_INCREASE_PER_TICK,
    HUNGER_MAX,
    HUNGER_RESET_ON_FEED,
    HUNGER_THRESHOLD,
    HUNGER_TICK_SECONDS,
)



Listener = Callable[[int, bool], None]  # (hunger, is_hungry)



@dataclass
class HungerSystem:
    hunger: int = 0
    tick_seconds: int = HUNGER_TICK_SECONDS
    increase_per_tick: int = HUNGER_INCREASE_PER_TICK
    threshold: int = HUNGER_THRESHOLD
    max_value: int = HUNGER_MAX
    _seconds_accum: float = 0.0
    _listeners: list[Listener] = field(default_factory=list)


    def add_listener(self, callback: Listener) -> None:
        self._listeners.append(callback)


    def _notify(self) -> None:
        hungry = self.is_hungry
        for cb in self._listeners:
            try:
                cb(self.hunger, hungry)
            except Exception:
                pass


    @property
    def is_hungry(self) -> bool:
        return self.hunger >= self.threshold


    def advance(self, dt_seconds: float = 1.0) -> None:
        """由主循环每秒调用。"""
        self._seconds_accum += dt_seconds
        changed = False
        while self._seconds_accum >= self.tick_seconds:
            self._seconds_accum -= self.tick_seconds
            old = self.hunger
            self.hunger = min(self.max_value, self.hunger + self.increase_per_tick)
            if self.hunger != old:
                changed = True
        if changed:
            self._notify()


    def feed(self) -> None:
        self.hunger = HUNGER_RESET_ON_FEED
        self._seconds_accum = 0.0
        self._notify()


    def set_hunger(self, value: int) -> None:
        self.hunger = max(0, min(self.max_value, value))
        self._notify()
