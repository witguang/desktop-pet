"""首次启动 / 安装向导：选择安装位置与备忘录目录。"""
from __future__ import annotations

import subprocess
import sys
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
    阻塞式向导。run() 返回 True 表示完成；False 表示取消。

    结果字段：
      - should_launch_pet: 用户是否勾选「完成后打开桌宠」（默认 True）
      - relaunch_exe: 若应打开桌宠，指向入口（.exe 或 main.py）
      - install_dir / memo_dir: 最终路径
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
        self.should_launch_pet = True
        self.relaunch_exe: Path | None = None
        # 不预填 D:\某文件夹；D 盘仅作文案提醒 / 输入框占位示例
        if mode == "install":
            self.install_dir = default_install_dir()
        else:
            self.install_dir = find_app_source()
        self.memo_dir = default_memo_suggestion()
        self._root: tk.Tk | None = None

    def run(self) -> bool:
        # 必须先创建根窗口，再配置 ttk，否则 ttk.Style() 会生成空白幽灵窗
        root = tk.Tk()
        apply_window_bg(root)  # 背景 + app.ico（去掉左上角羽毛）
        configure_ttk_styles(root)
        self._root = root
        root.title("Desktop Pet 安装向导" if self.mode == "install" else "Desktop Pet 初始设置")
        root.resizable(False, False)
        try:
            root.attributes("-topmost", True)
        except tk.TclError:
            pass

        # 输入框初始为空，仅用灰色占位「D:」示例，不写入真实默认文件夹
        install_var = tk.StringVar(value="")
        memo_var = tk.StringVar(value="")
        shortcut_var = tk.BooleanVar(value=True)
        launch_var = tk.BooleanVar(value=True)  # 默认完成后打开桌宠，可取消
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
            text="请自行选择安装位置与备忘录目录（可浏览）。",
            fg=Colors.TEXT_SECONDARY,
            bg=Colors.BG_WINDOW,
            font=Fonts.body(),
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 4))

        # 醒目提示：仅提醒，不预填路径
        tip = tk.Frame(
            frame,
            bg=Colors.BG_HOVER,
            highlightbackground=Colors.PRIMARY,
            highlightthickness=1,
            padx=10,
            pady=8,
        )
        tip.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        tk.Label(
            tip,
            text="建议安装在 D 盘",
            font=Fonts.body(bold=True),
            bg=Colors.BG_HOVER,
            fg=Colors.PRIMARY,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            tip,
            text="软件与备忘录都建议放在 D 盘，少占 C 盘。下方不会自动填好文件夹，请自己选或输入（可参考占位示例 D:）。",
            font=Fonts.small(),
            bg=Colors.BG_HOVER,
            fg=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=480,
        ).pack(fill="x", pady=(2, 0))

        row = 3
        box = tk.LabelFrame(
            frame,
            text=" 软件安装位置（建议 D 盘） ",
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
        self._attach_path_placeholder(install_entry, install_var, "例如 D:\\…（请选择安装文件夹）")
        tk.Button(
            box,
            text="浏览…",
            width=8,
            command=lambda: self._browse_dir(
                root, install_var, install_entry, "选择安装文件夹（建议 D 盘）"
            ),
            bg=Colors.PRIMARY,
            fg=Colors.TEXT_ON_PRIMARY,
            activebackground=Colors.PRIMARY_DARK,
            activeforeground=Colors.TEXT_ON_PRIMARY,
            relief="flat",
            font=Fonts.body(),
            cursor="hand2",
        ).grid(row=0, column=1)
        tk.Label(
            box,
            text="不会默认创建路径。建议放在 D 盘，点「浏览」自选文件夹。",
            fg=Colors.TEXT_MUTED,
            bg=Colors.BG_CARD,
            font=Fonts.small(),
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        row += 1

        memo_box = tk.LabelFrame(
            frame,
            text=" 备忘录保存位置（建议 D 盘） ",
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
        self._attach_path_placeholder(memo_entry, memo_var, "例如 D:\\…（请选择备忘录文件夹）")
        tk.Button(
            memo_box,
            text="浏览…",
            width=8,
            command=lambda: self._browse_dir(
                root, memo_var, memo_entry, "选择备忘录文件夹（建议 D 盘）"
            ),
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
            text="不会默认创建路径。建议放在 D 盘；每日笔记或 Obsidian 库都可。",
            fg=Colors.TEXT_MUTED,
            bg=Colors.BG_CARD,
            font=Fonts.small(),
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        row += 1

        opts = tk.Frame(frame, bg=Colors.BG_WINDOW)
        opts.grid(row=row, column=0, columnspan=3, sticky="w", pady=(12, 4))
        _cb_kw = dict(
            bg=Colors.BG_WINDOW,
            fg=Colors.TEXT_MAIN,
            activebackground=Colors.BG_WINDOW,
            activeforeground=Colors.TEXT_MAIN,
            selectcolor=Colors.BG_CARD,
            font=Fonts.body(),
            anchor="w",
        )
        tk.Checkbutton(
            opts,
            text="在桌面创建快捷方式",
            variable=shortcut_var,
            **_cb_kw,
        ).pack(anchor="w")
        launch_label = (
            "安装完成后打开桌宠"
            if self.mode == "install"
            else "完成后打开桌宠"
        )
        tk.Checkbutton(
            opts,
            text=launch_label,
            variable=launch_var,
            **_cb_kw,
        ).pack(anchor="w", pady=(4, 0))
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

        def _real_path(var: tk.StringVar, entry: tk.Entry) -> str:
            """去掉占位符，返回用户真实输入。"""
            raw = var.get().strip()
            ph = getattr(entry, "_placeholder_text", None)
            if ph and raw == ph:
                return ""
            if getattr(entry, "_is_placeholder", False):
                return ""
            return raw

        def do_finish() -> None:
            install_raw = _real_path(install_var, install_entry)
            memo_raw = _real_path(memo_var, memo_entry)
            if not install_raw:
                messagebox.showwarning(
                    "提示",
                    "请选择或填写软件安装位置（建议放在 D 盘）。",
                    parent=root,
                )
                return
            if not memo_raw:
                messagebox.showwarning(
                    "提示",
                    "请选择或填写备忘录保存位置（建议放在 D 盘）。",
                    parent=root,
                )
                return

            install_path = Path(install_raw).expanduser()
            memo_path = Path(memo_raw).expanduser()

            # C 盘软提示（不拦截，仅确认）
            if not self._confirm_if_system_drive(root, install_path, "软件安装位置"):
                return
            if not self._confirm_if_system_drive(root, memo_path, "备忘录保存位置"):
                return

            try:
                memo_path.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                messagebox.showerror("错误", f"无法创建备忘录目录：\n{exc}", parent=root)
                return

            src = find_app_source()
            target = install_path
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
            self.should_launch_pet = bool(launch_var.get())
            want_launch = self.should_launch_pet

            # relaunch_exe 仅在「需要另起进程」时设置：
            # - install：安装器进程会退出，由本向导启动（见下方 _launch_pet）
            # - first_run 换目录：调用方启动新位置后退出当前进程
            # - first_run 同目录：relaunch_exe=None，调用方继续跑本进程主程序
            if want_launch and exe and (
                self.mode == "install" or (self.mode == "first_run" and needs_copy)
            ):
                self.relaunch_exe = exe
            else:
                self.relaunch_exe = None

            lines = [
                "设置完成！",
                "",
                f"程序目录：\n{target}",
                "",
                f"备忘录目录：\n{memo_path}",
            ]
            if self.mode == "first_run" and needs_copy:
                lines.insert(1, "程序已复制到新位置。")
            if want_launch and exe and (
                self.mode == "install" or (self.mode == "first_run" and needs_copy)
            ):
                lines.extend(["", "即将打开桌宠…"])
            elif want_launch and self.mode == "first_run" and not needs_copy:
                lines.extend(["", "即将进入桌宠…"])
            elif not want_launch and exe and exe.suffix.lower() == ".exe":
                lines.extend(["", f"以后可运行：\n{exe}"])
            messagebox.showinfo("完成", "\n".join(lines), parent=root)

            # install 模式：向导结束后进程会退出，在此启动桌宠
            if want_launch and exe and self.mode == "install":
                self._launch_pet(exe)
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
        root.bind("<Escape>", lambda _e: do_cancel())
        root.bind("<Return>", lambda _e: do_finish())
        root.mainloop()
        self._root = None
        return self.result_ok

    @staticmethod
    def _confirm_if_system_drive(parent: tk.Tk, path: Path, label: str) -> bool:
        """若路径在 C: 上，提醒建议 D 盘；用户可仍选继续。"""
        try:
            drive = path.expanduser().resolve().drive.upper()
        except OSError:
            drive = str(path)[:2].upper()
        if drive != "C:":
            return True
        return bool(
            messagebox.askyesno(
                "建议使用 D 盘",
                f"{label} 当前在系统盘（C:）：\n{path}\n\n"
                "建议改到 D 盘以减少占满系统盘的风险。\n\n"
                "仍要使用 C 盘吗？",
                parent=parent,
                icon="warning",
            )
        )

    @staticmethod
    def _attach_path_placeholder(entry: tk.Entry, var: tk.StringVar, text: str) -> None:
        """空输入时显示灰色占位（如「例如 D:\\…」），不作为真实路径提交。"""
        muted = Colors.TEXT_MUTED
        normal = Colors.TEXT_MAIN
        entry._placeholder_text = text  # type: ignore[attr-defined]
        entry._is_placeholder = True  # type: ignore[attr-defined]

        def show_ph(_event: object | None = None) -> None:
            if var.get().strip() and not getattr(entry, "_is_placeholder", False):
                return
            if not var.get().strip() or getattr(entry, "_is_placeholder", False):
                entry._is_placeholder = True  # type: ignore[attr-defined]
                var.set(text)
                try:
                    entry.configure(fg=muted)
                except tk.TclError:
                    pass

        def hide_ph(_event: object | None = None) -> None:
            if getattr(entry, "_is_placeholder", False):
                entry._is_placeholder = False  # type: ignore[attr-defined]
                var.set("")
                try:
                    entry.configure(fg=normal)
                except tk.TclError:
                    pass

        entry.bind("<FocusIn>", hide_ph, add="+")
        entry.bind("<FocusOut>", show_ph, add="+")
        show_ph()

    @staticmethod
    def _browse_dir(
        parent: tk.Tk,
        var: tk.StringVar,
        entry: tk.Entry,
        title: str,
    ) -> None:
        raw = var.get().strip()
        ph = getattr(entry, "_placeholder_text", None)
        if getattr(entry, "_is_placeholder", False) or (ph and raw == ph):
            # 建议从 D 盘开始浏览；没有 D: 再用用户主目录
            initial = "D:/" if Path("D:/").exists() else str(Path.home())
        else:
            initial = raw or (str(Path("D:/")) if Path("D:/").exists() else str(Path.home()))
        p = Path(initial)
        if not p.is_dir():
            p = Path("D:/") if Path("D:/").exists() else Path.home()
        chosen = filedialog.askdirectory(
            parent=parent,
            title=title,
            initialdir=str(p),
        )
        if chosen:
            entry._is_placeholder = False  # type: ignore[attr-defined]
            var.set(chosen)
            # 选完目录后 Windows 可能把 Entry 前景改成系统白字，强制恢复可读配色
            try:
                entry.configure(**entry_kwargs())
                entry.icursor("end")
                entry.xview_moveto(1.0)
            except tk.TclError:
                pass

    @staticmethod
    def _launch_pet(entry: Path) -> None:
        """安装完成后启动桌宠（.exe 直接开；.py 用当前解释器）。"""
        try:
            entry = entry.resolve()
            cwd = str(entry.parent)
            if entry.suffix.lower() == ".exe":
                subprocess.Popen([str(entry)], cwd=cwd)
            elif entry.suffix.lower() == ".py":
                subprocess.Popen([sys.executable, str(entry)], cwd=cwd)
            else:
                subprocess.Popen([str(entry)], cwd=cwd)
        except Exception as exc:
            messagebox.showerror("启动失败", f"无法打开桌宠：\n{exc}")


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
