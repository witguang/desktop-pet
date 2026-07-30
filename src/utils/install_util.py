"""安装工具：复制程序目录、写设置、创建桌面快捷方式。"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Iterable

# 不复制的目录/文件
_SKIP_NAMES = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "build",
    "dist",
    "*.pyc",
}


def default_install_dir() -> Path:
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "DesktopPet"
    return Path.home() / "DesktopPet"


def default_memo_suggestion() -> Path:
    docs = Path.home() / "Documents" / "DesktopPetMemos"
    return docs


def should_skip(name: str) -> bool:
    if name in _SKIP_NAMES:
        return True
    if name.endswith(".pyc"):
        return True
    if name.startswith("."):
        # keep .gitignore? skip hidden
        return name not in (".gitkeep",)
    return False


def copy_app_tree(src: Path, dst: Path, progress=None) -> int:
    """
    复制应用目录到安装位置。
    保留目标已有 data_store（若存在），避免覆盖用户数据。
    返回复制的文件数。
    """
    src = src.resolve()
    dst = dst.resolve()
    if src == dst:
        return 0

    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for root, dirs, files in os.walk(src):
        rel_root = Path(root).relative_to(src)
        # filter dirs in-place
        dirs[:] = [d for d in dirs if not should_skip(d)]
        # skip overwriting existing data_store contents partially — skip walking into src data_store if dst has one
        if rel_root.parts[:1] == ("data_store",) and (dst / "data_store").exists():
            # still allow merging new empty structure? skip entire data_store from src
            dirs[:] = []
            continue

        target_dir = dst / rel_root
        target_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            if should_skip(f):
                continue
            # don't overwrite settings in data_store if we skipped walk — already skipped
            sfile = Path(root) / f
            dfile = target_dir / f
            if dfile.exists() and rel_root.parts[:1] == ("data_store",):
                continue
            shutil.copy2(sfile, dfile)
            count += 1
            if progress and count % 50 == 0:
                progress(f"已复制 {count} 个文件…")
    return count


def write_initial_settings(
    install_dir: Path,
    *,
    memo_dir: Path,
    character_id: str = "kiki",
) -> Path:
    data_dir = install_dir / "data_store"
    data_dir.mkdir(parents=True, exist_ok=True)
    settings_path = data_dir / "settings.json"
    data: dict = {}
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except (json.JSONDecodeError, OSError):
            data = {}
    data["character_id"] = data.get("character_id") or character_id
    # 路径尽量可移植：主目录下写成 ~/...，默认 memos 写成相对名
    try:
        from data.settings import portable_path_str

        data["memo_dir"] = portable_path_str(Path(memo_dir))
    except Exception:
        # 开发/安装早期：尽量用 ~/ 相对用户主目录
        memo = Path(memo_dir).expanduser()
        try:
            rel = memo.resolve().relative_to(Path.home().resolve())
            data["memo_dir"] = str(Path("~") / rel).replace("\\", "/")
        except (ValueError, OSError):
            data["memo_dir"] = str(memo)
    data["setup_completed"] = True
    # install_dir 仅本机记录，不进 Git；用绝对路径便于快捷方式
    data["install_dir"] = str(Path(install_dir).expanduser().resolve())
    settings_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    memo_dir.mkdir(parents=True, exist_ok=True)
    return settings_path


def find_app_icon(base: Path | None = None) -> Path | None:
    """查找 Kiki / 应用图标（优先 .ico）。"""
    roots: list[Path] = []
    if base is not None:
        roots.append(Path(base))
    try:
        roots.append(find_app_source())
    except Exception:
        pass
    # 去重并保持顺序
    seen: set[str] = set()
    candidates: list[Path] = []
    for root in roots:
        root = root.resolve()
        key = str(root).lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.extend(
            [
                root / "app.ico",
                root / "characters" / "kiki" / "assets" / "preview.png",
                root / "characters" / "kiki" / "assets" / "idle.png",
                root / "_internal" / "app.ico",
                root / "_internal" / "characters" / "kiki" / "assets" / "preview.png",
            ]
        )
    for c in candidates:
        if c.is_file():
            return c
    return None


def create_windows_shortcut(
    target_exe: Path,
    shortcut_path: Path,
    workdir: Path | None = None,
    *,
    icon_path: Path | None = None,
    description: str = "Desktop Pet — Kiki",
) -> bool:
    """创建 .lnk 快捷方式（Windows）。失败返回 False。"""
    if not sys.platform.startswith("win"):
        return False
    target_exe = target_exe.resolve()
    workdir = (workdir or target_exe.parent).resolve()
    shortcut_path = shortcut_path.resolve()
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    icon = icon_path or find_app_icon(workdir) or find_app_icon(target_exe.parent)
    icon_loc = f"{icon},0" if icon and icon.is_file() else f"{target_exe},0"
    try:
        # Prefer win32com if available
        try:
            import win32com.client  # type: ignore

            shell = win32com.client.Dispatch("WScript.Shell")
            sc = shell.CreateShortCut(str(shortcut_path))
            sc.Targetpath = str(target_exe)
            sc.WorkingDirectory = str(workdir)
            sc.IconLocation = icon_loc
            sc.Description = description
            sc.save()
            return True
        except Exception:
            pass
        # Fallback: PowerShell
        def _ps(s: str) -> str:
            return s.replace("'", "''")

        ps = (
            f"$ws = New-Object -ComObject WScript.Shell; "
            f"$s = $ws.CreateShortcut('{_ps(str(shortcut_path))}'); "
            f"$s.TargetPath = '{_ps(str(target_exe))}'; "
            f"$s.WorkingDirectory = '{_ps(str(workdir))}'; "
            f"$s.IconLocation = '{_ps(icon_loc)}'; "
            f"$s.Description = '{_ps(description)}'; "
            f"$s.Save()"
        )
        import subprocess

        subprocess.check_call(
            ["powershell", "-NoProfile", "-Command", ps],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return shortcut_path.exists()
    except Exception:
        return False


def desktop_dir() -> Path:
    """用户桌面目录（优先 shell 真实桌面，兼容 OneDrive）。"""
    if sys.platform.startswith("win"):
        # 1) PowerShell 用户桌面（含 OneDrive 重定向）
        try:
            import subprocess

            out = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "[Environment]::GetFolderPath('Desktop')",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=8,
            ).strip()
            if out:
                p = Path(out)
                if p.is_dir():
                    return p
        except Exception:
            pass
        # 2) 常见路径
        home = Path(os.environ.get("USERPROFILE", str(Path.home())))
        for candidate in (
            home / "Desktop",
            home / "OneDrive" / "Desktop",
            home / "OneDrive" / "桌面",
        ):
            if candidate.is_dir():
                return candidate
        return home / "Desktop"
    return Path.home() / "Desktop"


def find_app_source() -> Path:
    """当前程序所在目录（打包后 = exe 旁；开发 = 项目根）。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    here = Path(__file__).resolve()
    # src/utils/xxx.py → 项目根
    if here.parent.name == "utils" and here.parent.parent.name == "src":
        return here.parent.parent.parent
    # 兼容：exe 旁平铺的 utils/
    return here.parent.parent


def find_main_exe(install_dir: Path) -> Path | None:
    candidates = [
        install_dir / "DesktopPet.exe",
        install_dir / "DesktopPet" / "DesktopPet.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    # python 开发模式
    main_py = install_dir / "main.py"
    if main_py.exists():
        return main_py
    return None
