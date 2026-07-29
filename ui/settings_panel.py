"""主设置：备忘录目录 + 开机自启 + GitHub 更新（含加速代理）。"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import sys

from data.settings import default_memo_dir
from utils import autostart
from utils.updater import (
    BUILTIN_GH_PROXIES,
    check_update,
    download_and_apply,
    proxy_chain_from_settings,
    read_local_version,
)


def sys_platform_is_win() -> bool:
    return sys.platform.startswith("win")

if TYPE_CHECKING:
    from app import DesktopPetApp


class SettingsPanel:
    def __init__(self, app: DesktopPetApp) -> None:
        self.app = app
        self.win: tk.Toplevel | None = None
        self._path_var = tk.StringVar()
        self._repo_var = tk.StringVar()
        self._branch_var = tk.StringVar()
        self._proxy_var = tk.StringVar()
        self._custom_proxy_var = tk.StringVar()
        self._update_status = tk.StringVar()
        self._version_var = tk.StringVar()
        self._autostart_var = tk.BooleanVar(value=False)
        self._autostart_hint = tk.StringVar()
        self._auto_restart_var = tk.BooleanVar(value=True)
        self._busy = False

    def open(self) -> None:
        if self.win and self.win.winfo_exists():
            self.win.lift()
            self._load_fields()
            return

        win = tk.Toplevel(self.app.root)
        win.title("主设置")
        win.attributes("-topmost", True)
        win.minsize(520, 520)
        win.resizable(True, True)
        win.protocol("WM_DELETE_WINDOW", self.close)
        self.win = win

        # 可滚动主区域
        canvas = tk.Canvas(win, highlightthickness=0)
        scroll = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas, padding=14)
        frame.bind(
            "<Configure>",
            lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        def _on_mousewheel(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        win.bind("<Destroy>", lambda _e: canvas.unbind_all("<MouseWheel>"), add="+")

        ttk.Label(
            frame,
            text="主设置",
            font=("Microsoft YaHei UI", 12, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        char = self.app.character
        ttk.Label(
            frame,
            text=f"当前角色：{char.name}（{char.id}）",
            foreground="#1565C0",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))

        # ---- 备忘录目录 ----
        box = ttk.LabelFrame(frame, text="Obsidian / 备忘录笔记目录", padding=10)
        box.grid(row=2, column=0, columnspan=3, sticky="ew", pady=4)
        box.columnconfigure(0, weight=1)

        ttk.Label(
            box,
            text="每日笔记：日期.md（如 2026-07-30.md）· 序号列表 · 历史版本在应用 data_store/memo_history",
            justify="left",
            foreground="#444444",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Entry(box, textvariable=self._path_var, width=48).grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=(0, 6)
        )
        ttk.Button(box, text="浏览…", command=self._browse, width=8).grid(row=1, column=2, sticky="e")
        ttk.Button(box, text="恢复默认目录", command=self._reset_default).grid(
            row=2, column=0, sticky="w", pady=(8, 0)
        )

        # ---- 开机自启 / 退出 ----
        gen = ttk.LabelFrame(frame, text="启动与退出", padding=10)
        gen.grid(row=3, column=0, columnspan=3, sticky="ew", pady=8)
        gen.columnconfigure(0, weight=1)

        cb = ttk.Checkbutton(
            gen,
            text="开机自启（登录 Windows 后自动运行桌宠）",
            variable=self._autostart_var,
            command=self._on_autostart_toggle,
        )
        cb.grid(row=0, column=0, sticky="w")
        ttk.Label(
            gen,
            textvariable=self._autostart_hint,
            foreground="#666666",
            wraplength=460,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(4, 8))
        ttk.Button(
            gen,
            text="退出桌宠",
            command=self._quit_app,
            width=14,
        ).grid(row=2, column=0, sticky="w")

        # ---- 软件更新 ----
        upd = ttk.LabelFrame(frame, text="软件更新（GitHub）", padding=10)
        upd.grid(row=4, column=0, columnspan=3, sticky="ew", pady=8)
        upd.columnconfigure(1, weight=1)

        self._version_var.set(f"本地版本：{read_local_version()}")
        ttk.Label(upd, textvariable=self._version_var, foreground="#1565C0").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )

        ttk.Label(upd, text="仓库").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(upd, textvariable=self._repo_var, width=36).grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=3
        )
        ttk.Label(upd, text="分支").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(upd, textvariable=self._branch_var, width=16).grid(
            row=2, column=1, sticky="w", pady=3
        )

        ttk.Label(upd, text="加速代理").grid(row=3, column=0, sticky="w", pady=3)
        self._proxy_combo = ttk.Combobox(upd, textvariable=self._proxy_var, width=42, state="readonly")
        self._proxy_combo.grid(row=3, column=1, columnspan=2, sticky="ew", pady=3)

        ttk.Label(
            upd,
            text="自定义代理（每行一个完整前缀 URL，可追加）",
            foreground="#555555",
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 2))
        self._custom_text = tk.Text(upd, height=3, width=52, font=("Consolas", 9))
        self._custom_text.grid(row=5, column=0, columnspan=3, sticky="ew", pady=2)

        ttk.Label(
            upd,
            text="检查/更新时按：首选代理 → 自定义 → 内置代理 → 直连 依次尝试。",
            foreground="#888888",
            font=("Microsoft YaHei UI", 8),
        ).grid(row=6, column=0, columnspan=3, sticky="w", pady=(4, 6))

        ttk.Checkbutton(
            upd,
            text="更新后自动重启（推荐 · 默认开）",
            variable=self._auto_restart_var,
            command=self._on_auto_restart_toggle,
        ).grid(row=7, column=0, columnspan=3, sticky="w", pady=(4, 0))
        ttk.Label(
            upd,
            text="开启时：点「立即更新」装完后会强制结束旧进程并启动新桌宠，你不用手动退出。",
            foreground="#1565C0",
            font=("Microsoft YaHei UI", 8),
            wraplength=460,
        ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(2, 6))

        btn_row = ttk.Frame(upd)
        btn_row.grid(row=9, column=0, columnspan=3, sticky="w", pady=4)
        ttk.Button(btn_row, text="检查更新", command=self._check_update, width=12).pack(
            side="left", padx=3
        )
        ttk.Button(btn_row, text="立即更新", command=self._do_update, width=12).pack(
            side="left", padx=3
        )
        ttk.Button(btn_row, text="打开仓库页", command=self._open_repo_page, width=12).pack(
            side="left", padx=3
        )

        ttk.Label(upd, textvariable=self._update_status, foreground="#333333", wraplength=460).grid(
            row=10, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )

        tip = ttk.Label(
            frame,
            text="热键：Ctrl+Shift+D 生成道具 · Ctrl+Shift+P 面板 · Ctrl+Shift+C 角色\n"
            "更新不会覆盖 data_store；是否自动重启可在上方勾选。\n"
            "退出：本页或控制面板底部「退出桌宠」。",
            foreground="#666666",
            justify="left",
        )
        tip.grid(row=5, column=0, columnspan=3, sticky="w", pady=(12, 4))

        setup_row = ttk.Frame(frame)
        setup_row.grid(row=6, column=0, columnspan=3, sticky="w", pady=(4, 0))
        ttk.Button(
            setup_row,
            text="重新运行安装/路径向导…",
            command=self._rerun_setup,
            width=22,
        ).pack(side="left")

        btns = ttk.Frame(frame)
        btns.grid(row=7, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(btns, text="保存设置", command=self._save, width=12).pack(side="left", padx=4)
        ttk.Button(btns, text="关闭", command=self.close, width=10).pack(side="left", padx=4)

        self._load_fields()
        self._update_status.set("就绪")

        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        ww, wh = 560, 640
        win.geometry(f"{ww}x{wh}+{(sw - ww) // 2}+{(sh - wh) // 2}")

    def _proxy_choices(self) -> list[str]:
        choices = ["(直连)"] + list(BUILTIN_GH_PROXIES)
        for c in self.app.settings.custom_gh_proxies:
            if c and c not in choices:
                choices.append(c)
        # 当前值若自定义也要出现
        cur = self.app.settings.gh_proxy
        if cur and cur not in choices and cur.lower() not in ("direct", "none", "直连"):
            choices.append(cur)
        return choices

    def _load_fields(self) -> None:
        s = self.app.settings
        self._path_var.set(str(s.memo_dir))
        self._repo_var.set(s.github_repo)
        self._branch_var.set(s.github_branch)
        self._version_var.set(f"本地版本：{read_local_version()}")
        choices = self._proxy_choices()
        self._proxy_combo["values"] = choices
        cur = s.gh_proxy
        if not cur or cur.lower() in ("direct", "none", "直连"):
            self._proxy_var.set("(直连)")
        elif cur in choices:
            self._proxy_var.set(cur)
        else:
            self._proxy_var.set(choices[1] if len(choices) > 1 else "(直连)")
        if hasattr(self, "_custom_text") and self._custom_text:
            self._custom_text.delete("1.0", tk.END)
            self._custom_text.insert("1.0", "\n".join(s.custom_gh_proxies))
        # 开机自启：以系统 Startup 快捷方式为准，并同步到设置
        enabled = autostart.is_enabled()
        self._autostart_var.set(enabled)
        if s.autostart != enabled:
            s.autostart = enabled
        self._refresh_autostart_hint()
        self._auto_restart_var.set(s.auto_restart_after_update)

    def _selected_proxy(self) -> str:
        v = self._proxy_var.get().strip()
        if v in ("(直连)", "直连", "direct", "none", ""):
            return ""
        return v

    def _read_custom_proxies(self) -> list[str]:
        if not hasattr(self, "_custom_text") or not self._custom_text:
            return self.app.settings.custom_gh_proxies
        raw = self._custom_text.get("1.0", "end-1c")
        return [ln.strip() for ln in raw.splitlines() if ln.strip()]

    def _browse(self) -> None:
        initial = self._path_var.get().strip() or str(default_memo_dir())
        initial_path = Path(initial)
        if not initial_path.is_dir():
            initial_path = default_memo_dir()
            initial_path.mkdir(parents=True, exist_ok=True)
        chosen = filedialog.askdirectory(
            parent=self.win,
            title="选择 Obsidian / 备忘录目录",
            initialdir=str(initial_path),
        )
        if chosen:
            self._path_var.set(chosen)

    def _reset_default(self) -> None:
        path = default_memo_dir()
        path.mkdir(parents=True, exist_ok=True)
        self._path_var.set(str(path))

    def _save(self) -> None:
        raw = self._path_var.get().strip()
        if not raw:
            messagebox.showwarning("主设置", "请填写笔记目录路径。", parent=self.win)
            return
        path = Path(raw).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("主设置", f"无法创建目录：\n{exc}", parent=self.win)
            return
        if not path.is_dir():
            messagebox.showerror("主设置", "路径不是有效文件夹。", parent=self.win)
            return

        s = self.app.settings
        s.memo_dir = path
        s.github_repo = self._repo_var.get().strip()
        s.github_branch = self._branch_var.get().strip() or "main"
        s.gh_proxy = self._selected_proxy() or "direct"
        s.custom_gh_proxies = self._read_custom_proxies()
        s.auto_restart_after_update = bool(self._auto_restart_var.get())
        # 开机自启：保存时再同步一次（勾选时已即时生效）
        want = bool(self._autostart_var.get())
        ok, msg = autostart.set_enabled(want)
        s.autostart = want and ok
        if not ok and want:
            self._autostart_var.set(False)
            messagebox.showwarning("开机自启", msg, parent=self.win)
            return
        self._refresh_autostart_hint()
        # 刷新下拉
        self._proxy_combo["values"] = self._proxy_choices()
        messagebox.showinfo("主设置", "设置已保存。", parent=self.win)

    def _refresh_autostart_hint(self) -> None:
        if not sys_platform_is_win():
            self._autostart_hint.set("当前系统非 Windows，开机自启不可用。")
            return
        sc = autostart.shortcut_path()
        if self._autostart_var.get() and autostart.is_enabled():
            self._autostart_hint.set(f"已启用 · 启动项：{sc}")
        elif self._autostart_var.get():
            self._autostart_hint.set("已勾选，但启动项未写入成功，请重新勾选或点「保存设置」。")
        else:
            self._autostart_hint.set("未启用。勾选后会在「启动」文件夹创建 DesktopPet 快捷方式。")

    def _on_autostart_toggle(self) -> None:
        want = bool(self._autostart_var.get())
        ok, msg = autostart.set_enabled(want)
        self.app.settings.autostart = want and ok
        if not ok:
            self._autostart_var.set(False)
            self.app.settings.autostart = False
            messagebox.showwarning("开机自启", msg, parent=self.win)
        self._refresh_autostart_hint()

    def _on_auto_restart_toggle(self) -> None:
        self.app.settings.auto_restart_after_update = bool(self._auto_restart_var.get())

    def _quit_app(self) -> None:
        self.app.quit_app(confirm=True)

    def _proxy_chain(self) -> list[str]:
        return proxy_chain_from_settings(
            self._selected_proxy(),
            self._read_custom_proxies(),
            include_direct=True,
        )

    def _set_status(self, text: str) -> None:
        def _apply() -> None:
            self._update_status.set(text)
            self._version_var.set(f"本地版本：{read_local_version()}")

        if self.win and self.win.winfo_exists():
            self.win.after(0, _apply)

    def _check_update(self) -> None:
        if self._busy:
            return
        self._save_update_fields_silent()
        self._busy = True
        self._set_status("正在检查更新…")

        def work() -> None:
            try:
                info = check_update(
                    repo=self.app.settings.github_repo,
                    branch=self.app.settings.github_branch,
                    proxies=self._proxy_chain(),
                )
                msg = (
                    f"{info.message}\n"
                    f"本地 {info.local_version} → 远程 {info.remote_version}\n"
                    f"仓库 {info.repo}@{info.branch}"
                )
                self._set_status(msg)

                def _popup() -> None:
                    if info.remote_version == "?":
                        messagebox.showerror("检查更新", info.message, parent=self.win)
                    elif info.has_update:
                        messagebox.showinfo("检查更新", msg + "\n\n可点击「立即更新」。", parent=self.win)
                    else:
                        messagebox.showinfo("检查更新", msg, parent=self.win)

                if self.win:
                    self.win.after(0, _popup)
            finally:
                self._busy = False

        threading.Thread(target=work, daemon=True).start()

    def _do_update(self) -> None:
        if self._busy:
            return
        # 默认强制走自动重启；仅当用户主动取消勾选时才手动退出
        do_restart = bool(self._auto_restart_var.get())
        self.app.settings.auto_restart_after_update = do_restart
        if do_restart:
            restart_hint = (
                "【自动重启已开启】\n"
                "安装完成后会自动结束当前桌宠并启动新版本，\n"
                "你不需要手动关闭。"
            )
        else:
            restart_hint = (
                "【自动重启已关闭】\n"
                "装完后需自己点「退出桌宠」再打开。\n"
                "若关不掉，请勾选上方「更新后自动重启」后再更新。"
            )
        if not messagebox.askyesno(
            "立即更新",
            "将从 GitHub 下载最新代码并覆盖程序文件。\n"
            "data_store（设置/日志/备忘录历史）不会被覆盖。\n\n"
            f"{restart_hint}\n\n是否继续？",
            parent=self.win,
        ):
            return
        self._save_update_fields_silent()
        self._busy = True
        self._set_status("正在下载并安装更新…")

        def work() -> None:
            try:
                # 安装成功后立刻写独立脚本：taskkill 旧 PID → 启动新桌宠
                used = download_and_apply(
                    repo=self.app.settings.github_repo,
                    branch=self.app.settings.github_branch,
                    proxies=self._proxy_chain(),
                    progress=lambda m: self._set_status(m),
                    auto_restart=do_restart,
                    allow_downgrade=False,
                    restart_delay_sec=2.0,
                )
                ver = read_local_version()
                if do_restart:
                    self._set_status(
                        f"更新完成 · VERSION={ver}\n来源: {used}\n"
                        "正在自动重启：约 2 秒后结束本进程并启动新桌宠（无需你操作）。"
                    )

                    def _auto_only() -> None:
                        # 不弹「请关闭」对话框——独立脚本会强制结束本进程
                        # 尝试优雅退出；失败也没关系，taskkill 会兜底
                        try:
                            self.app.quit_app(confirm=False)
                        except Exception:
                            pass

                    root = self.app.root
                    if root:
                        # 给状态文案一点时间刷新，再软退出
                        root.after(200, _auto_only)
                else:
                    self._set_status(
                        f"更新完成 · VERSION={ver}\n来源: {used}\n"
                        "未勾选自动重启：请点「退出桌宠」后重新运行。"
                    )

                    def _popup_manual() -> None:
                        parent = self.win if self.win and self.win.winfo_exists() else None
                        messagebox.showinfo(
                            "更新完成",
                            f"已更新到 VERSION {ver}\n\n"
                            "当前未开启「更新后自动重启」。\n"
                            "请点控制面板「退出桌宠」，再重新运行。\n\n"
                            "若希望下次不用手动关：请勾选上方自动重启后再更新。",
                            parent=parent,
                        )

                    root = self.app.root
                    if root:
                        root.after(0, _popup_manual)
            except Exception as exc:  # noqa: BLE001
                self._set_status(f"更新失败: {exc}")

                def _err() -> None:
                    messagebox.showerror("更新失败", str(exc), parent=self.win)

                if self.win:
                    self.win.after(0, _err)
                else:
                    self.app.root.after(0, _err)
            finally:
                self._busy = False

        threading.Thread(target=work, daemon=True).start()

    def _save_update_fields_silent(self) -> None:
        s = self.app.settings
        if self._repo_var.get().strip():
            s.github_repo = self._repo_var.get().strip()
        if self._branch_var.get().strip():
            s.github_branch = self._branch_var.get().strip()
        s.gh_proxy = self._selected_proxy() or "direct"
        s.custom_gh_proxies = self._read_custom_proxies()
        s.auto_restart_after_update = bool(self._auto_restart_var.get())

    def _open_repo_page(self) -> None:
        import webbrowser

        repo = self._repo_var.get().strip() or self.app.settings.github_repo
        url = f"https://github.com/{repo.removeprefix('https://github.com/').strip('/')}"
        webbrowser.open(url)

    def _rerun_setup(self) -> None:
        from ui.setup_wizard import SetupWizard

        # 允许改安装位置：完整安装；仅改路径用 first_run 也可
        if not messagebox.askyesno(
            "安装向导",
            "将打开安装向导。\n"
            "「完整安装」可复制到新目录；完成后请从新位置启动。\n\n是否继续？",
            parent=self.win,
        ):
            return
        self.close()
        SetupWizard(mode="install").run()
        # 刷新当前设置显示
        self.app.apply_reminder_schedules()
        try:
            self.open()
        except Exception:
            pass

    def close(self) -> None:
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None
