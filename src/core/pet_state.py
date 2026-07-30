"""
桌宠状态机：根据优先级决定当前展示形态。


优先级（高 → 低）：
  TIME_MACHINE > EAT / FLY > DRINK > FOCUS > HUNGRY > IDLE
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from config import PetState

StateListener = Callable[[str, str], None]  # (old, new)

# 临时动画/提醒期间不被 focus / hungry 抢占
_TEMPORARY_STATES = (
    PetState.EAT,
    PetState.FLY,
    PetState.TIME_MACHINE,
    PetState.DRINK,
    PetState.PREVIEW,
)


@dataclass
class PetStateMachine:
    """管理桌宠视觉状态，支持临时覆盖（吃东西、投递、时光机等）。"""

    _state: str = PetState.IDLE
    _focusing: bool = False
    _hungry: bool = False
    _listeners: list[StateListener] = field(default_factory=list)

    @property
    def state(self) -> str:
        return self._state

    def add_listener(self, callback: StateListener) -> None:
        self._listeners.append(callback)

    def _emit(self, old: str, new: str) -> None:
        for cb in self._listeners:
            try:
                cb(old, new)
            except Exception:
                pass

    def _set(self, new_state: str) -> None:
        if new_state == self._state:
            return
        old = self._state
        self._state = new_state
        self._emit(old, new_state)

    def recompute(self) -> None:
        """根据长期标志重算基础状态（不打断临时动画 / 锁定提醒）。"""
        if self._state in _TEMPORARY_STATES:
            return

        if self._focusing:
            self._set(PetState.FOCUS)
        elif self._hungry:
            self._set(PetState.HUNGRY)
        else:
            self._set(PetState.IDLE)

    def set_focusing(self, focusing: bool) -> None:
        self._focusing = focusing
        self.recompute()

    def set_hungry(self, hungry: bool) -> None:
        """饥饿 / 低愉悦（等单）共用 hungry 视觉位。"""
        self._hungry = hungry
        self.recompute()

    def enter_temporary(self, state: str) -> None:
        """进入临时状态（吃、投递飞行、时光机、喝水提醒）。"""
        self._set(state)

    def leave_temporary(self) -> None:
        """临时状态结束，回到基础状态（始终通知 UI，避免仍停在 fly/eat 静态图）。"""
        if self._focusing:
            target = PetState.FOCUS
        elif self._hungry:
            target = PetState.HUNGRY
        else:
            target = PetState.IDLE
        old = self._state
        self._state = target
        # 即使 target 与强制写入后相同，也要从 FLY/EAT 等视觉态刷新到 idle
        self._emit(old, target)
