"""
提醒会话：喝水 / 用餐等「锁定直到确认」引擎。

触发后宠物进入对应状态并保持，直到用户点击「已完成」。
同一时刻只允许一个活动会话；新触发可排队，确认后依次弹出。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


class ReminderKind(str, Enum):
    WATER = "water"
    MEAL = "meal"


# (kind, state, message, time_str, period)
StartListener = Callable[["ActiveReminder"], None]
CompleteListener = Callable[["ActiveReminder"], None]


@dataclass(frozen=True)
class ActiveReminder:
    kind: ReminderKind
    state: str
    message: str
    time_str: str = ""
    period: str = ""

    @property
    def title(self) -> str:
        if self.kind == ReminderKind.WATER:
            return "喝水提醒"
        if self.kind == ReminderKind.MEAL:
            return "用餐提醒"
        return "提醒"

    @property
    def complete_label(self) -> str:
        if self.kind == ReminderKind.WATER:
            return "已喝完 ✓"
        if self.kind == ReminderKind.MEAL:
            return "已用餐 ✓"
        return "已完成 ✓"


@dataclass
class ReminderSession:
    """锁定直到用户确认的提醒会话管理器。"""

    _active: ActiveReminder | None = None
    _queue: list[ActiveReminder] = field(default_factory=list)
    _on_start: list[StartListener] = field(default_factory=list)
    _on_complete: list[CompleteListener] = field(default_factory=list)

    @property
    def is_locked(self) -> bool:
        return self._active is not None

    @property
    def active(self) -> ActiveReminder | None:
        return self._active

    def add_start_listener(self, callback: StartListener) -> None:
        self._on_start.append(callback)

    def add_complete_listener(self, callback: CompleteListener) -> None:
        self._on_complete.append(callback)

    def start(
        self,
        kind: ReminderKind | str,
        state: str,
        message: str,
        *,
        time_str: str = "",
        period: str = "",
    ) -> ActiveReminder:
        """
        发起一次锁定提醒。

        若当前已有活动会话，则入队，返回排队项；
        否则立即激活并通知 start 监听器。
        """
        if isinstance(kind, str):
            kind = ReminderKind(kind)
        item = ActiveReminder(
            kind=kind,
            state=state,
            message=message,
            time_str=time_str,
            period=period,
        )
        if self._active is not None:
            self._queue.append(item)
            return item
        self._activate(item)
        return item

    def complete(self) -> ActiveReminder | None:
        """用户确认完成。清除锁定；若有排队则无缝激活下一个。"""
        if self._active is None:
            return None
        finished = self._active
        self._active = None
        nxt = self._queue.pop(0) if self._queue else None
        # 先占住锁，避免 complete 回调里误判为「已完全解锁」而闪回 idle
        if nxt is not None:
            self._active = nxt
        for cb in self._on_complete:
            try:
                cb(finished)
            except Exception:
                pass
        if nxt is not None:
            for cb in self._on_start:
                try:
                    cb(nxt)
                except Exception:
                    pass
        return finished

    def cancel_all(self) -> None:
        """强制清空活动会话与队列（角色切换 / 退出时用）。"""
        self._queue.clear()
        if self._active is not None:
            finished = self._active
            self._active = None
            for cb in self._on_complete:
                try:
                    cb(finished)
                except Exception:
                    pass

    def _activate(self, item: ActiveReminder) -> None:
        self._active = item
        for cb in self._on_start:
            try:
                cb(item)
            except Exception:
                pass
