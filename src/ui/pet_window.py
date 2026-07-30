"""
无边框、透明、置顶、可拖动的桌宠主窗口。

尺寸与透明色来自当前 CharacterPack，支持运行时换角。
动作态：播放 motion GIF 两轮，再定格到对应 still PNG。
"""
from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from config import PetState
from utils.asset_loader import AssetLoader, AnimationFrames


class PetWindow:
    def __init__(
        self,
        root: tk.Tk,
        loader: AssetLoader,
        on_right_click: Callable[[tk.Event], None] | None = None,
        on_double_click: Callable[[tk.Event], None] | None = None,
    ) -> None:
        self.root = root
        self.loader = loader
        self.on_right_click = on_right_click
        self.on_double_click = on_double_click

        self._anim: AnimationFrames | None = None
        self._frame_index = 0
        self._anim_job: str | None = None
        self._current_state = PetState.IDLE
        self._drag_ox = 0
        self._drag_oy = 0
        self._dragging = False

        # GIF → PNG 播放控制
        self._loops_remaining = 0
        self._loop_total_frames = 0
        self._frames_played_in_loop = 0
        self._settled = True
        self._on_settle: Callable[[], None] | None = None
        self._topmost_job: str | None = None

        self._setup_window()
        self._build_widgets()
        self.set_state(PetState.IDLE)
        self._place_default()

    @property
    def transparent_color(self) -> str:
        return self.loader.transparent_color

    def _setup_window(self) -> None:
        self.root.title("Desktop Pet")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self._apply_transparency()
        w, h = self.loader.pet_size
        self.root.geometry(f"{w}x{h}")
        self._schedule_topmost()

    def _apply_transparency(self) -> None:
        color = self.transparent_color
        try:
            self.root.attributes("-transparentcolor", color)
        except tk.TclError:
            try:
                self.root.attributes("-alpha", 0.95)
            except tk.TclError:
                pass
        self.root.configure(bg=color)

    def _schedule_topmost(self, interval_ms: int = 5000) -> None:
        """定期刷新置顶状态，防止被其他窗口覆盖后沉下去。"""
        self.cancel_topmost_job()
        self._topmost_job = self.root.after(interval_ms, self._enforce_topmost)

    def _enforce_topmost(self) -> None:
        """强制置顶并提到最前，然后重新调度。"""
        self._topmost_job = None
        try:
            self.root.attributes("-topmost", True)
            self.root.lift()
        except tk.TclError:
            pass
        self._schedule_topmost()

    def cancel_topmost_job(self) -> None:
        if self._topmost_job:
            try:
                self.root.after_cancel(self._topmost_job)
            except Exception:
                pass
            self._topmost_job = None

    def _build_widgets(self) -> None:
        self.label = tk.Label(self.root, bg=self.transparent_color, bd=0, cursor="hand2")
        self.label.pack(fill="both", expand=True)
        self.label.bind("<ButtonPress-1>", self._on_press)
        self.label.bind("<B1-Motion>", self._on_drag)
        self.label.bind("<ButtonRelease-1>", self._on_release)
        self.label.bind("<Button-3>", self._on_right)
        self.label.bind("<Double-Button-1>", self._on_double)

    def _place_default(self) -> None:
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = self.loader.pet_size
        x = sw - w - 40
        y = sh - h - 80
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def apply_character(self) -> None:
        """切换角色后刷新窗口尺寸、透明色与当前动画。"""
        self._apply_transparency()
        self.label.configure(bg=self.transparent_color)
        w, h = self.loader.pet_size
        x, y = self.root.winfo_x(), self.root.winfo_y()
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.set_state(self._current_state)
        self._schedule_topmost()

    def _on_press(self, event: tk.Event) -> None:
        self._drag_ox = event.x_root - self.root.winfo_x()
        self._drag_oy = event.y_root - self.root.winfo_y()
        self._dragging = True

    def _on_drag(self, event: tk.Event) -> None:
        if not self._dragging:
            return
        x = event.x_root - self._drag_ox
        y = event.y_root - self._drag_oy
        self.root.geometry(f"+{x}+{y}")

    def _on_release(self, _event: tk.Event) -> None:
        self._dragging = False

    def _on_right(self, event: tk.Event) -> None:
        if self.on_right_click:
            self.on_right_click(event)

    def _on_double(self, event: tk.Event) -> None:
        if self.on_double_click:
            self.on_double_click(event)

    def _cancel_anim_job(self) -> None:
        if self._anim_job:
            try:
                self.root.after_cancel(self._anim_job)
            except Exception:
                pass
            self._anim_job = None

    def set_state(
        self,
        state: str,
        *,
        play_loops: int = 2,
        on_settle: Callable[[], None] | None = None,
    ) -> None:
        """
        切换形态。

        - 若有 motion GIF：播放 play_loops 轮后定格 still PNG
        - 若仅有静态图：直接显示 still，轻微呼吸循环
        - idle / hungry 等长期态：still 循环（或短 idle gif 循环）
        """
        self._current_state = state
        self._on_settle = on_settle
        self._cancel_anim_job()

        motion = self.loader.get_motion(state)
        still = self.loader.get_still(state)

        # 长期基础态：优先 still；若只有 gif 则循环 gif
        long_lived = state in (PetState.IDLE, PetState.FOCUS, PetState.HUNGRY)
        if long_lived:
            if still is not None and not still.is_motion:
                self._anim = still
                self._loops_remaining = 0
                self._settled = True
                self._frame_index = 0
                self._play_frame()
                return
            # 仅有 motion：无限循环
            self._anim = motion or still
            self._loops_remaining = 0  # 0 + is_motion → infinite below
            self._settled = True
            self._frame_index = 0
            self._loop_total_frames = len(self._anim) if self._anim else 0
            self._frames_played_in_loop = 0
            self._play_frame()
            return

        # 动作态：GIF × play_loops → still
        if motion is not None and motion.is_motion and play_loops > 0:
            self._anim = motion
            self._loops_remaining = play_loops
            self._loop_total_frames = len(motion)
            self._frames_played_in_loop = 0
            self._settled = False
            self._frame_index = 0
            self._play_frame()
            return

        # 无 motion：直接 still
        self._anim = still or motion
        self._loops_remaining = 0
        self._settled = True
        self._frame_index = 0
        self._play_frame()
        if on_settle:
            try:
                on_settle()
            except Exception:
                pass

    def _settle_to_still(self) -> None:
        state = self._current_state
        still = self.loader.get_still(state)
        if still is None:
            still = self.loader.get_still(PetState.IDLE)
        self._anim = still
        self._settled = True
        self._loops_remaining = 0
        self._frame_index = 0
        self._frames_played_in_loop = 0
        self._play_frame()
        cb = self._on_settle
        self._on_settle = None
        if cb:
            try:
                cb()
            except Exception:
                pass

    def _play_frame(self) -> None:
        self._cancel_anim_job()
        if not self._anim:
            return

        n = len(self._anim)
        frame = self._anim.frames[self._frame_index % n]
        delay = self._anim.delays_ms[self._frame_index % n]
        self.label.configure(image=frame)
        self.label.image = frame  # type: ignore[attr-defined]
        self._frame_index += 1

        # 已定格静态：双帧呼吸或单帧慢闪
        if self._settled:
            self._anim_job = self.root.after(delay, self._play_frame)
            return

        # motion 播放中：计一轮
        self._frames_played_in_loop += 1
        if self._frames_played_in_loop >= self._loop_total_frames:
            self._frames_played_in_loop = 0
            self._loops_remaining -= 1
            if self._loops_remaining <= 0:
                self._settle_to_still()
                return
            self._frame_index = 0

        self._anim_job = self.root.after(delay, self._play_frame)

    def bbox(self) -> tuple[int, int, int, int]:
        return (
            self.root.winfo_x(),
            self.root.winfo_y(),
            self.root.winfo_width(),
            self.root.winfo_height(),
        )

    def center(self) -> tuple[int, int]:
        x, y, w, h = self.bbox()
        return x + w // 2, y + h // 2
