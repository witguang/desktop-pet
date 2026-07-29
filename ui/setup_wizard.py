"""首次启动 / 安装向导：选择安装位置与备忘录目录。"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from utils.install_util import (
    copy_app_tree,
    create_windows_shortcut,
    default_install_dir,
    default_memo_suggestion,
    desktop_dir,
    find_app_source,
    find_main_exe,
    write_initial_settings,
)


class SetupWizard:
    """
    阻塞式向导。run() 返回 True 表示完成并应启动应用；False 表示取消。
    """

    def __init__(
        self,
        *,
        mode: str = "first_run",
        on_done: Callable[[], None] | None = None,
    ) -> None:
        """
        mode:
          - first_run: 当前目录即运行目录，只配备忘录 + 快捷方式
          - install: 可选择安装位置并复制程序
        """
        self.mode = mode
        self.on_done = on_done
        self.result_ok = False
        self.install_dir = default_install_dir()
        self.memo_dir = default_memo_suggestion()
        self._root: tk.Tk | None = None

    def run(self) -> bool:
        root = tk.Tk()
        self._root = root
        root.title("Desktop Pet 安装向导" if self.mode == "install" else "Desktop Pet 初始设置")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        install_var = tk.StringVar(value=str(self.install_dir))
        memo_var = tk.StringVar(value=str(self.memo_dir))
        shortcut_var = tk.BooleanVar(value=True)
        status_var = tk.StringVar(value="")

        frame = ttk.Frame(root, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")

        title = "安装向导" if self.mode == "install" else "欢迎使用桌面宠物"
        ttk.Label(frame, text=title, font=("Microsoft YaHei UI", 14, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )
        ttk.Label(
            frame,
            text="请选择安装位置与备忘录保存位置（可浏览自定义）。",
            foreground="#444444",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))

        row = 2
        if self.mode == "install":
            box = ttk.LabelFrame(frame, text="程序安装位置", padding=10)
            box.grid(row=row, column=0, columnspan=3, sticky="ew", pady=4)
            box.columnconfigure(0, weight=1)
            ttk.Entry(box, textvariable=install_var, width=52).grid(row=0, column=0, sticky="ew", padx=(0, 6))
            ttk.Button(
                box,
                text="浏览…",
                width=8,
                command=lambda: self._browse_dir(install_var, "选择安装文件夹"),
            ).grid(row=0, column=1)
            ttk.Label(
                box,
                text="程序文件将复制到此目录（可自由选择盘符与文件夹）。",
                foreground="#666666",
                font=("Microsoft YaHei UI", 8),
            ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
            row += 1

        memo_box = ttk.LabelFrame(frame, text="备忘录保存位置", padding=10)
        memo_box.grid(row=row, column=0, columnspan=3, sticky="ew", pady=4)
        memo_box.columnconfigure(0, weight=1)
        ttk.Entry(memo_box, textvariable=memo_var, width=52).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            memo_box,
            text="浏览…",
            width=8,
            command=lambda: self._browse_dir(memo_var, "选择备忘录文件夹"),
        ).grid(row=0, column=1)
        ttk.Label(
            memo_box,
            text="每日笔记（如 2026-07-30.md）写在这里，可选 Obsidian 库目录。",
            foreground="#666666",
            font=("Microsoft YaHei UI", 8),
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        row += 1

        ttk.Checkbutton(
            frame,
            text="在桌面创建快捷方式",
            variable=shortcut_var,
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(10, 4))
        row += 1

        ttk.Label(frame, textvariable=status_var, foreground="#1565C0").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=6
        )
        row += 1

        btns = ttk.Frame(frame)
        btns.grid(row=row, column=0, columnspan=3, sticky="e", pady=(12, 0))

        def do_cancel() -> None:
            self.result_ok = False
            root.destroy()

        def do_finish() -> None:
            install_path = Path(install_var.get().strip()).expanduser()
            memo_path = Path(memo_var.get().strip()).expanduser()
            if not memo_path.as_posix().strip("."):
                messagebox.showwarning("提示", "请填写备忘录保存位置。", parent=root)
                return
            try:
                memo_path.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                messagebox.showerror("错误", f"无法创建备忘录目录：\n{exc}", parent=root)
                return

            src = find_app_source()
            target = src if self.mode == "first_run" else install_path

            if self.mode == "install":
                if not install_path.as_posix().strip("."):
                    messagebox.showwarning("提示", "请填写安装位置。", parent=root)
                    return
                try:
                    install_path.mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                    messagebox.showerror("错误", f"无法创建安装目录：\n{exc}", parent=root)
                    return
                status_var.set("正在复制文件，请稍候…")
                root.update_idletasks()
                try:
                    n = copy_app_tree(src, install_path, progress=lambda m: status_var.set(m))
                    status_var.set(f"已复制 {n} 个文件")
                except OSError as exc:
                    messagebox.showerror("复制失败", str(exc), parent=root)
                    return
                target = install_path

            try:
                write_initial_settings(target, memo_dir=memo_path)
            except OSError as exc:
                messagebox.showerror("写入设置失败", str(exc), parent=root)
                return

            exe = find_main_exe(target)
            if shortcut_var.get() and exe and exe.suffix.lower() == ".exe":
                sc = desktop_dir() / "Desktop Pet.lnk"
                if create_windows_shortcut(exe, sc, workdir=exe.parent):
                    status_var.set(status_var.get() + " · 已创建桌面快捷方式")
                else:
                    status_var.set(status_var.get() + " · 快捷方式创建失败（可手动创建）")

            self.install_dir = target
            self.memo_dir = memo_path
            self.result_ok = True

            msg = f"设置完成！\n\n程序目录：\n{target}\n\n备忘录目录：\n{memo_path}"
            if self.mode == "install" and exe:
                msg += f"\n\n请运行：\n{exe}"
            messagebox.showinfo("完成", msg, parent=root)
            root.destroy()

        ttk.Button(btns, text="取消", command=do_cancel, width=10).pack(side="left", padx=4)
        ttk.Button(
            btns,
            text="安装并完成" if self.mode == "install" else "完成并启动",
            command=do_finish,
            width=14,
        ).pack(side="left", padx=4)

        # center
        root.update_idletasks()
        w, h = root.winfo_reqwidth(), root.winfo_reqheight()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")
        root.mainloop()
        self._root = None
        return self.result_ok

    @staticmethod
    def _browse_dir(var: tk.StringVar, title: str) -> None:
        initial = var.get().strip() or str(Path.home())
        p = Path(initial)
        if not p.is_dir():
            p = Path.home()
        chosen = filedialog.askdirectory(title=title, initialdir=str(p))
        if chosen:
            var.set(chosen)


def needs_setup() -> bool:
    from data.settings import Settings

    s = Settings()
    if s.get("setup_completed"):
        return False
    # 已配置过备忘录路径：视为完成，避免老用户被弹窗
    if s.get("memo_dir") or s.get("obsidian_dir"):
        s.set("setup_completed", True)
        return False
    return True


def mark_setup_done(memo_dir: Path | None = None) -> None:
    from data.settings import Settings

    s = Settings()
    if memo_dir is not None:
        s.memo_dir = memo_dir
    s.set("setup_completed", True)
