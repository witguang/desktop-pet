"""吃喝设置：自定义喝水 / 用餐时刻（精确到分钟 HH:MM）。"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import tkinter as tk
from tkinter import messagebox, ttk

from config import MEAL_PERIOD_OPTIONS, MEAL_REMINDERS, WATER_REMINDERS

if TYPE_CHECKING:
    from app import DesktopPetApp

_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def normalize_hhmm(text: str) -> str | None:
    text = (text or "").strip()
    m = _TIME_RE.match(text)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    return f"{h:02d}:{mi:02d}"


class EatDrinkSettingsPanel:
    def __init__(self, app: DesktopPetApp) -> None:
        self.app = app
        self.win: tk.Toplevel | None = None
        self._water_rows: list[tuple[tk.StringVar, tk.StringVar]] = []
        self._meal_rows: list[tuple[tk.StringVar, tk.StringVar]] = []
        self._water_frame: ttk.Frame | None = None
        self._meal_frame: ttk.Frame | None = None

    def open(self) -> None:
        if self.win and self.win.winfo_exists():
            self.win.lift()
            return

        win = tk.Toplevel(self.app.root)
        win.title("吃喝设置")
        win.attributes("-topmost", True)
        win.minsize(460, 480)
        win.geometry("500x560")
        win.protocol("WM_DELETE_WINDOW", self.close)
        self.win = win

        win.columnconfigure(0, weight=1)
        win.rowconfigure(0, weight=1)

        canvas = tk.Canvas(win, highlightthickness=0)
        scroll = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        root = ttk.Frame(canvas, padding=12)
        root.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=root, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        ttk.Label(
            root,
            text="吃喝提醒设置",
            font=("Microsoft YaHei UI", 12, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        ttk.Label(
            root,
            text="时间格式：15:16（24 小时制，精确到分钟）· 可自由增减次数",
            foreground="#666666",
            font=("Microsoft YaHei UI", 8),
        ).pack(anchor="w", pady=(0, 10))

        # 喝水
        water_box = ttk.LabelFrame(root, text="喝水提醒", padding=8)
        water_box.pack(fill="x", pady=6)
        self._water_frame = ttk.Frame(water_box)
        self._water_frame.pack(fill="x")
        ttk.Button(water_box, text="＋ 添加喝水时刻", command=self._add_water_row).pack(
            anchor="w", pady=(6, 0)
        )

        # 用餐
        meal_box = ttk.LabelFrame(root, text="用餐提醒（早餐 / 午餐 / 晚餐 / 宵夜）", padding=8)
        meal_box.pack(fill="x", pady=6)
        self._meal_frame = ttk.Frame(meal_box)
        self._meal_frame.pack(fill="x")
        ttk.Button(meal_box, text="＋ 添加用餐时刻", command=self._add_meal_row).pack(
            anchor="w", pady=(6, 0)
        )

        bar = ttk.Frame(root)
        bar.pack(fill="x", pady=(14, 0))
        ttk.Button(bar, text="恢复默认", command=self._reset_defaults, width=10).pack(
            side="left", padx=2
        )
        ttk.Button(bar, text="保存", command=self._save, width=10).pack(side="right", padx=2)
        ttk.Button(bar, text="关闭", command=self.close, width=10).pack(side="right", padx=2)

        self._load_from_settings()
        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"500x560+{(sw - 500) // 2}+{(sh - 560) // 2}")

    def _clear_frame(self, frame: ttk.Frame | None) -> None:
        if not frame:
            return
        for child in frame.winfo_children():
            child.destroy()

    def _load_from_settings(self) -> None:
        self._water_rows.clear()
        self._meal_rows.clear()
        self._clear_frame(self._water_frame)
        self._clear_frame(self._meal_frame)
        for t, p in self.app.settings.water_reminders:
            self._add_water_row(t, p)
        for t, p in self.app.settings.meal_reminders:
            self._add_meal_row(t, p)
        if not self._water_rows:
            self._add_water_row("10:00", "早晨")
        if not self._meal_rows:
            self._add_meal_row("12:00", "午餐")

    def _add_water_row(self, time_str: str = "10:00", period: str = "提醒") -> None:
        if not self._water_frame:
            return
        row = ttk.Frame(self._water_frame)
        row.pack(fill="x", pady=2)
        tv = tk.StringVar(value=time_str)
        pv = tk.StringVar(value=period)
        ttk.Label(row, text="时间", width=4).pack(side="left")
        ttk.Entry(row, textvariable=tv, width=8).pack(side="left", padx=4)
        ttk.Label(row, text="标签", width=4).pack(side="left")
        ttk.Entry(row, textvariable=pv, width=12).pack(side="left", padx=4)
        ttk.Button(row, text="删除", width=6, command=lambda r=row, tv=tv: self._remove_water(r, tv)).pack(
            side="right"
        )
        self._water_rows.append((tv, pv))

    def _remove_water(self, row: ttk.Frame, tv: tk.StringVar) -> None:
        self._water_rows = [(t, p) for t, p in self._water_rows if t is not tv]
        row.destroy()

    def _add_meal_row(self, time_str: str = "12:00", period: str = "午餐") -> None:
        if not self._meal_frame:
            return
        row = ttk.Frame(self._meal_frame)
        row.pack(fill="x", pady=2)
        tv = tk.StringVar(value=time_str)
        pv = tk.StringVar(value=period if period in MEAL_PERIOD_OPTIONS else "午餐")
        ttk.Label(row, text="时间", width=4).pack(side="left")
        ttk.Entry(row, textvariable=tv, width=8).pack(side="left", padx=4)
        ttk.Label(row, text="餐次", width=4).pack(side="left")
        cb = ttk.Combobox(
            row,
            textvariable=pv,
            values=list(MEAL_PERIOD_OPTIONS),
            width=10,
            state="readonly",
        )
        cb.pack(side="left", padx=4)
        ttk.Button(row, text="删除", width=6, command=lambda r=row, tv=tv: self._remove_meal(r, tv)).pack(
            side="right"
        )
        self._meal_rows.append((tv, pv))

    def _remove_meal(self, row: ttk.Frame, tv: tk.StringVar) -> None:
        self._meal_rows = [(t, p) for t, p in self._meal_rows if t is not tv]
        row.destroy()

    def _reset_defaults(self) -> None:
        self._water_rows.clear()
        self._meal_rows.clear()
        self._clear_frame(self._water_frame)
        self._clear_frame(self._meal_frame)
        for t, p in WATER_REMINDERS:
            self._add_water_row(t, p)
        for t, p in MEAL_REMINDERS:
            self._add_meal_row(t, p)

    def _collect(
        self, rows: list[tuple[tk.StringVar, tk.StringVar]], *, meal: bool
    ) -> list[tuple[str, str]] | None:
        result: list[tuple[str, str]] = []
        for tv, pv in rows:
            t = normalize_hhmm(tv.get())
            if t is None:
                messagebox.showwarning(
                    "时间格式",
                    f"无效时间「{tv.get()}」\n请使用 15:16 这种 24 小时制。",
                    parent=self.win,
                )
                return None
            period = pv.get().strip() or ("用餐" if meal else "提醒")
            if meal and period not in MEAL_PERIOD_OPTIONS:
                period = "午餐"
            result.append((t, period))
        # 按时间排序
        result.sort(key=lambda x: x[0])
        return result

    def _save(self) -> None:
        water = self._collect(self._water_rows, meal=False)
        if water is None:
            return
        meal = self._collect(self._meal_rows, meal=True)
        if meal is None:
            return
        if not water and not meal:
            messagebox.showwarning("吃喝设置", "请至少保留一条提醒。", parent=self.win)
            return
        self.app.settings.water_reminders = water
        self.app.settings.meal_reminders = meal
        self.app.apply_reminder_schedules()
        messagebox.showinfo(
            "吃喝设置",
            f"已保存\n喝水 {len(water)} 次 · 用餐 {len(meal)} 次",
            parent=self.win,
        )

    def close(self) -> None:
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None
            self._water_frame = None
            self._meal_frame = None
            self._water_rows.clear()
            self._meal_rows.clear()
