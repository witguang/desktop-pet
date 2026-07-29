"""
Cross-platform desktop pet packager.
Run:  python build_app.py
  or: build_app.bat
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=str(ROOT))


def main() -> int:
    print(f"Python: {sys.executable}")
    print(f"Root:   {ROOT}")

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Installing PyInstaller ...")
        run([sys.executable, "-m", "pip", "install", "-U", "pyinstaller"])

    # Clean previous build output (keep script simple)
    for name in ("build", "dist"):
        p = ROOT / name
        if p.exists():
            print(f"Removing {p} ...")
            shutil.rmtree(p, ignore_errors=True)

    # Windows uses ";" in --add-data; other OS use ":"
    sep = ";" if sys.platform.startswith("win") else ":"
    add_data = [
        f"characters{sep}characters",
        f"assets{sep}assets",
        f"VERSION{sep}.",
    ]

    common = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--paths",
        str(ROOT),
        "--hidden-import",
        "PIL._tkinter_finder",
        "--collect-all",
        "PIL",
    ]
    for item in add_data:
        common.extend(["--add-data", item])

    # Main app
    run(common + ["--name", "DesktopPet", str(ROOT / "main.py")])

    # Installer (separate small entry — shares same datas)
    run(
        common
        + [
            "--name",
            "DesktopPetSetup",
            str(ROOT / "install_app.py"),
        ]
    )

    # Merge installer exe into main dist folder for one-folder distribution
    main_dir = ROOT / "dist" / "DesktopPet"
    setup_dir = ROOT / "dist" / "DesktopPetSetup"
    setup_exe = setup_dir / "DesktopPetSetup.exe"
    if main_dir.exists() and setup_exe.exists():
        shutil.copy2(setup_exe, main_dir / "DesktopPetSetup.exe")
        print("Copied DesktopPetSetup.exe into dist/DesktopPet/")
        # optional: remove separate setup dist to avoid confusion
        shutil.rmtree(setup_dir, ignore_errors=True)

    exe = main_dir / "DesktopPet.exe"
    if not exe.exists():
        print("ERROR: build finished but exe not found:", exe)
        return 1

    # 把业务源码拷到 exe 旁，供 GitHub 源码更新 + external_source 热加载
    _copy_sources_beside_exe(main_dir)

    print("OK:", exe)
    setup = main_dir / "DesktopPetSetup.exe"
    if setup.exists():
        print("OK:", setup)
    print("Share the whole folder: dist/DesktopPet/")
    print("Friends can run DesktopPetSetup.exe to pick install + memo folders.")
    return 0


def _copy_sources_beside_exe(main_dir: Path) -> None:
    """Copy pure-Python app tree next to DesktopPet.exe for in-place updates."""
    patterns = [
        "main.py",
        "app.py",
        "config.py",
        "VERSION",
        "requirements.txt",
        "README.md",
        ".gitignore",
        "DesktopPet.spec",
        "build_app.py",
        "build_app.bat",
        "install_app.py",
    ]
    dirs = ["core", "data", "ui", "utils", "characters", "assets"]
    for name in patterns:
        src = ROOT / name
        if src.is_file():
            shutil.copy2(src, main_dir / name)
    for d in dirs:
        src = ROOT / d
        dst = main_dir / d
        if not src.is_dir():
            continue
        if dst.exists():
            shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(
            src,
            dst,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".memo_history"),
        )
    print("Copied source tree beside exe for hot update.")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print("Build failed with code", exc.returncode)
        raise SystemExit(exc.returncode)
