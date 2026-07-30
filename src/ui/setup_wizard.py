"""首次启动 / 安装向导：选择安装位置与备忘录目录。"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

from ui.theme import Colors, Fonts, apply_window_bg, configure_ttk_styles, entry_kwargs
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
    若 first_run 模式下用户修改了安装位置，relaunch_exe 将指向新位置的入口，
    调用者应启动该入口后退出当前实例。
    """

    def __init__(
        self,
        *,
        mode: str = "first_run",
        on_done: Callable[[], None] | None = None,
    ) -> None:
        """
        mode:
          - first_run: 可选择安装位置（默认当前目录）并配备忘录
          - install: 可选择安装位置并复制程序
        """
        self.mode = mode
        self.on_done = on_done
        self.result_ok = False
        self.relaunch_exe: Path | None = None
        self.install_dir = default_install_dir() if mode == "install" else find_app_source()
        self.memo_dir = default_memo_suggestion()
        self._root: tk.Tk | None = None

    def run(self) -> bool:
        # 必须先创建根窗口，再配置 ttk，否则 ttk.Style() 会生成空白幽灵窗
        root = tk.Tk()
        apply_window_bg(root)
        configure_ttk_styles(root)
        self._root = root
        root.title("Desktop Pet 安装向导" if self.mode == "install" else "Desktop Pet 初始设置")
        root.resizable(False, False)
        try:
            root.attributes("-topmost", True)
        except tk.TclError:
            pass

        install_var = tk.StringVar(value=str(self.install_dir))
        memo_var = tk.StringVar(value=str(self.memo_dir))
        shortcut_var = tk.BooleanVar(value=True)
        status_var = tk.StringVar(value="")

        frame = tk.Frame(root, bg=Colors.BG_WINDOW, padx=20, pady=20)
        frame.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        title = "安装向导" if self.mode == "install" else "欢迎使用桌面宠物"
        tk.Label(
            frame,
            text=title,
            font=Fonts.title(size=16),
            bg=Colors.BG_WINDOW,
            fg=Colors.TEXT_MAIN,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        tk.Label(
            frame,
            text="请选择安装位置与备忘录保存位置（可浏览自定义）。",
            fg=Colors.TEXT_SECONDARY,
            bg=Colors.BG_WINDOW,
            font=Fonts.body(),
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 16))

        row = 2
        box = tk.LabelFrame(
            frame,
            text=" 程序安装位置 ",
            bg=Colors.BG_CARD,
            fg=Colors.PRIMARY,
            font=Fonts.body(bold=True),
            relief="solid",
            bd=1,
            padx=12,
            pady=12,
        )
        box.grid(row=row, column=0, columnspan=3, sticky="ew", pady=6)
        box.columnconfigure(0, weight=1)
        install_entry = tk.Entry(
            box,
            textvariable=install_var,
            width=52,
            **entry_kwargs(),
        )
        install_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        tk.Button(
            box,
            text="浏览…",
            width=8,
            command=lambda: self._browse_dir(root, install_var, install_entry, "选择安装文件夹"),
            bg=Colors.PRIMARY,
            fg=Colors.TEXT_ON_PRIMARY,
            activebackground=Colors.PRIMARY_DARK,
            activeforeground=Colors.TEXT_ON_PRIMARY,
            relief="flat",
            font=Fonts.body(),
            cursor="hand2",
        ).grid(row=0, column=1)
        install_hint = (
            "程序文件将复制到此目录（可自由选择盘符与文件夹）。"
            if self.mode == "install"
            else "留空则使用当前目录；改到其他位置会复制程序并需重新启动。"
        )
        tk.Label(
            box,
            text=install_hint,
            fg=Colors.TEXT_MUTED,
            bg=Colors.BG_CARD,
            font=Fonts.small(),
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        row += 1

        memo_box = tk.LabelFrame(
            frame,
            text=" 备忘录保存位置 ",
            bg=Colors.BG_CARD,
            fg=Colors.PRIMARY,
            font=Fonts.body(bold=True),
            relief="solid",
            bd=1,
            padx=12,
            pady=12,
        )
        memo_box.grid(row=row, column=0, columnspan=3, sticky="ew", pady=6)
        memo_box.columnconfigure(0, weight=1)
        memo_entry = tk.Entry(
            memo_box,
            textvariable=memo_var,
            width=52,
            **entry_kwargs(),
        )
        memo_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        tk.Button(
            memo_box,
            text="浏览…",
            width=8,
            command=lambda: self._browse_dir(root, memo_var, memo_entry, "选择备忘录文件夹"),
            bg=Colors.PRIMARY,
            fg=Colors.TEXT_ON_PRIMARY,
            activebackground=Colors.PRIMARY_DARK,
            activeforeground=Colors.TEXT_ON_PRIMARY,
            relief="flat",
            font=Fonts.body(),
            cursor="hand2",
        ).grid(row=0, column=1)
        tk.Label(
            memo_box,
            text="每日笔记（如 2026-07-30.md）写在这里，可选 Obsidian 库目录。",
            fg=Colors.TEXT_MUTED,
            bg=Colors.BG_CARD,
            font=Fonts.small(),
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        row += 1

        cb = tk.Checkbutton(
            frame,
            text="在桌面创建快捷方式",
            variable=shortcut_var,
            bg=Colors.BG_WINDOW,
            fg=Colors.TEXT_MAIN,
            activebackground=Colors.BG_WINDOW,
            activeforeground=Colors.TEXT_MAIN,
            selectcolor=Colors.BG_CARD,
            font=Fonts.body(),
        )
        cb.grid(row=row, column=0, columnspan=3, sticky="w", pady=(12, 4))
        row += 1

        tk.Label(
            frame,
            textvariable=status_var,
            fg=Colors.PRIMARY,
            bg=Colors.BG_WINDOW,
            font=Fonts.body(),
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=6)
        row += 1

        btns = tk.Frame(frame, bg=Colors.BG_WINDOW)
        btns.grid(row=row, column=0, columnspan=3, sticky="e", pady=(16, 0))

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
            target = install_path

            if not install_path.as_posix().strip("."):
                messagebox.showwarning("提示", "请填写安装位置。", parent=root)
                return
            try:
                install_path.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                messagebox.showerror("错误", f"无法创建安装目录：\n{exc}", parent=root)
                return

            # first_run 模式下若安装位置就是当前目录，无需复制
            needs_copy = src.resolve() != install_path.resolve()
            if needs_copy:
                status_var.set("正在复制文件，请稍候…")
                root.update_idletasks()
                try:
                    n = copy_app_tree(src, install_path, progress=lambda m: status_var.set(m))
                    status_var.set(f"已复制 {n} 个文件")
                except OSError as exc:
                    messagebox.showerror("复制失败", str(exc), parent=root)
                    return

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

            # 若 first_run 模式下移动了安装位置，需要从新位置重启
            if self.mode == "first_run" and needs_copy and exe:
                self.relaunch_exe = exe
                msg = (
                    f"设置完成！程序已复制到新位置：\n\n{target}\n\n"
                    f"请从新位置的 DesktopPet.exe 启动。"
                )
                messagebox.showinfo("完成", msg, parent=root)
                root.destroy()
                return

            msg = f"设置完成！\n\n程序目录：\n{target}\n\n备忘录目录：\n{memo_path}"
            if self.mode == "install" and exe:
                msg += f"\n\n请运行：\n{exe}"
            messagebox.showinfo("完成", msg, parent=root)
            root.destroy()

        tk.Button(
            btns,
            text="取消",
            command=do_cancel,
            width=10,
            bg=Colors.BG_CARD,
            fg=Colors.TEXT_MAIN,
            activebackground=Colors.BG_HOVER,
            activeforeground=Colors.TEXT_MAIN,
            relief="solid",
            bd=1,
            highlightbackground=Colors.BORDER,
            highlightthickness=1,
            font=Fonts.body(),
            cursor="hand2",
        ).pack(side="left", padx=4)
        tk.Button(
            btns,
            text="安装并完成" if self.mode == "install" else "完成并启动",
            command=do_finish,
            width=14,
            bg=Colors.PRIMARY,
            fg=Colors.TEXT_ON_PRIMARY,
            activebackground=Colors.PRIMARY_DARK,
            activeforeground=Colors.TEXT_ON_PRIMARY,
            relief="flat",
            font=Fonts.body(bold=True),
            cursor="hand2",
        ).pack(side="left", padx=4)

        # 居中（带合理最小尺寸，避免空白小窗感）
        root.update_idletasks()
        w = max(root.winfo_reqwidth(), 520)
        h = max(root.winfo_reqheight(), 360)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        root.minsize(480, 320)
        root.mainloop()
        self._root = None
        return self.result_ok

    @staticmethod
    def _browse_dir(
        parent: tk.Tk,
        var: tk.StringVar,
        entry: tk.Entry,
        title: str,
    ) -> None:
        initial = var.get().strip() or str(Path.home())
        p = Path(initial)
        if not p.is_dir():
            p = Path.home()
        chosen = filedialog.askdirectory(
            parent=parent,
            title=title,
            initialdir=str(p),
        )
        if chosen:
            var.set(chosen)
            # 选完目录后 Windows 可能把 Entry 前景改成系统白字，强制恢复可读配色
            try:
                entry.configure(**entry_kwargs())
                entry.icursor("end")
                entry.xview_moveto(1.0)
            except tk.TclError:
                pass


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
