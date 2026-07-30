
"""时光机：历史任务与番茄钟回顾面板。"""
from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk
from typing import TYPE_CHECKING

from ui.theme import Colors, Fonts, apply_window_bg, configure_ttk_styles

if TYPE_CHECKING:
    from app import DesktopPetApp


class TimeMachinePanel:
    def __init__(self, app: DesktopPetApp) -> None:
        self.app = app
        self.win: tk.Toplevel | None = None
        self.date_var = tk.StringVar()
        self.summary_var = tk.StringVar()
        self._task_tree: ttk.Treeview | None = None
        self._session_tree: ttk.Treeview | None = None

    def open(self) -> None:
        if self.win and self.win.winfo_exists():
            self.win.lift()
            return

        configure_ttk_styles()
        win = tk.Toplevel(self.app.root)
        apply_window_bg(win)
        win.title(self.app.character.ui_text("timemachine_title"))
        win.attributes("-topmost", True)
        win.geometry("560x460")
        win.protocol("WM_DELETE_WINDOW", self.close)
        self.win = win

        top = tk.Frame(win, bg=Colors.BG_WINDOW, padx=14, pady=12)
        top.pack(fill="x")
        tk.Label(top, text="选择日期", bg=Colors.BG_WINDOW, fg=Colors.TEXT_MAIN, font=Fonts.body()).pack(side="left")
        dates = self.app.storage.list_available_dates()
        if not dates:
            today = date.today()
            dates = [today.isoformat(), (today - timedelta(days=1)).isoformat()]
        self.date_var.set(dates[0])
        combo = ttk.Combobox(top, textvariable=self.date_var, values=dates, width=16, state="readonly")
        combo.pack(side="left", padx=8)
        combo.bind("<<ComboboxSelected>>", lambda _e: self._load())
        for text, cmd in (
            ("昨天", self._select_yesterday),
            ("刷新", self._load),
        ):
            tk.Button(
                top,
                text=text,
                command=cmd,
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_MAIN,
                activebackground=Colors.BG_HOVER,
                activeforeground=Colors.TEXT_MAIN,
                relief="solid",
                bd=1,
                highlightbackground=Colors.BORDER,
                highlightthickness=1,
                font=Fonts.body(),
                padx=8,
                pady=3,
                cursor="hand2",
            ).pack(side="left", padx=4)

        tk.Label(
            win,
            textvariable=self.summary_var,
            bg=Colors.BG_WINDOW,
            fg=Colors.TEXT_SECONDARY,
            font=Fonts.body(),
            padx=14,
            justify="left",
        ).pack(fill="x")

        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True, padx=14, pady=8)

        task_frame = ttk.Frame(notebook)
        session_frame = ttk.Frame(notebook)
        notebook.add(task_frame, text="任务")
        notebook.add(session_frame, text="番茄钟记录")

        self._task_tree = self._make_tree(
            task_frame,
            columns=("title", "done", "sessions", "minutes"),
            headings=("任务", "完成", "专注次数", "专注分钟"),
            widths=(200, 60, 80, 80),
        )
        self._session_tree = self._make_tree(
            session_frame,
            columns=("title", "mode", "planned", "actual", "done", "time"),
            headings=("任务", "类型", "计划分", "实际秒", "完成", "结束时间"),
            widths=(120, 50, 50, 60, 50, 140),
        )
        self._load()

    def _make_tree(
        self,
        parent: ttk.Frame,
        columns: tuple[str, ...],
        headings: tuple[str, ...],
        widths: tuple[int, ...],
    ) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=12)
        for col, head, width in zip(columns, headings, widths):
            tree.heading(col, text=head)
            tree.column(col, width=width, anchor="center")
        scroll = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        return tree

    def _select_yesterday(self) -> None:
        self.date_var.set((date.today() - timedelta(days=1)).isoformat())
        self._load()

    def _load(self) -> None:
        if not self._task_tree or not self._session_tree:
            return
        day = self.date_var.get().strip() or date.today().isoformat()
        summary = self.app.storage.get_day_summary(day)
        self.summary_var.set(
            f"📅 {summary['date']}  |  任务 {summary['completed_task_count']}/{summary['task_count']} 完成  |  "
            f"番茄钟 {summary['focus_count']} 次  |  专注合计 {summary['focus_minutes']} 分钟"
        )
        for tree in (self._task_tree, self._session_tree):
            for item in tree.get_children():
                tree.delete(item)
        for t in summary["tasks"]:
            self._task_tree.insert(
                "",
                "end",
                values=(
                    t.get("title", ""),
                    "✓" if t.get("completed") else "—",
                    t.get("focus_sessions", 0),
                    t.get("focus_minutes", 0),
                ),
            )
        for s in summary["sessions"]:
            ended = (s.get("ended_at") or "")[-8:]
            self._session_tree.insert(
                "",
                "end",
                values=(
                    s.get("task_title", ""),
                    "专注" if s.get("mode") == "focus" else "休息",
                    s.get("planned_minutes", 0),
                    s.get("actual_seconds", 0),
                    "✓" if s.get("completed") else "—",
                    ended,
                ),
            )

    def close(self) -> None:
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None
