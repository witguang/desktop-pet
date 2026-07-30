"""Desktop Pet 统一视觉主题。

集中管理配色、字体、间距与常用控件样式，确保所有面板风格一致。
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

# 防止 PhotoImage 被 GC 后窗口图标变回默认羽毛
_ICON_PHOTO_REFS: list[tk.PhotoImage] = []
_ICON_PATH_CACHE: Path | None | bool = False  # False=未解析


class Colors:
    """统一配色方案（柔和、低饱和、适合长时间陪伴）。"""

    # 主色与强调
    PRIMARY = "#5C6BC0"          # 靛蓝主色
    PRIMARY_DARK = "#3949AB"     # 深靛蓝（悬停/按下）
    ACCENT = "#FF8A65"           # 暖珊瑚 accent
    SUCCESS = "#66BB6A"          # 成功绿
    WARNING = "#FFB74D"          # 警告橙
    DANGER = "#EF5350"           # 危险红

    # 背景
    BG_WINDOW = "#F7F9FC"        # 窗口背景
    BG_CARD = "#FFFFFF"          # 卡片背景
    BG_INPUT = "#FFFEF7"         # 输入区背景
    BG_HOVER = "#E8EAF6"         # 悬停背景

    # 文字
    TEXT_MAIN = "#2D3748"        # 主文字
    TEXT_SECONDARY = "#718096"   # 次要文字
    TEXT_MUTED = "#A0AEC0"       # 更淡的文字
    TEXT_ON_PRIMARY = "#FFFFFF"  # 主色上的文字

    # 边框与分隔
    BORDER = "#E2E8F0"           # 边框
    BORDER_LIGHT = "#EDF2F7"     # 浅边框/分隔线
    SHADOW = "#CBD5E0"           # 阴影色（模拟）


class Fonts:
    """统一字体族。"""

    FAMILY = "Microsoft YaHei UI"
    FAMILY_MONO = "Consolas"

    @classmethod
    def title(cls, size: int = 14, bold: bool = True) -> tuple[str, int, str]:
        weight = "bold" if bold else "normal"
        return (cls.FAMILY, size, weight)

    @classmethod
    def heading(cls, size: int = 12, bold: bool = True) -> tuple[str, int, str]:
        weight = "bold" if bold else "normal"
        return (cls.FAMILY, size, weight)

    @classmethod
    def body(cls, size: int = 10, bold: bool = False) -> tuple[str, int, str]:
        weight = "bold" if bold else "normal"
        return (cls.FAMILY, size, weight)

    @classmethod
    def small(cls, size: int = 8, bold: bool = False) -> tuple[str, int, str]:
        weight = "bold" if bold else "normal"
        return (cls.FAMILY, size, weight)

    @classmethod
    def mono(cls, size: int = 9) -> tuple[str, int, str]:
        return (cls.FAMILY_MONO, size, "normal")


class Spacing:
    """统一间距。"""

    PAD_XS = 2
    PAD_SM = 4
    PAD_MD = 8
    PAD_LG = 12
    PAD_XL = 16


def entry_kwargs(**overrides) -> dict:
    """
    经典 tk.Entry 的可读配色（Windows 深色模式下也保持深字浅底）。
    未设 insertbackground / selectforeground 时，选目录后常出现白字看不见。
    """
    cfg = {
        "bg": Colors.BG_INPUT,
        "fg": Colors.TEXT_MAIN,
        "insertbackground": Colors.TEXT_MAIN,
        "selectbackground": Colors.PRIMARY,
        "selectforeground": Colors.TEXT_ON_PRIMARY,
        "disabledbackground": Colors.BG_INPUT,
        "disabledforeground": Colors.TEXT_SECONDARY,
        "relief": "solid",
        "bd": 1,
        "font": Fonts.body(),
        "highlightthickness": 1,
        "highlightbackground": Colors.BORDER,
        "highlightcolor": Colors.PRIMARY,
    }
    cfg.update(overrides)
    return cfg


# ttk 样式统一入口
def configure_ttk_styles(master: tk.Misc | None = None) -> None:
    """配置全局 ttk 样式，使按钮、输入框、标签框架风格一致。

    务必在已有 Tk/Toplevel 之后调用（或传入 master）。
    若在没有任何根窗口时调用 ttk.Style()，会偷偷创建一个空白幽灵窗口。
    """
    style = ttk.Style(master) if master is not None else ttk.Style()

    # 通用 TFrame 背景
    style.configure("TFrame", background=Colors.BG_WINDOW)
    style.configure("TLabel", background=Colors.BG_WINDOW, foreground=Colors.TEXT_MAIN)
    style.configure(
        "TButton",
        font=Fonts.body(),
        foreground=Colors.TEXT_ON_PRIMARY,
        background=Colors.PRIMARY,
    )
    style.map(
        "TButton",
        background=[("active", Colors.PRIMARY_DARK), ("pressed", Colors.PRIMARY_DARK)],
        foreground=[("active", Colors.TEXT_ON_PRIMARY), ("pressed", Colors.TEXT_ON_PRIMARY)],
    )
    style.configure(
        "TEntry",
        font=Fonts.body(),
        fieldbackground=Colors.BG_INPUT,
        foreground=Colors.TEXT_MAIN,
    )
    style.configure(
        "TCombobox",
        font=Fonts.body(),
        fieldbackground=Colors.BG_INPUT,
        foreground=Colors.TEXT_MAIN,
    )
    style.configure(
        "TCheckbutton",
        font=Fonts.body(),
        background=Colors.BG_WINDOW,
        foreground=Colors.TEXT_MAIN,
    )
    style.configure(
        "TLabelframe",
        background=Colors.BG_CARD,
        foreground=Colors.TEXT_SECONDARY,
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "TLabelframe.Label",
        background=Colors.BG_CARD,
        foreground=Colors.PRIMARY,
        font=Fonts.body(bold=True),
    )
    style.configure(
        "Title.TLabel",
        font=Fonts.title(),
        foreground=Colors.TEXT_MAIN,
        background=Colors.BG_WINDOW,
    )
    style.configure(
        "Subtitle.TLabel",
        font=Fonts.heading(),
        foreground=Colors.TEXT_SECONDARY,
        background=Colors.BG_WINDOW,
    )
    style.configure(
        "Hint.TLabel",
        font=Fonts.small(),
        foreground=Colors.TEXT_MUTED,
        background=Colors.BG_WINDOW,
    )


def resolve_app_icon_path() -> Path | None:
    """定位 app.ico：打包 onefile 在 _MEIPASS；开发在 packaging/。"""
    global _ICON_PATH_CACHE
    if _ICON_PATH_CACHE is not False:
        return _ICON_PATH_CACHE if isinstance(_ICON_PATH_CACHE, Path) else None

    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "app.ico")
        candidates.append(Path(sys.executable).resolve().parent / "app.ico")
    # 开发：src/ui/theme.py → 项目根/packaging/app.ico
    here = Path(__file__).resolve()
    if here.parent.name == "ui":
        root = here.parent.parent.parent  # src/ui → 项目根
        candidates.append(root / "packaging" / "app.ico")
        candidates.append(root / "app.ico")
    # 平铺布局
    candidates.append(here.parent.parent / "packaging" / "app.ico")
    candidates.append(here.parent.parent / "app.ico")

    for p in candidates:
        try:
            if p.is_file():
                _ICON_PATH_CACHE = p
                return p
        except OSError:
            continue
    _ICON_PATH_CACHE = None
    return None


def apply_app_icon(window: tk.Misc) -> None:
    """
    把窗口左上角 / 任务栏图标从 Python 羽毛换成 app.ico（Kiki）。

    iconphoto(True, …) 会作为后续 Toplevel 的默认图标。
    """
    path = resolve_app_icon_path()
    if path is None:
        return

    # Windows：.ico 用 iconbitmap 最稳
    try:
        window.iconbitmap(default=str(path))
    except tk.TclError:
        try:
            window.iconbitmap(str(path))
        except tk.TclError:
            pass

    # 再设 iconphoto，覆盖部分环境下的羽毛默认图
    try:
        from PIL import Image, ImageTk

        img = Image.open(path).convert("RGBA")
        # 标题栏常用 16/32
        photo = ImageTk.PhotoImage(img.resize((32, 32), Image.Resampling.LANCZOS))
        window.iconphoto(True, photo)
        _ICON_PHOTO_REFS.append(photo)
        # 挂到窗口上防止被回收
        setattr(window, "_desktop_pet_icon", photo)
    except Exception:
        pass


def apply_window_bg(window: tk.Tk | tk.Toplevel) -> None:
    """给窗口设置统一背景色，并应用 app.ico（去掉羽毛 logo）。"""
    try:
        window.configure(bg=Colors.BG_WINDOW)
    except tk.TclError:
        pass
    apply_app_icon(window)


def styled_label(
    parent: tk.Widget,
    text: str = "",
    *,
    style: str = "body",
    **kwargs,
) -> tk.Label:
    """创建统一风格的 tk.Label。"""
    presets = {
        "title": {"font": Fonts.title(), "fg": Colors.TEXT_MAIN, "bg": Colors.BG_WINDOW},
        "heading": {"font": Fonts.heading(), "fg": Colors.TEXT_MAIN, "bg": Colors.BG_WINDOW},
        "body": {"font": Fonts.body(), "fg": Colors.TEXT_MAIN, "bg": Colors.BG_WINDOW},
        "secondary": {"font": Fonts.body(), "fg": Colors.TEXT_SECONDARY, "bg": Colors.BG_WINDOW},
        "hint": {"font": Fonts.small(), "fg": Colors.TEXT_MUTED, "bg": Colors.BG_WINDOW},
        "accent": {"font": Fonts.body(bold=True), "fg": Colors.PRIMARY, "bg": Colors.BG_WINDOW},
    }
    cfg = dict(presets.get(style, presets["body"]))
    cfg.update(kwargs)
    return tk.Label(parent, text=text, **cfg)


def styled_button(
    parent: tk.Widget,
    text: str,
    *,
    kind: str = "primary",
    command=None,
    **kwargs,
) -> tk.Button:
    """创建统一风格的 tk.Button。"""
    palettes = {
        "primary": {"bg": Colors.PRIMARY, "fg": Colors.TEXT_ON_PRIMARY, "activebackground": Colors.PRIMARY_DARK, "activeforeground": Colors.TEXT_ON_PRIMARY},
        "success": {"bg": Colors.SUCCESS, "fg": Colors.TEXT_ON_PRIMARY, "activebackground": "#43A047", "activeforeground": Colors.TEXT_ON_PRIMARY},
        "danger": {"bg": Colors.DANGER, "fg": Colors.TEXT_ON_PRIMARY, "activebackground": "#D32F2F", "activeforeground": Colors.TEXT_ON_PRIMARY},
        "secondary": {"bg": Colors.BG_CARD, "fg": Colors.TEXT_MAIN, "activebackground": Colors.BG_HOVER, "activeforeground": Colors.TEXT_MAIN},
    }
    cfg = {
        "font": Fonts.body(),
        "relief": "flat",
        "padx": 14,
        "pady": 5,
        "cursor": "hand2",
    }
    cfg.update(palettes.get(kind, palettes["primary"]))
    if command is not None:
        cfg["command"] = command
    cfg.update(kwargs)
    return tk.Button(parent, text=text, **cfg)


def card_frame(parent: tk.Widget, **kwargs) -> tk.Frame:
    """创建卡片式容器：白底、细边框、轻微内边距。"""
    defaults = {
        "bg": Colors.BG_CARD,
        "highlightbackground": Colors.BORDER,
        "highlightthickness": 1,
        "bd": 0,
    }
    defaults.update(kwargs)
    return tk.Frame(parent, **defaults)
