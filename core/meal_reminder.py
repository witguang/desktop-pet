"""
用餐提醒：按配置的固定时刻触发（早餐 / 午餐 / 晚餐 / 宵夜）。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime

from config import MEAL_REMINDERS

Listener = Callable[[str, str], None]  # (time_str, period_label)


@dataclass
class MealReminder:
    """每天每个时刻只提醒一次，跨日自动清空。"""

    schedule: list[tuple[str, str]] = field(default_factory=lambda: list(MEAL_REMINDERS))
    _fired_today: set[str] = field(default_factory=set)
    _current_day: str = field(default_factory=lambda: date.today().isoformat())
    _listeners: list[Listener] = field(default_factory=list)

    def add_listener(self, callback: Listener) -> None:
        self._listeners.append(callback)

    def set_schedule(self, schedule: list[tuple[str, str]]) -> None:
        self.schedule = list(schedule)

    def _reset_if_new_day(self) -> None:
        today = date.today().isoformat()
        if today != self._current_day:
            self._current_day = today
            self._fired_today.clear()

    def check(self, now: datetime | None = None) -> list[tuple[str, str]]:
        self._reset_if_new_day()
        now = now or datetime.now()
        current = now.strftime("%H:%M")
        triggered: list[tuple[str, str]] = []
        for time_str, period in self.schedule:
            key = f"meal:{time_str}:{period}"
            if time_str == current and key not in self._fired_today:
                self._fired_today.add(key)
                triggered.append((time_str, period))
                for cb in self._listeners:
                    try:
                        cb(time_str, period)
                    except Exception:
                        pass
        return triggered

    def force_remind(self, period: str = "测试") -> None:
        for cb in self._listeners:
            try:
                cb(datetime.now().strftime("%H:%M"), period)
            except Exception:
                pass
