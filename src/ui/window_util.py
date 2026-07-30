"""窗口几何工具：屏幕居中等。"""
from __future__ import annotations

import tkinter as tk


def center_window_on_screen(win: tk.Misc) -> None:
    """把窗口放到当前屏幕几何中心（不跟随桌宠坐标）。"""
    try:
        win.update_idletasks()
        w = win.winfo_width() or win.winfo_reqwidth()
        h = win.winfo_height() or win.winfo_reqheight()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        win.geometry(f"+{x}+{y}")
    except tk.TclError:
        pass
