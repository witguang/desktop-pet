
"""
番茄钟定时器逻辑层（纯逻辑，不依赖 UI）。

UI 通过 tick() 每秒推进，并订阅状态变化回调。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from config import DEFAULT_BREAK_MINUTES, DEFAULT_FOCUS_MINUTES


class TimerMode(str, Enum):
    FOCUS = "focus"
    BREAK = "break"


class TimerStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"


Listener = Callable[[], None]


@dataclass
class PomodoroTimer:
    focus_minutes: int = DEFAULT_FOCUS_MINUTES
    break_minutes: int = DEFAULT_BREAK_MINUTES
    mode: TimerMode = TimerMode.FOCUS
    status: TimerStatus = TimerStatus.IDLE
    remaining_seconds: int = field(init=False)
    elapsed_seconds: int = 0
    task_title: str = ""
    task_id: str | None = None
    _listeners: list[Listener] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.remaining_seconds = self.focus_minutes * 60

    def add_listener(self, callback: Listener) -> None:
        self._listeners.append(callback)

    def _notify(self) -> None:
        for cb in self._listeners:
            try:
                cb()
            except Exception:
                pass

    def configure(
        self,
        *,
        focus_minutes: int | None = None,
        break_minutes: int | None = None,
        task_title: str | None = None,
        task_id: str | None = None,
    ) -> None:
        if focus_minutes is not None and focus_minutes > 0:
            self.focus_minutes = focus_minutes
        if break_minutes is not None and break_minutes > 0:
            self.break_minutes = break_minutes
        if task_title is not None:
            self.task_title = task_title
        if task_id is not None:
            self.task_id = task_id
        if self.status == TimerStatus.IDLE:
            self.remaining_seconds = self._planned_seconds()
            self.elapsed_seconds = 0
        self._notify()

    def _planned_seconds(self) -> int:
        if self.mode == TimerMode.FOCUS:
            return self.focus_minutes * 60
        return self.break_minutes * 60

    @property
    def planned_minutes(self) -> int:
        return self.focus_minutes if self.mode == TimerMode.FOCUS else self.break_minutes

    def start(self) -> None:
        if self.status == TimerStatus.FINISHED:
            self.reset()
        if self.status in (TimerStatus.IDLE, TimerStatus.PAUSED, TimerStatus.FINISHED):
            if self.status == TimerStatus.IDLE:
                self.remaining_seconds = self._planned_seconds()
                self.elapsed_seconds = 0
            self.status = TimerStatus.RUNNING
            self._notify()

    def pause(self) -> None:
        if self.status == TimerStatus.RUNNING:
            self.status = TimerStatus.PAUSED
            self._notify()

    def reset(self) -> None:
        self.status = TimerStatus.IDLE
        self.mode = TimerMode.FOCUS
        self.remaining_seconds = self.focus_minutes * 60
        self.elapsed_seconds = 0
        self._notify()

    def tick(self) -> bool:
        """
        推进 1 秒。返回 True 表示本轮刚刚结束。
        """
        if self.status != TimerStatus.RUNNING:
            return False
        if self.remaining_seconds <= 0:
            return False

        self.remaining_seconds -= 1
        self.elapsed_seconds += 1
        finished = self.remaining_seconds <= 0
        if finished:
            self.remaining_seconds = 0
            self.status = TimerStatus.FINISHED
        self._notify()
        return finished

    def switch_to_break(self) -> None:
        self.mode = TimerMode.BREAK
        self.status = TimerStatus.IDLE
        self.remaining_seconds = self.break_minutes * 60
        self.elapsed_seconds = 0
        self._notify()

    def switch_to_focus(self) -> None:
        self.mode = TimerMode.FOCUS
        self.status = TimerStatus.IDLE
        self.remaining_seconds = self.focus_minutes * 60
        self.elapsed_seconds = 0
        self._notify()

    def format_remaining(self) -> str:
        m, s = divmod(max(0, self.remaining_seconds), 60)
        return f"{m:02d}:{s:02d}"

    def is_focus_running(self) -> bool:
        return self.mode == TimerMode.FOCUS and self.status == TimerStatus.RUNNING
