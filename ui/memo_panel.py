"""每日备忘录：序号列表白板 + 历史版本恢复。"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import tkinter as tk
from tkinter import messagebox, ttk

from data.memo_history import (
    HistoryVersion,
    history_dir_for,
    list_versions,
    record_version,
    restore_version,
)

if TYPE_CHECKING:
    from app import DesktopPetApp


# 匹配「1. 」或「- 」列表行
_LIST_LINE_RE = re.compile(r"^(\s*)(?:(\d+)[.)]\s+|([-*+])\s+)(.*)$")
_NUMBERED_RE = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")


def today_note_path(memo_dir: Path, day: date | None = None) -> Path:
    d = day or date.today()
    return Path(memo_dir) / f"{d.isoformat()}.md"


def default_memo_body(day: date) -> str:
    return f"# {day.isoformat()}\n\n1. \n"


def renumber_list_items(text: str) -> str:
    """将正文中的列表项统一为连续序号 1. 2. 3. …（保留非列表行）。"""
    out: list[str] = []
    n = 0
    for line in text.splitlines():
        m = _LIST_LINE_RE.match(line)
        if m:
            indent, _num, _bullet, body = m.group(1), m.group(2), m.group(3), m.group(4)
            n += 1
            out.append(f"{indent}{n}. {body}")
        else:
            out.append(line)
    result = "\n".join(out)
    if text.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result


def load_or_create_memo_text(path: Path, day: date | None = None) -> str:
    d = day or date.today()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8")
            if text.strip():
                return text if text.endswith("\n") else text + "\n"
        except OSError:
            pass
    body = default_memo_body(d)
    try:
        path.write_text(body, encoding="utf-8")
    except OSError:
        pass
    return body


def save_memo_text(path: Path, text: str, *, snapshot: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text = text + "\n"
    path.write_text(text, encoding="utf-8")
    if snapshot:
        record_version(path, text)


def open_path_externally(path: Path) -> None:
    path = Path(path)
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def open_folder_externally(path: Path, *, select_file: Path | None = None) -> None:
    """
    在资源管理器中打开文件夹。
    Windows 若提供 select_file，会定位并选中该文件。
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        if select_file is not None and Path(select_file).exists():
            # /select, 后不要多余空格写进路径
            subprocess.Popen(["explorer", f"/select,{Path(select_file).resolve()}"])
        else:
            os.startfile(str(path.resolve()))  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        if select_file is not None and Path(select_file).exists():
            subprocess.Popen(["open", "-R", str(Path(select_file).resolve())])
        else:
            subprocess.Popen(["open", str(path.resolve())])
        return
    subprocess.Popen(["xdg-open", str(path.resolve())])


class MemoPanel:
    """今日备忘录：序号白板 + 历史版本。"""

    def __init__(self, app: DesktopPetApp) -> None:
        self.app = app
        self.win: tk.Toplevel | None = None
        self._day = date.today()
        self._text: tk.Text | None = None
        self._path_var = tk.StringVar()
        self._status_var = tk.StringVar(value="")
        self._dirty = False
        self._autosave_job: str | None = None
        self._loading = False
        self._history_win: tk.Toplevel | None = None
        self._hist_list: tk.Listbox | None = None
        self._hist_detail: tk.Text | None = None
        self._hist_versions: list[HistoryVersion] = []

    def open(self) -> None:
        if self.win and self.win.winfo_exists():
            self.win.lift()
            self.win.focus_force()
            if self._text:
                self._text.focus_set()
            return

        self._day = date.today()
        win = tk.Toplevel(self.app.root)
        win.title(f"备忘录 · {self._day.isoformat()}")
        win.attributes("-topmost", True)
        win.minsize(520, 460)
        win.geometry("600x600")
        win.protocol("WM_DELETE_WINDOW", self.close)
        self.win = win

        win.columnconfigure(0, weight=1)
        win.rowconfigure(2, weight=1)

        top = ttk.Frame(win, padding=(12, 10, 12, 4))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        ttk.Label(
            top,
            text=f"今日笔记  {self._day.isoformat()}.md",
            font=("Microsoft YaHei UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w")
        btns = ttk.Frame(top)
        btns.grid(row=0, column=1, sticky="e")
        ttk.Button(btns, text="历史版本", command=self.open_history, width=10).pack(side="left", padx=2)
        ttk.Button(btns, text="打开文件夹", command=self.open_memo_folder, width=10).pack(side="left", padx=2)
        ttk.Button(btns, text="刷新", command=self.reload, width=8).pack(side="left", padx=2)
        ttk.Button(btns, text="外部打开", command=self.open_external, width=10).pack(side="left", padx=2)

        path_row = ttk.Frame(win, padding=(12, 0, 12, 4))
        path_row.grid(row=1, column=0, sticky="ew")
        path_row.columnconfigure(0, weight=1)
        ttk.Label(
            path_row,
            textvariable=self._path_var,
            foreground="#666666",
            font=("Consolas", 8),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            path_row,
            text="默认序号列表 · 回车自动下一项 · 保存时重排序号 · 历史可恢复误删",
            foreground="#888888",
            font=("Microsoft YaHei UI", 8),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        board = ttk.Frame(win, padding=(12, 4, 12, 4))
        board.grid(row=2, column=0, sticky="nsew")
        board.columnconfigure(0, weight=1)
        board.rowconfigure(0, weight=1)

        scroll = ttk.Scrollbar(board, orient="vertical")
        text = tk.Text(
            board,
            wrap="word",
            undo=True,
            maxundo=-1,
            font=("Microsoft YaHei UI", 11),
            bg="#FFFEF7",
            fg="#1a1a1a",
            insertbackground="#222222",
            selectbackground="#FFE082",
            selectforeground="#000000",
            relief="solid",
            borderwidth=1,
            padx=14,
            pady=12,
            spacing1=2,
            spacing3=4,
            yscrollcommand=scroll.set,
        )
        scroll.config(command=text.yview)
        text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self._text = text

        text.bind("<<Modified>>", self._on_modified)
        text.bind("<Control-s>", self._on_ctrl_s)
        text.bind("<Control-S>", self._on_ctrl_s)
        text.bind("<Return>", self._on_return)
        text.bind("<Button-1>", lambda _e: text.focus_set(), add="+")

        bottom = ttk.Frame(win, padding=(12, 6, 12, 12))
        bottom.grid(row=3, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        ttk.Label(bottom, textvariable=self._status_var, foreground="#555555").grid(
            row=0, column=0, sticky="w"
        )
        action = ttk.Frame(bottom)
        action.grid(row=0, column=1, sticky="e")
        ttk.Button(action, text="重排序号", command=self.renumber_now, width=10).pack(side="left", padx=3)
        ttk.Button(action, text="保存", command=lambda: self.save(quiet=False), width=8).pack(
            side="left", padx=3
        )
        ttk.Button(action, text="关闭", command=self.close, width=8).pack(side="left", padx=3)

        self.reload()
        text.focus_set()
        text.mark_set(tk.INSERT, "end-1c")
        text.see(tk.INSERT)

        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        ww, wh = 600, 600
        win.geometry(f"{ww}x{wh}+{(sw - ww) // 2}+{(sh - wh) // 2}")

    def _note_path(self) -> Path:
        return today_note_path(self.app.settings.memo_dir, self._day)

    def _get_body(self) -> str:
        if not self._text:
            return ""
        return self._text.get("1.0", "end-1c")

    def _set_body(self, body: str, *, cursor_end: bool = False) -> None:
        if not self._text:
            return
        self._loading = True
        self._text.delete("1.0", tk.END)
        self._text.insert("1.0", body)
        self._text.edit_modified(False)
        self._loading = False
        if cursor_end:
            self._text.mark_set(tk.INSERT, "end-1c")
            self._text.see(tk.INSERT)

    def reload(self) -> None:
        if not self._text:
            return
        self._day = date.today()
        path = self._note_path()
        body = load_or_create_memo_text(path, self._day)
        # 若还是旧 bullet 模板，转成序号
        if re.search(r"^-\s", body, re.M) and not re.search(r"^\d+[.)]\s", body, re.M):
            body = renumber_list_items(body)
        self._path_var.set(str(path))
        self._set_body(body)
        self._dirty = False
        self._status_var.set("已加载 · 点击白板直接编辑 · 改动会记入历史版本")
        if self.win and self.win.winfo_exists():
            self.win.title(f"备忘录 · {self._day.isoformat()}")

    def renumber_now(self) -> None:
        if not self._text:
            return
        body = renumber_list_items(self._get_body())
        insert = self._text.index(tk.INSERT)
        self._set_body(body)
        try:
            self._text.mark_set(tk.INSERT, insert)
        except tk.TclError:
            pass
        self._dirty = True
        self.save(quiet=True)
        self._status_var.set("已重排序号并保存")

    def _on_return(self, _event: object | None = None) -> str | None:
        """在序号行回车 → 自动插入下一项序号。"""
        if not self._text:
            return None
        line_start = self._text.index("insert linestart")
        line_end = self._text.index("insert lineend")
        line = self._text.get(line_start, line_end)
        m = _NUMBERED_RE.match(line)
        if not m:
            return None  # 默认换行
        indent, num_s, body = m.group(1), m.group(2), m.group(3)
        # 空序号行再回车：结束列表
        if not body.strip():
            self._text.delete(line_start, line_end)
            self._text.insert(line_start, "")
            return None
        try:
            nxt = int(num_s) + 1
        except ValueError:
            nxt = 1
        self._text.insert(tk.INSERT, f"\n{indent}{nxt}. ")
        return "break"

    def _on_modified(self, _event: object | None = None) -> None:
        if not self._text or self._loading:
            return
        if not self._text.edit_modified():
            return
        self._text.edit_modified(False)
        self._dirty = True
        self._status_var.set("已修改 · 自动保存中…")
        self._schedule_autosave()

    def _schedule_autosave(self) -> None:
        if not self.win:
            return
        if self._autosave_job:
            try:
                self.win.after_cancel(self._autosave_job)
            except Exception:
                pass
        self._autosave_job = self.win.after(700, self._autosave)

    def _autosave(self) -> None:
        self._autosave_job = None
        if self._dirty:
            self.save(quiet=True)

    def _on_ctrl_s(self, _event: object | None = None) -> str:
        self.save(quiet=True)
        return "break"

    def save(self, quiet: bool = False, *, renumber: bool = True) -> None:
        if not self._text:
            return
        path = self._note_path()
        body = self._get_body()
        if renumber:
            body = renumber_list_items(body)
            # 序号规范化后回写白板，尽量保持光标
            if body != self._get_body():
                insert = self._text.index(tk.INSERT)
                self._set_body(body)
                try:
                    self._text.mark_set(tk.INSERT, insert)
                except tk.TclError:
                    pass
        try:
            save_memo_text(path, body, snapshot=True)
            self._dirty = False
            self._path_var.set(str(path))
            self._status_var.set(f"已保存 · {path.name}（已记历史）")
            if not quiet:
                messagebox.showinfo("备忘录", f"已保存：\n{path}", parent=self.win)
            if self._history_win and self._history_win.winfo_exists():
                self._refresh_history_list()
        except OSError as exc:
            self._status_var.set("保存失败")
            messagebox.showerror("保存失败", str(exc), parent=self.win)

    def open_external(self) -> None:
        path = self._note_path()
        try:
            if self._dirty:
                self.save(quiet=True)
            elif not path.exists():
                save_memo_text(path, self._get_body() or default_memo_body(self._day))
            open_path_externally(path)
        except OSError as exc:
            messagebox.showerror("打开失败", str(exc), parent=self.win)

    def open_memo_folder(self) -> None:
        """在资源管理器中打开备忘录目录，并尽量选中今日笔记。"""
        path = self._note_path()
        try:
            folder = path.parent
            folder.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                save_memo_text(path, self._get_body() or default_memo_body(self._day), snapshot=False)
            open_folder_externally(folder, select_file=path if path.exists() else None)
            self._status_var.set(f"已打开文件夹 · {folder}")
        except OSError as exc:
            messagebox.showerror("打开文件夹失败", str(exc), parent=self.win)

    def open_history_folder(self) -> None:
        """打开当前笔记的历史版本快照目录。"""
        note = self._note_path()
        hdir = history_dir_for(note)
        try:
            hdir.mkdir(parents=True, exist_ok=True)
            open_folder_externally(hdir)
            parent = self._history_win or self.win
            if parent and self._status_var:
                self._status_var.set(f"已打开历史目录 · {hdir}")
        except OSError as exc:
            messagebox.showerror(
                "打开历史文件夹失败",
                str(exc),
                parent=self._history_win or self.win,
            )

    # ------------------------------------------------------------------
    # 历史版本
    # ------------------------------------------------------------------
    def open_history(self) -> None:
        if self._dirty:
            self.save(quiet=True)

        if self._history_win and self._history_win.winfo_exists():
            self._history_win.lift()
            self._refresh_history_list()
            return

        parent = self.win or self.app.root
        hw = tk.Toplevel(parent)
        hw.title("备忘录历史版本")
        hw.attributes("-topmost", True)
        hw.geometry("640x480")
        hw.minsize(520, 360)
        hw.protocol("WM_DELETE_WINDOW", self._close_history)
        self._history_win = hw

        hw.columnconfigure(0, weight=1)
        hw.columnconfigure(1, weight=2)
        hw.rowconfigure(1, weight=1)

        header = ttk.Frame(hw, padding=(10, 10, 10, 4))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="类似 GitHub 的增删记录 · 选中版本可预览并恢复（防误删）",
            font=("Microsoft YaHei UI", 9),
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            header,
            text="打开历史文件夹",
            command=self.open_history_folder,
            width=14,
        ).grid(row=0, column=1, sticky="e", padx=(8, 0))
        ttk.Button(
            header,
            text="打开笔记文件夹",
            command=self.open_memo_folder,
            width=14,
        ).grid(row=0, column=2, sticky="e", padx=(4, 0))

        left = ttk.Frame(hw, padding=(10, 0, 6, 10))
        left.grid(row=1, column=0, sticky="nsew")
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        scroll_l = ttk.Scrollbar(left)
        lb = tk.Listbox(left, font=("Consolas", 9), yscrollcommand=scroll_l.set, exportselection=False)
        scroll_l.config(command=lb.yview)
        lb.grid(row=0, column=0, sticky="nsew")
        scroll_l.grid(row=0, column=1, sticky="ns")
        lb.bind("<<ListboxSelect>>", self._on_history_select)
        self._hist_list = lb

        right = ttk.Frame(hw, padding=(6, 0, 10, 10))
        right.grid(row=1, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        scroll_r = ttk.Scrollbar(right)
        detail = tk.Text(
            right,
            wrap="word",
            font=("Microsoft YaHei UI", 10),
            bg="#F7F9FC",
            yscrollcommand=scroll_r.set,
            state="disabled",
        )
        scroll_r.config(command=detail.yview)
        detail.grid(row=0, column=0, sticky="nsew")
        scroll_r.grid(row=0, column=1, sticky="ns")
        self._hist_detail = detail

        bar = ttk.Frame(hw, padding=10)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Button(bar, text="恢复此版本", command=self._restore_selected).pack(side="left", padx=4)
        ttk.Button(bar, text="刷新列表", command=self._refresh_history_list).pack(side="left", padx=4)
        ttk.Button(bar, text="打开历史文件夹", command=self.open_history_folder).pack(side="left", padx=4)
        ttk.Button(bar, text="打开笔记文件夹", command=self.open_memo_folder).pack(side="left", padx=4)
        ttk.Button(bar, text="关闭", command=self._close_history).pack(side="right", padx=4)

        self._refresh_history_list()
        hw.update_idletasks()
        sw, sh = hw.winfo_screenwidth(), hw.winfo_screenheight()
        hw.geometry(f"640x480+{(sw - 640) // 2}+{(sh - 480) // 2}")

    def _refresh_history_list(self) -> None:
        if not self._hist_list:
            return
        path = self._note_path()
        self._hist_versions = list_versions(path)
        self._hist_list.delete(0, tk.END)
        if not self._hist_versions:
            self._hist_list.insert(tk.END, "（暂无历史 · 保存后会出现）")
            return
        for v in self._hist_versions:
            self._hist_list.insert(tk.END, f"{v.time}  {v.summary}")

    def _on_history_select(self, _event: object | None = None) -> None:
        if not self._hist_list or not self._hist_detail or not self._hist_versions:
            return
        sel = self._hist_list.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < 0 or idx >= len(self._hist_versions):
            return
        v = self._hist_versions[idx]
        from data.memo_history import read_version_content

        content = read_version_content(self._note_path(), v) or "（快照文件丢失）"
        lines = [
            f"时间：{v.time}",
            f"摘要：{v.summary}",
            f"版本：{v.id}",
            "",
            "—— 增删记录 ——",
        ]
        if v.added:
            for a in v.added:
                lines.append(f"+ {a}")
        if v.removed:
            for r in v.removed:
                lines.append(f"- {r}")
        if not v.added and not v.removed:
            lines.append("（无列表项增删，或为正文微调 / 初始版）")
        lines.extend(["", "—— 全文快照 ——", content])
        self._hist_detail.configure(state="normal")
        self._hist_detail.delete("1.0", tk.END)
        self._hist_detail.insert("1.0", "\n".join(lines))
        self._hist_detail.configure(state="disabled")

    def _restore_selected(self) -> None:
        if not self._hist_list or not self._hist_versions:
            return
        sel = self._hist_list.curselection()
        if not sel:
            messagebox.showinfo("历史版本", "请先选择一个版本。", parent=self._history_win)
            return
        idx = int(sel[0])
        if idx < 0 or idx >= len(self._hist_versions):
            return
        v = self._hist_versions[idx]
        if not messagebox.askyesno(
            "恢复版本",
            f"确定恢复到：\n{v.time}\n{v.summary}\n\n当前内容会先记入历史，可再回退。",
            parent=self._history_win,
        ):
            return
        try:
            content = restore_version(self._note_path(), v)
            if self._text:
                self._set_body(content)
                self._dirty = False
            self._status_var.set(f"已恢复 · {v.time}")
            self._refresh_history_list()
            messagebox.showinfo("历史版本", "已恢复该版本到白板与笔记文件。", parent=self._history_win)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("恢复失败", str(exc), parent=self._history_win)

    def _close_history(self) -> None:
        if self._history_win is not None:
            try:
                self._history_win.destroy()
            except tk.TclError:
                pass
            self._history_win = None
            self._hist_list = None
            self._hist_detail = None
            self._hist_versions = []

    def close(self) -> None:
        if self._autosave_job and self.win:
            try:
                self.win.after_cancel(self._autosave_job)
            except Exception:
                pass
            self._autosave_job = None
        if self._dirty:
            try:
                body = renumber_list_items(self._get_body())
                save_memo_text(self._note_path(), body, snapshot=True)
            except OSError:
                pass
            self._dirty = False
        self._close_history()
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None
            self._text = None
