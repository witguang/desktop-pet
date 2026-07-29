
"""角色切换面板 — 浏览 characters/ 下所有角色包并一键切换。"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from core.character_pack import CharacterPack, discover_characters
from utils.asset_loader import AssetLoader

if TYPE_CHECKING:
    from app import DesktopPetApp


class CharacterPicker:
    def __init__(self, app: DesktopPetApp) -> None:
        self.app = app
        self.win: tk.Toplevel | None = None
        self._preview_refs: list = []  # 防止 PhotoImage 被回收
        self._cards: list[ttk.Frame] = []

    def open(self) -> None:
        if self.win and self.win.winfo_exists():
            self.win.lift()
            self.refresh()
            return

        win = tk.Toplevel(self.app.root)
        win.title("切换角色 · Character Packs")
        win.attributes("-topmost", True)
        win.geometry("480x420")
        win.protocol("WM_DELETE_WINDOW", self.close)
        self.win = win

        header = ttk.Frame(win, padding=10)
        header.pack(fill="x")
        ttk.Label(
            header,
            text="选择角色包（放入 characters/ 即可被发现）",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(side="left")
        ttk.Button(header, text="刷新", command=self.refresh).pack(side="right", padx=4)
        ttk.Button(header, text="打开角色目录", command=self._open_folder).pack(side="right")

        tip = ttk.Label(
            win,
            text="提示：复制 characters/_template 并替换图片，即可自定义新角色，无需改代码。",
            foreground="#555555",
            padding=(10, 0),
        )
        tip.pack(fill="x")

        canvas_frame = ttk.Frame(win)
        canvas_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.list_frame = ttk.Frame(self.canvas)
        self.list_frame.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self._list_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.status_var = tk.StringVar()
        ttk.Label(win, textvariable=self.status_var, padding=8).pack(fill="x")

        self.refresh()

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._list_window, width=event.width)

    def _open_folder(self) -> None:
        from config import CHARACTERS_DIR
        import os
        import subprocess
        import sys

        CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
        path = str(CHARACTERS_DIR)
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as exc:
            messagebox.showinfo("角色目录", f"{path}\n\n{exc}", parent=self.win)

    def refresh(self) -> None:
        if not self.win or not self.win.winfo_exists():
            return
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._preview_refs.clear()

        packs = discover_characters()
        current_id = self.app.character.id
        self.status_var.set(f"已发现 {len(packs)} 个角色 · 当前：{self.app.character.name} ({current_id})")

        if not packs:
            ttk.Label(self.list_frame, text="未找到角色包，请运行 python -m utils.pack_generator").pack(pady=20)
            return

        for pack in packs:
            self._add_card(pack, is_current=(pack.id == current_id))

    def _add_card(self, pack: CharacterPack, is_current: bool) -> None:
        style_bg = "#E8F5E9" if is_current else "#F7F7F7"
        card = tk.Frame(self.list_frame, bg=style_bg, highlightbackground="#CCCCCC", highlightthickness=1)
        card.pack(fill="x", padx=4, pady=4)

        # 预览图：临时 loader
        preview_label = tk.Label(card, bg=style_bg)
        preview_label.pack(side="left", padx=8, pady=8)
        try:
            tmp_loader = AssetLoader(pack)
            photo = tmp_loader.get_preview_photo((56, 56))
            if photo:
                preview_label.configure(image=photo)
                preview_label.image = photo
                self._preview_refs.append(photo)
                self._preview_refs.append(tmp_loader)  # 保活缓存
        except Exception:
            preview_label.configure(text="?", width=6)

        info = tk.Frame(card, bg=style_bg)
        info.pack(side="left", fill="both", expand=True, pady=8)
        title = f"{pack.name}"
        if pack.name_en and pack.name_en != pack.name:
            title += f"  ({pack.name_en})"
        if is_current:
            title += "  ✓ 当前"
        tk.Label(info, text=title, bg=style_bg, font=("Microsoft YaHei UI", 11, "bold"), anchor="w").pack(fill="x")
        tk.Label(
            info,
            text=f"id: {pack.id}  ·  v{pack.version}  ·  {pack.author or 'unknown'}",
            bg=style_bg,
            fg="#666666",
            anchor="w",
        ).pack(fill="x")
        desc = pack.description or f"喜欢{pack.food.name} {pack.food.emoji}"
        tk.Label(info, text=desc, bg=style_bg, fg="#444444", anchor="w", wraplength=260, justify="left").pack(fill="x")

        missing = pack.missing_assets()
        if missing:
            tk.Label(
                info,
                text=f"缺少素材: {', '.join(missing[:4])}{'…' if len(missing) > 4 else ''}",
                bg=style_bg,
                fg="#C62828",
                anchor="w",
            ).pack(fill="x")

        btn_frame = tk.Frame(card, bg=style_bg)
        btn_frame.pack(side="right", padx=8)
        if is_current:
            tk.Label(btn_frame, text="使用中", bg=style_bg, fg="#2E7D32").pack()
        else:
            ttk.Button(
                btn_frame,
                text="使用",
                command=lambda p=pack: self._select(p),
            ).pack()

    def _select(self, pack: CharacterPack) -> None:
        try:
            self.app.switch_character(pack.id)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("切换失败", str(exc), parent=self.win)

    def close(self) -> None:
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None
        self._preview_refs.clear()
