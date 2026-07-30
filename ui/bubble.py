
"""桌宠头顶气泡提示。"""
from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from ui.theme import Colors, Fonts

if TYPE_CHECKING:
    from ui.pet_window import PetWindow


class SpeechBubble:
    """附着在宠物窗口上方的简易气泡。"""

    def __init__(self, pet: PetWindow) -> None:
        self.pet = pet
        self._win: tk.Toplevel | None = None
        self._hide_job: str | None = None

    def show(self, text: str, duration_ms: int = 5000) -> None:
        self.hide()
        parent = self.pet.root
        win = tk.Toplevel(parent)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        try:
            win.attributes("-transparentcolor", self.pet.transparent_color)
        except tk.TclError:
            pass
        win.configure(bg=self.pet.transparent_color)

        # 气泡主体：白底 + 主色细边框 + 圆角通过内边距模拟
        frame = tk.Frame(
            win,
            bg=Colors.BG_CARD,
            highlightbackground=Colors.PRIMARY,
            highlightthickness=1,
            bd=0,
        )
        frame.pack(padx=2, pady=2)
        label = tk.Label(
            frame,
            text=text,
            bg=Colors.BG_CARD,
            fg=Colors.TEXT_MAIN,
            font=Fonts.body(),
            padx=14,
            pady=10,
            justify="left",
            wraplength=200,
        )
        label.pack()
        # 小三角（与气泡同色的倒三角）
        tip = tk.Label(
            win,
            text="▼",
            bg=self.pet.transparent_color,
            fg=Colors.BG_CARD,
            font=("Arial", 10),
        )
        tip.pack()

        self._win = win
        self._reposition()
        if duration_ms > 0:
            self._hide_job = parent.after(duration_ms, self.hide)

    def _reposition(self) -> None:
        if not self._win:
            return
        self._win.update_idletasks()
        px = self.pet.root.winfo_x()
        py = self.pet.root.winfo_y()
        bw = self._win.winfo_reqwidth()
        bh = self._win.winfo_reqheight()
        pw = self.pet.root.winfo_width()
        x = px + (pw - bw) // 2
        y = py - bh + 8
        self._win.geometry(f"+{x}+{y}")

    def follow_pet(self) -> None:
        self._reposition()

    def hide(self) -> None:
        if self._hide_job:
            try:
                self.pet.root.after_cancel(self._hide_job)
            except Exception:
                pass
            self._hide_job = None
        if self._win is not None:
            try:
                self._win.destroy()
            except tk.TclError:
                pass
            self._win = None
