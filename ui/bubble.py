
"""桌宠头顶气泡提示。"""
from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

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

        frame = tk.Frame(win, bg="#FFF8DC", highlightbackground="#333333", highlightthickness=2)
        frame.pack()
        label = tk.Label(
            frame,
            text=text,
            bg="#FFF8DC",
            fg="#222222",
            font=("Microsoft YaHei UI", 10),
            padx=10,
            pady=6,
            justify="left",
            wraplength=180,
        )
        label.pack()
        # 小三角
        tip = tk.Label(win, text="▼", bg=self.pet.transparent_color, fg="#FFF8DC", font=("Arial", 10))
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
