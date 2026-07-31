"""开机自启：Windows 启动文件夹快捷方式。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from utils.install_util import create_windows_shortcut

# 启动项快捷方式名称（固定，便于增删）
SHORTCUT_NAME = "DesktopPet.lnk"


def startup_dir() -> Path | None:
    """当前用户 Startup 目录。"""
    if not sys.platform.startswith("win"):
        return None
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def shortcut_path() -> Path | None:
    d = startup_dir()
    if d is None:
        return None
    return d / SHORTCUT_NAME


def is_enabled() -> bool:
    p = shortcut_path()
    return bool(p and p.is_file())


def resolve_launch_target() -> tuple[Path, Path, list[str]]:
    """
    返回 (target, workdir, extra_args)。
    frozen: DesktopPet.exe；开发: python.exe + packaging/entry_main.py
    """
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        return exe, exe.parent, []

    # 开发模式：用当前解释器启动 packaging/entry_main.py
    here = Path(__file__).resolve()
    if here.parent.name == "utils" and here.parent.parent.name == "src":
        root = here.parent.parent.parent
    else:
        root = here.parent.parent
    entry = root / "packaging" / "entry_main.py"
    if not entry.is_file():
        entry = root / "main.py"  # 旧布局兼容
    python = Path(sys.executable).resolve()
    return python, root, [str(entry)]


def enable() -> tuple[bool, str]:
    """启用开机自启。返回 (成功, 说明)。"""
    if not sys.platform.startswith("win"):
        return False, "当前仅支持 Windows 开机自启。"
    sc = shortcut_path()
    if sc is None:
        return False, "无法定位 Startup 目录。"
    target, workdir, args = resolve_launch_target()
    if not target.exists():
        return False, f"启动目标不存在：{target}"

    # create_windows_shortcut 不支持参数；开发模式用包装 .vbs 或带参数的快捷方式
    if args:
        ok = _create_shortcut_with_args(sc, target, workdir, args)
    else:
        ok = create_windows_shortcut(target, sc, workdir=workdir)
    if ok:
        return True, f"已写入启动项：\n{sc}"
    return False, "创建启动快捷方式失败。"


def disable() -> tuple[bool, str]:
    """关闭开机自启。"""
    sc = shortcut_path()
    if sc is None:
        return True, "非 Windows，无需处理。"
    if not sc.exists():
        return True, "启动项本就不存在。"
    try:
        sc.unlink()
        return True, "已移除开机自启。"
    except OSError as exc:
        return False, f"删除启动项失败：{exc}"


def set_enabled(want: bool) -> tuple[bool, str]:
    if want:
        return enable()
    return disable()


def _create_shortcut_with_args(
    shortcut_path: Path,
    target: Path,
    workdir: Path,
    args: list[str],
    *,
    icon_path: Path | None = None,
    description: str = "Desktop Pet — Kiki",
) -> bool:
    """创建带命令行参数的 .lnk（PowerShell）。"""
    from utils.install_util import find_app_icon

    shortcut_path = shortcut_path.resolve()
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    arg_str = " ".join(f'"{a}"' if " " in a else a for a in args)
    icon = icon_path or find_app_icon(workdir) or find_app_icon(target.parent)
    icon_loc = f"{icon},0" if icon and icon.is_file() else f"{target},0"

    # 转义给 PowerShell 单引号字符串
    def _ps(s: str) -> str:
        return s.replace("'", "''")

    ps = (
        f"$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{_ps(str(shortcut_path))}'); "
        f"$s.TargetPath = '{_ps(str(target))}'; "
        f"$s.Arguments = '{_ps(arg_str)}'; "
        f"$s.WorkingDirectory = '{_ps(str(workdir))}'; "
        f"$s.IconLocation = '{_ps(icon_loc)}'; "
        f"$s.Description = '{_ps(description)}'; "
        f"$s.Save()"
    )
    try:
        import subprocess

        subprocess.check_call(
            ["powershell", "-NoProfile", "-Command", ps],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return shortcut_path.exists()
    except Exception:
        return False
