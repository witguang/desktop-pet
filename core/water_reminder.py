
"""
喝水提醒：按配置的固定时刻触发。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime

from config import WATER_REMINDERS


Listener = Callable[[str, str], None]  # (time_str, period_label)


@dataclass
class WaterReminder:
    """每天每个时刻只提醒一次，跨日自动清空。"""

    schedule: list[tuple[str, str]] = field(default_factory=lambda: list(WATER_REMINDERS))
    _fired_today: set[str] = field(default_factory=set)
    _current_day: str = field(default_factory=lambda: date.today().isoformat())
    _listeners: list[Listener] = field(default_factory=list)

    def add_listener(self, callback: Listener) -> None:
        self._listeners.append(callback)

    def _reset_if_new_day(self) -> None:
        today = date.today().isoformat()
        if today != self._current_day:
            self._current_day = today
            self._fired_today.clear()

    def check(self, now: datetime | None = None) -> list[tuple[str, str]]:
        """
        检查是否有应触发的提醒。返回刚触发的 (HH:MM, 时段) 列表。
        """
        self._reset_if_new_day()
        now = now or datetime.now()
        current = now.strftime("%H:%M")
        triggered: list[tuple[str, str]] = []
        for time_str, period in self.schedule:
            if time_str == current and time_str not in self._fired_today:
                self._fired_today.add(time_str)
                triggered.append((time_str, period))
                for cb in self._listeners:
                    try:
                        cb(time_str, period)
                    except Exception:
                        pass
        return triggered

    def force_remind(self, period: str = "测试") -> None:
        """调试用：立即触发一次提醒。"""
        for cb in self._listeners:
            try:
                cb(datetime.now().strftime("%H:%M"), period)
            except Exception:
                pass
