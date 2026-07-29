"""番茄钟与任务管理控制面板（文案跟随当前角色包）。"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from config import DEFAULT_BREAK_MINUTES, DEFAULT_FOCUS_MINUTES
from core.pomodoro import TimerMode, TimerStatus

if TYPE_CHECKING:
    from app import DesktopPetApp


class ControlPanel:
    def __init__(self, app: DesktopPetApp) -> None:
        self.app = app
        self.win: tk.Toplevel | None = None

        self.task_var = tk.StringVar()
        self.focus_var = tk.StringVar(value=str(DEFAULT_FOCUS_MINUTES))
        self.break_var = tk.StringVar(value=str(DEFAULT_BREAK_MINUTES))
        self.timer_label_var = tk.StringVar(value="25:00")
        self.status_var = tk.StringVar(value="空闲")
        self.meter_var = tk.StringVar(value="")
        self.mode_var = tk.StringVar(value="专注")
        self.character_var = tk.StringVar(value="")
        self.tip_var = tk.StringVar(value="")
        self._food_btn: ttk.Button | None = None
        self._memo_btn: ttk.Button | None = None
        self._settings_btn: ttk.Button | None = None

    def toggle(self) -> None:
        if self.win and self.win.winfo_exists():
            self.close()
        else:
            self.open()

    def open(self) -> None:
        if self.win and self.win.winfo_exists():
            self.win.lift()
            self.refresh()
            return

        char = self.app.character
        win = tk.Toplevel(self.app.root)
        win.title(char.ui_text("panel_title"))
        win.attributes("-topmost", True)
        win.resizable(False, False)
        win.protocol("WM_DELETE_WINDOW", self.close)
        self.win = win

        pad = {"padx": 10, "pady": 4}
        root_frame = ttk.Frame(win, padding=12)
        root_frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(root_frame, textvariable=self.character_var, foreground="#1565C0").grid(
            row=0, column=0, columnspan=3, sticky="w", **pad
        )

        ttk.Label(root_frame, text="当前任务").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(root_frame, textvariable=self.task_var, width=28).grid(
            row=1, column=1, columnspan=2, sticky="ew", **pad
        )

        ttk.Label(root_frame, text="专注 (分钟)").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(root_frame, textvariable=self.focus_var, width=8).grid(row=2, column=1, sticky="w", **pad)
        ttk.Label(root_frame, text="休息 (分钟)").grid(row=3, column=0, sticky="w", **pad)
        ttk.Entry(root_frame, textvariable=self.break_var, width=8).grid(row=3, column=1, sticky="w", **pad)

        timer_frame = ttk.LabelFrame(root_frame, text="番茄钟", padding=8)
        timer_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=8)
        ttk.Label(timer_frame, textvariable=self.timer_label_var, font=("Consolas", 28, "bold")).pack()
        ttk.Label(timer_frame, textvariable=self.mode_var).pack()
        ttk.Label(timer_frame, textvariable=self.status_var).pack()

        btn_frame = ttk.Frame(root_frame)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=6)
        ttk.Button(btn_frame, text="开始", command=self._on_start, width=8).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="暂停", command=self._on_pause, width=8).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="重置", command=self._on_reset, width=8).pack(side="left", padx=4)

        extra = ttk.LabelFrame(root_frame, text="互动", padding=8)
        extra.grid(row=6, column=0, columnspan=3, sticky="ew", pady=6)
        self._food_btn = ttk.Button(
            extra,
            text=char.ui_text("spawn_food_button"),
            command=self.app.spawn_food,
        )
        self._food_btn.pack(fill="x", pady=2)
        ttk.Button(
            extra,
            text=char.ui_text("timemachine_button"),
            command=self.app.open_time_machine,
        ).pack(fill="x", pady=2)
        ttk.Button(
            extra,
            text=char.ui_text("character_button"),
            command=self.app.open_character_picker,
        ).pack(fill="x", pady=2)
        ttk.Button(extra, text="完成当前任务 ✓", command=self._on_complete_task).pack(fill="x", pady=2)
        ttk.Button(extra, text="测试喝水提醒 💧", command=self.app.debug_water_remind).pack(fill="x", pady=2)
        ttk.Button(extra, text="测试用餐提醒 🍽", command=self.app.debug_meal_remind).pack(fill="x", pady=2)
        ttk.Button(extra, text="吃喝设置", command=self.open_eat_drink_settings).pack(fill="x", pady=2)

        # 底部：备忘录 + 主设置
        bottom = ttk.LabelFrame(root_frame, text="工具", padding=8)
        bottom.grid(row=7, column=0, columnspan=3, sticky="ew", pady=6)
        self._memo_btn = ttk.Button(
            bottom,
            text=char.ui_text("memo_button"),
            command=self.open_memo,
        )
        self._memo_btn.pack(fill="x", pady=2)
        self._settings_btn = ttk.Button(
            bottom,
            text=char.ui_text("settings_button"),
            command=self.open_main_settings,
        )
        self._settings_btn.pack(fill="x", pady=2)

        ttk.Label(root_frame, textvariable=self.meter_var).grid(
            row=8, column=0, columnspan=3, sticky="w", **pad
        )
        ttk.Label(root_frame, textvariable=self.tip_var, foreground="#555555", justify="left").grid(
            row=9, column=0, columnspan=3, sticky="w", **pad
        )

        win.update_idletasks()
        ww = win.winfo_reqwidth()
        wh = win.winfo_reqheight()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = max(0, (sw - ww) // 2)
        y = max(0, (sh - wh) // 2)
        win.geometry(f"+{x}+{y}")

        self.refresh()

    def close(self) -> None:
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None
            self._food_btn = None
            self._memo_btn = None
            self._settings_btn = None

    def on_character_changed(self) -> None:
        """角色切换后刷新标题与按钮文案。"""
        if not self.win or not self.win.winfo_exists():
            self.refresh()
            return
        char = self.app.character
        self.win.title(char.ui_text("panel_title"))
        if self._food_btn is not None:
            self._food_btn.configure(text=char.ui_text("spawn_food_button"))
        if self._memo_btn is not None:
            self._memo_btn.configure(text=char.ui_text("memo_button"))
        if self._settings_btn is not None:
            self._settings_btn.configure(text=char.ui_text("settings_button"))
        self.refresh()

    def open_eat_drink_settings(self) -> None:
        messagebox.showinfo(
            "吃喝设置",
            "吃喝提醒时刻表设置尚未接入 UI。\n"
            "当前使用 config.py 中的 WATER_REMINDERS / MEAL_REMINDERS。",
            parent=self.win or self.app.root,
        )

    def open_main_settings(self) -> None:
        self.app.open_main_settings()

    def open_memo(self) -> None:
        self.app.open_memo()

    def _parse_minutes(self) -> tuple[int, int] | None:
        try:
            focus = int(self.focus_var.get().strip())
            brk = int(self.break_var.get().strip())
            if focus <= 0 or brk <= 0:
                raise ValueError
            return focus, brk
        except ValueError:
            messagebox.showwarning("输入错误", "专注/休息时间请输入正整数（分钟）。", parent=self.win)
            return None

    def _on_start(self) -> None:
        parsed = self._parse_minutes()
        if not parsed:
            return
        focus, brk = parsed
        title = self.task_var.get().strip() or "未命名任务"
        self.app.start_pomodoro(task_title=title, focus_minutes=focus, break_minutes=brk)

    def _on_pause(self) -> None:
        self.app.pause_pomodoro()

    def _on_reset(self) -> None:
        self.app.reset_pomodoro()

    def _on_complete_task(self) -> None:
        self.app.complete_current_task()

    def refresh(self) -> None:
        timer = self.app.timer
        char = self.app.character
        self.character_var.set(char.ui_text("status_line"))
        self.tip_var.set(char.ui_text("tip_line"))
        self.timer_label_var.set(timer.format_remaining())
        self.mode_var.set("专注中" if timer.mode == TimerMode.FOCUS else "休息中")
        status_map = {
            TimerStatus.IDLE: "空闲",
            TimerStatus.RUNNING: "运行中",
            TimerStatus.PAUSED: "已暂停",
            TimerStatus.FINISHED: "本轮结束",
        }
        self.status_var.set(status_map.get(timer.status, str(timer.status)))

        if char.uses_mood:
            value, maximum = self.app.mood.mood, self.app.mood.max_value
        else:
            value, maximum = self.app.hunger.hunger, self.app.hunger.max_value
        self.meter_var.set(char.ui_text("meter_label", value=value, max=maximum))
