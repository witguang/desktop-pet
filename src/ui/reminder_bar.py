"""
提醒确认条：附着在桌宠附近的「已完成」浮动条。

置顶、无边框；随宠物移动；点击按钮才关闭。
"""
from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import TYPE_CHECKING

from ui.theme import Colors, Fonts

if TYPE_CHECKING:
    from core.reminder_session import ActiveReminder
    from ui.pet_window import PetWindow


class ReminderBar:
    """锁定提醒期间显示的确认条。"""

    def __init__(
        self,
        pet: PetWindow,
        on_complete: Callable[[], None],
    ) -> None:
        self.pet = pet
        self.on_complete = on_complete
        self._win: tk.Toplevel | None = None
        self._msg_var = tk.StringVar()
        self._btn_var = tk.StringVar(value="已完成 ✓")
        self._title_var = tk.StringVar(value="提醒")

    @property
    def visible(self) -> bool:
        return self._win is not None and self._win.winfo_exists()

    def show(self, reminder: ActiveReminder) -> None:
        self.hide()
        parent = self.pet.root
        win = tk.Toplevel(parent)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=Colors.PRIMARY)
        # 不抢焦点，避免打断输入；但按钮仍可点
        try:
            win.attributes("-toolwindow", True)
        except tk.TclError:
            pass

        self._title_var.set(reminder.title)
        self._msg_var.set(reminder.message)
        self._btn_var.set(reminder.complete_label)

        outer = tk.Frame(win, bg=Colors.PRIMARY, padx=2, pady=2)
        outer.pack(fill="both", expand=True)
        card = tk.Frame(outer, bg=Colors.BG_CARD, padx=14, pady=12)
        card.pack(fill="both", expand=True)

        tk.Label(
            card,
            textvariable=self._title_var,
            bg=Colors.BG_CARD,
            fg=Colors.PRIMARY,
            font=Fonts.heading(bold=True),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            card,
            textvariable=self._msg_var,
            bg=Colors.BG_CARD,
            fg=Colors.TEXT_MAIN,
            font=Fonts.body(),
            justify="left",
            wraplength=240,
            anchor="w",
        ).pack(fill="x", pady=(6, 10))

        btn = tk.Button(
            card,
            textvariable=self._btn_var,
            font=Fonts.body(bold=True),
            bg=Colors.SUCCESS,
            fg=Colors.TEXT_ON_PRIMARY,
            activebackground="#43A047",
            activeforeground=Colors.TEXT_ON_PRIMARY,
            relief="flat",
            padx=16,
            pady=7,
            cursor="hand2",
            command=self._click_complete,
        )
        btn.pack(fill="x")

        # 轻微拖动整条（可选）
        for w in (outer, card):
            w.bind("<ButtonPress-1>", self._on_press)
            w.bind("<B1-Motion>", self._on_drag)

        self._win = win
        self._drag_ox = 0
        self._drag_oy = 0
        self._manual_offset: tuple[int, int] | None = None
        self._reposition()

    def _on_press(self, event: tk.Event) -> None:
        if not self._win:
            return
        self._drag_ox = event.x_root - self._win.winfo_x()
        self._drag_oy = event.y_root - self._win.winfo_y()

    def _on_drag(self, event: tk.Event) -> None:
        if not self._win:
            return
        x = event.x_root - self._drag_ox
        y = event.y_root - self._drag_oy
        self._win.geometry(f"+{x}+{y}")
        # 记录相对宠物的偏移，follow 时保持
        px = self.pet.root.winfo_x()
        py = self.pet.root.winfo_y()
        self._manual_offset = (x - px, y - py)

    def _click_complete(self) -> None:
        # 先回调再 hide，由 app 统一收尾；hide 也可幂等
        try:
            self.on_complete()
        except Exception:
            self.hide()

    def _reposition(self) -> None:
        if not self._win:
            return
        try:
            self._win.update_idletasks()
            px = self.pet.root.winfo_x()
            py = self.pet.root.winfo_y()
            pw = self.pet.root.winfo_width()
            ph = self.pet.root.winfo_height()
            bw = self._win.winfo_reqwidth()
            bh = self._win.winfo_reqheight()
            if self._manual_offset is not None:
                ox, oy = self._manual_offset
                x, y = px + ox, py + oy
            else:
                # 默认：宠物右侧偏下
                x = px + pw + 8
                y = py + max(0, (ph - bh) // 2)
                # 若右侧出屏，改到左侧
                sw = self._win.winfo_screenwidth()
                if x + bw > sw - 8:
                    x = max(8, px - bw - 8)
            self._win.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def follow_pet(self) -> None:
        if self.visible:
            self._reposition()

    def hide(self) -> None:
        if self._win is not None:
            try:
                self._win.destroy()
            except tk.TclError:
                pass
            self._win = None
        self._manual_offset = None
