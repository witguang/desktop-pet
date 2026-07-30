"""番茄钟与任务管理控制面板（文案跟随当前角色包）。"""
from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from config import DEFAULT_BREAK_MINUTES, DEFAULT_FOCUS_MINUTES
from core.pomodoro import TimerMode, TimerStatus
from ui.theme import Colors, Fonts, apply_window_bg, configure_ttk_styles

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
        self._focus_trace: str | None = None
        self._break_trace: str | None = None

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

        configure_ttk_styles()
        char = self.app.character
        win = tk.Toplevel(self.app.root)
        apply_window_bg(win)
        win.title(char.ui_text("panel_title"))
        win.attributes("-topmost", True)
        win.resizable(False, False)
        win.protocol("WM_DELETE_WINDOW", self.close)
        self.win = win

        pad = {"padx": 8, "pady": 3}
        root_frame = tk.Frame(win, bg=Colors.BG_WINDOW, padx=14, pady=14)
        root_frame.grid(row=0, column=0, sticky="nsew")

        tk.Label(
            root_frame,
            textvariable=self.character_var,
            fg=Colors.PRIMARY,
            bg=Colors.BG_WINDOW,
            font=Fonts.body(bold=True),
        ).grid(row=0, column=0, columnspan=3, sticky="w", **pad)

        tk.Label(root_frame, text="当前任务", bg=Colors.BG_WINDOW, fg=Colors.TEXT_MAIN, font=Fonts.body()).grid(
            row=1, column=0, sticky="w", **pad
        )
        tk.Entry(
            root_frame,
            textvariable=self.task_var,
            width=28,
            bg=Colors.BG_INPUT,
            fg=Colors.TEXT_MAIN,
            relief="solid",
            bd=1,
            font=Fonts.body(),
        ).grid(row=1, column=1, columnspan=2, sticky="ew", **pad)

        tk.Label(root_frame, text="专注 (分钟)", bg=Colors.BG_WINDOW, fg=Colors.TEXT_MAIN, font=Fonts.body()).grid(
            row=2, column=0, sticky="w", **pad
        )
        focus_entry = tk.Entry(
            root_frame,
            textvariable=self.focus_var,
            width=8,
            bg=Colors.BG_INPUT,
            fg=Colors.TEXT_MAIN,
            relief="solid",
            bd=1,
            font=Fonts.body(),
        )
        focus_entry.grid(row=2, column=1, sticky="w", **pad)
        tk.Label(root_frame, text="休息 (分钟)", bg=Colors.BG_WINDOW, fg=Colors.TEXT_MAIN, font=Fonts.body()).grid(
            row=3, column=0, sticky="w", **pad
        )
        break_entry = tk.Entry(
            root_frame,
            textvariable=self.break_var,
            width=8,
            bg=Colors.BG_INPUT,
            fg=Colors.TEXT_MAIN,
            relief="solid",
            bd=1,
            font=Fonts.body(),
        )
        break_entry.grid(row=3, column=1, sticky="w", **pad)
        # 修改分钟数时立即同步番茄钟大字显示（空闲时）
        self._focus_trace = self.focus_var.trace_add("write", self._on_minutes_edited)
        self._break_trace = self.break_var.trace_add("write", self._on_minutes_edited)
        focus_entry.bind("<KeyRelease>", self._on_minutes_edited)
        break_entry.bind("<KeyRelease>", self._on_minutes_edited)
        focus_entry.bind("<FocusOut>", self._on_minutes_edited)
        break_entry.bind("<FocusOut>", self._on_minutes_edited)

        timer_frame = tk.LabelFrame(
            root_frame,
            text=" 番茄钟 ",
            bg=Colors.BG_CARD,
            fg=Colors.PRIMARY,
            font=Fonts.body(bold=True),
            relief="solid",
            bd=1,
            padx=10,
            pady=10,
        )
        timer_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=8)
        tk.Label(
            timer_frame,
            textvariable=self.timer_label_var,
            font=("Consolas", 30, "bold"),
            bg=Colors.BG_CARD,
            fg=Colors.TEXT_MAIN,
        ).pack()
        tk.Label(timer_frame, textvariable=self.mode_var, bg=Colors.BG_CARD, fg=Colors.TEXT_SECONDARY, font=Fonts.body()).pack()
        tk.Label(timer_frame, textvariable=self.status_var, bg=Colors.BG_CARD, fg=Colors.TEXT_MUTED, font=Fonts.small()).pack()

        btn_frame = tk.Frame(root_frame, bg=Colors.BG_WINDOW)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=8)
        for text, cmd in (
            ("开始", self._on_start),
            ("暂停", self._on_pause),
            ("重置", self._on_reset),
        ):
            tk.Button(
                btn_frame,
                text=text,
                command=cmd,
                width=8,
                font=Fonts.body(),
                bg=Colors.PRIMARY,
                fg=Colors.TEXT_ON_PRIMARY,
                activebackground=Colors.PRIMARY_DARK,
                activeforeground=Colors.TEXT_ON_PRIMARY,
                relief="flat",
                padx=8,
                pady=4,
                cursor="hand2",
            ).pack(side="left", padx=4)

        def _secondary_btn(parent: tk.Widget, text: str, command: Callable[[], None] | None = None) -> tk.Button:
            """生成带边框的次要按钮，与卡片背景有区分。"""
            return tk.Button(
                parent,
                text=text,
                command=command,
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_MAIN,
                activebackground=Colors.BG_HOVER,
                activeforeground=Colors.TEXT_MAIN,
                relief="solid",
                bd=1,
                highlightbackground=Colors.BORDER,
                highlightthickness=1,
                font=Fonts.body(),
                anchor="w",
                padx=10,
                pady=5,
                cursor="hand2",
            )

        extra = tk.LabelFrame(
            root_frame,
            text=" 互动 ",
            bg=Colors.BG_CARD,
            fg=Colors.PRIMARY,
            font=Fonts.body(bold=True),
            relief="solid",
            bd=1,
            padx=10,
            pady=8,
        )
        extra.grid(row=6, column=0, columnspan=3, sticky="ew", pady=6)
        self._food_btn = _secondary_btn(
            extra,
            char.ui_text("spawn_food_button"),
            self.app.spawn_food,
        )
        self._food_btn.pack(fill="x", pady=2)
        for text, cmd in (
            (char.ui_text("timemachine_button"), self.app.open_time_machine),
            (char.ui_text("character_button"), self.app.open_character_picker),
            ("完成当前任务 ✓", self._on_complete_task),
            ("吃喝设置", self.open_eat_drink_settings),
        ):
            _secondary_btn(extra, text, cmd).pack(fill="x", pady=2)

        # 底部：备忘录 + 主设置
        bottom = tk.LabelFrame(
            root_frame,
            text=" 工具 ",
            bg=Colors.BG_CARD,
            fg=Colors.PRIMARY,
            font=Fonts.body(bold=True),
            relief="solid",
            bd=1,
            padx=10,
            pady=8,
        )
        bottom.grid(row=7, column=0, columnspan=3, sticky="ew", pady=6)
        self._memo_btn = _secondary_btn(
            bottom,
            char.ui_text("memo_button"),
            self.open_memo,
        )
        self._memo_btn.pack(fill="x", pady=2)
        self._settings_btn = _secondary_btn(
            bottom,
            char.ui_text("settings_button"),
            self.open_main_settings,
        )
        self._settings_btn.pack(fill="x", pady=2)

        # 退出：无边框窗口没有系统关闭钮，必须提供明确入口
        exit_frame = tk.Frame(root_frame, bg=Colors.BG_WINDOW)
        exit_frame.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(10, 4))
        tk.Button(
            exit_frame,
            text="退出桌宠",
            command=self.quit_app,
            bg=Colors.DANGER,
            fg=Colors.TEXT_ON_PRIMARY,
            activebackground="#D32F2F",
            activeforeground=Colors.TEXT_ON_PRIMARY,
            relief="flat",
            font=Fonts.body(),
            padx=10,
            pady=5,
            cursor="hand2",
        ).pack(fill="x")

        tk.Label(
            root_frame,
            textvariable=self.meter_var,
            bg=Colors.BG_WINDOW,
            fg=Colors.TEXT_SECONDARY,
            font=Fonts.body(),
        ).grid(row=9, column=0, columnspan=3, sticky="w", **pad)
        tk.Label(
            root_frame,
            textvariable=self.tip_var,
            bg=Colors.BG_WINDOW,
            fg=Colors.TEXT_MUTED,
            font=Fonts.small(),
            justify="left",
        ).grid(row=10, column=0, columnspan=3, sticky="w", **pad)

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
        if self._focus_trace is not None:
            try:
                self.focus_var.trace_remove("write", self._focus_trace)
            except Exception:
                pass
            self._focus_trace = None
        if self._break_trace is not None:
            try:
                self.break_var.trace_remove("write", self._break_trace)
            except Exception:
                pass
            self._break_trace = None
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None
            self._food_btn = None
            self._memo_btn = None
            self._settings_btn = None

    def _on_minutes_edited(self, *_args: object) -> None:
        """专注/休息分钟变化时，立即刷新番茄钟显示（运行中不打断剩余时间）。"""
        try:
            focus = int(self.focus_var.get().strip())
            brk = int(self.break_var.get().strip())
        except ValueError:
            return
        if focus <= 0 or brk <= 0:
            return
        timer = self.app.timer
        timer.configure(focus_minutes=focus, break_minutes=brk)
        # configure 在 IDLE 时会改 remaining；直接刷新大字
        self.timer_label_var.set(timer.format_remaining())
        self.mode_var.set("专注中" if timer.mode == TimerMode.FOCUS else "休息中")

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
        self.app.open_eat_drink_settings()

    def open_main_settings(self) -> None:
        self.app.open_main_settings()

    def open_memo(self) -> None:
        self.app.open_memo()

    def quit_app(self) -> None:
        self.app.quit_app(confirm=True)

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
