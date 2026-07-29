"""可拖动的食物道具。"""
from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from utils.asset_loader import AssetLoader


class FoodItem:
    def __init__(
        self,
        master: tk.Misc,
        loader: AssetLoader,
        start_xy: tuple[int, int],
        on_feed: Callable[[], None],
        pet_bbox_getter: Callable[[], tuple[int, int, int, int]],
        transparent_color: str,
        size: tuple[int, int] = (48, 48),
    ) -> None:
        self.master = master
        self.on_feed = on_feed
        self.pet_bbox_getter = pet_bbox_getter
        self.transparent_color = transparent_color
        self._fed = False

        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            self.win.attributes("-transparentcolor", transparent_color)
        except tk.TclError:
            pass
        self.win.configure(bg=transparent_color)

        anim = loader.get_food()
        self._photo = anim.frames[0]
        self.label = tk.Label(self.win, image=self._photo, bg=transparent_color, bd=0)
        self.label.pack()

        w, h = size
        x, y = start_xy
        self.win.geometry(f"{w}x{h}+{x}+{y}")

        self._drag_ox = 0
        self._drag_oy = 0
        self.label.bind("<ButtonPress-1>", self._on_press)
        self.label.bind("<B1-Motion>", self._on_drag)
        self.label.bind("<ButtonRelease-1>", self._on_release)
        self.label.bind("<Button-3>", lambda _e: self.destroy())

    def _on_press(self, event: tk.Event) -> None:
        self._drag_ox = event.x
        self._drag_oy = event.y

    def _on_drag(self, event: tk.Event) -> None:
        x = self.win.winfo_x() + event.x - self._drag_ox
        y = self.win.winfo_y() + event.y - self._drag_oy
        self.win.geometry(f"+{x}+{y}")

    def _on_release(self, _event: tk.Event) -> None:
        if self._fed:
            return
        fx = self.win.winfo_x()
        fy = self.win.winfo_y()
        fw = self.win.winfo_width()
        fh = self.win.winfo_height()
        fcx, fcy = fx + fw // 2, fy + fh // 2
        px, py, pw, ph = self.pet_bbox_getter()
        if px <= fcx <= px + pw and py <= fcy <= py + ph:
            self._fed = True
            self.on_feed()
            self.destroy()

    def destroy(self) -> None:
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# 向后兼容别名
DorayakiItem = FoodItem
