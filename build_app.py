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

    # 确保 Kiki 应用图标存在（快捷方式 + exe 图标）
    icon_path = _ensure_app_icon()

    # Windows uses ";" in --add-data; other OS use ":"
    sep = ";" if sys.platform.startswith("win") else ":"
    add_data = [
        f"characters{sep}characters",
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
    if icon_path is not None:
        common.extend(["--icon", str(icon_path)])

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

    # 根目录再放一份 app.ico，便于快捷方式 IconLocation
    if icon_path is not None and icon_path.is_file():
        shutil.copy2(icon_path, main_dir / "app.ico")

    # 给朋友一键分发的 zip（整包，解压即用）
    zip_path = _make_friend_zip(main_dir)

    print("OK:", exe)
    setup = main_dir / "DesktopPetSetup.exe"
    if setup.exists():
        print("OK:", setup)
    if zip_path is not None:
        print("OK:", zip_path)
    print()
    print("=== 给朋友 ===")
    print("1) 把 zip 发过去，或上传到 GitHub Releases")
    print("2) 朋友解压后双击 DesktopPetSetup.exe（推荐）或 DesktopPet.exe")
    print("3) 无需安装 Python")
    print()
    print("Share folder:", main_dir)
    return 0


def _ensure_app_icon() -> Path | None:
    """从 Kiki preview/idle 生成 app.ico（若不存在或过旧则重建）。"""
    out = ROOT / "app.ico"
    sources = [
        ROOT / "characters" / "kiki" / "assets" / "preview.png",
        ROOT / "characters" / "kiki" / "assets" / "idle.png",
    ]
    src = next((p for p in sources if p.is_file()), None)
    if src is None:
        print("WARN: no kiki image for app.ico")
        return out if out.is_file() else None

    try:
        need = True
        if out.is_file():
            need = out.stat().st_mtime < src.stat().st_mtime
        if need:
            from PIL import Image

            img = Image.open(src).convert("RGBA")
            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))
            sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            out.parent.mkdir(parents=True, exist_ok=True)
            img.save(out, format="ICO", sizes=sizes)
            print(f"Generated icon: {out}")
        return out
    except Exception as exc:
        print(f"WARN: could not build app.ico: {exc}")
        return out if out.is_file() else None


def _copy_sources_beside_exe(main_dir: Path) -> None:
    """Copy pure-Python app tree next to DesktopPet.exe for in-place updates."""
    patterns = [
        "main.py",
        "app.py",
        "config.py",
        "VERSION",
        "requirements.txt",
        "README.md",
        "给朋友看.md",
        ".gitignore",
        "DesktopPet.spec",
        "build_app.py",
        "build_app.bat",
        "install_app.py",
        "app.ico",
    ]
    dirs = ["core", "data", "ui", "utils", "characters"]
    for name in patterns:
        src = ROOT / name
        if src.is_file():
            dest = main_dir / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
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
    # 分发包内放一份极简说明，避免朋友打开一堆源码发懵
    readme_friend = main_dir / "【先读我】安装说明.txt"
    readme_friend.write_text(
        "\n".join(
            [
                "Desktop Pet 桌面宠物 — 安装说明",
                "================================",
                "",
                "【推荐】双击 DesktopPetSetup.exe",
                "  → 选择安装位置、备忘录目录",
                "  → 可选创建桌面快捷方式",
                "",
                "【也可以】直接双击 DesktopPet.exe 运行（便携模式）",
                "",
                "不需要安装 Python。",
                "Windows 若提示「未知发布者」，点「更多信息」→「仍要运行」。",
                "",
                "日常使用：右键桌宠打开控制面板；Ctrl+Shift+P 也可。",
                "退出：控制面板 / 主设置 → 退出桌宠。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print("Copied source tree beside exe for hot update.")


def _read_version() -> str:
    path = ROOT / "VERSION"
    try:
        return path.read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def _make_friend_zip(main_dir: Path) -> Path | None:
    """打包 dist/DesktopPet 为可直接发给朋友的 zip。"""
    if not main_dir.is_dir():
        return None
    version = _read_version()
    out = ROOT / "dist" / f"DesktopPet-v{version}-windows.zip"
    if out.exists():
        out.unlink()
    # zip 内顶层目录名固定，方便解压后找到
    base_name = str(ROOT / "dist" / f"DesktopPet-v{version}")
    archive = shutil.make_archive(base_name, "zip", root_dir=main_dir.parent, base_dir=main_dir.name)
    # make_archive 生成 DesktopPet-vX.zip，与目标名对齐
    generated = Path(archive)
    if generated.resolve() != out.resolve():
        if out.exists():
            out.unlink()
        generated.replace(out)
    print(f"Friend zip: {out} ({out.stat().st_size // (1024 * 1024)} MB)")
    return out


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print("Build failed with code", exc.returncode)
        raise SystemExit(exc.returncode)
