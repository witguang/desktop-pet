"""
Cross-platform desktop pet packager.

Run from project root:
  python packaging/build_app.py
  or: 打包给朋友.bat / packaging/build_app.bat

使用 packaging/ 下可移植 .spec（相对 SPECPATH，无硬编码绝对路径）。
不把 PyInstaller 自动生成的带本机绝对路径的 .spec 写入 packaging/。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
ROOT = PKG_DIR.parent
SRC = ROOT / "src"

# 可移植 spec（相对项目根的路径字符串，传给 PyInstaller）
SPEC_MAIN = "packaging/DesktopPet.spec"
SPEC_SETUP = "packaging/DesktopPetSetup.spec"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=str(ROOT))


def _rel_to_root(path: Path) -> str:
    """命令行参数尽量用相对项目根的路径，避免写入绝对路径。"""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        # 不在项目树内时退回文件名（仅日志/极端情况）
        return path.name


def main() -> int:
    print(f"Python: {sys.executable}")
    print(f"Root:   {_rel_to_root(ROOT) or '.'}")
    print(f"Src:    {_rel_to_root(SRC)}")

    if not SRC.is_dir():
        print("ERROR: missing src/ directory:", _rel_to_root(SRC))
        return 1

    for rel in (SPEC_MAIN, SPEC_SETUP):
        if not (ROOT / rel).is_file():
            print("ERROR: missing portable spec:", rel)
            return 1

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Installing PyInstaller ...")
        run([sys.executable, "-m", "pip", "install", "-U", "pyinstaller"])

    # Clean previous build output at project root
    for name in ("build", "dist"):
        p = ROOT / name
        if p.exists():
            print(f"Removing {_rel_to_root(p)} ...")
            shutil.rmtree(p, ignore_errors=True)

    icon_path = _ensure_app_icon()

    # 用 portable .spec 构建；dist/work 相对路径；不生成/覆盖 packaging 下的 spec
    common = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        "dist",
        "--workpath",
        "build",
    ]

    run(common + [SPEC_MAIN])
    run(common + [SPEC_SETUP])

    main_dir = ROOT / "dist" / "DesktopPet"
    setup_dir = ROOT / "dist" / "DesktopPetSetup"
    setup_exe = setup_dir / "DesktopPetSetup.exe"
    if main_dir.exists() and setup_exe.exists():
        shutil.copy2(setup_exe, main_dir / "DesktopPetSetup.exe")
        print("Copied DesktopPetSetup.exe into dist/DesktopPet/")
        shutil.rmtree(setup_dir, ignore_errors=True)

    exe = main_dir / "DesktopPet.exe"
    if not exe.exists():
        print("ERROR: build finished but exe not found:", _rel_to_root(exe))
        return 1

    # 业务源码平铺到 exe 旁（热更新 / external_source 约定）
    _copy_sources_beside_exe(main_dir)

    if icon_path is not None and icon_path.is_file():
        shutil.copy2(icon_path, main_dir / "app.ico")

    zip_path = _make_friend_zip(main_dir)

    print("OK:", _rel_to_root(exe))
    setup = main_dir / "DesktopPetSetup.exe"
    if setup.exists():
        print("OK:", _rel_to_root(setup))
    if zip_path is not None:
        print("OK:", _rel_to_root(zip_path))
    print()
    print("=== 给朋友 ===")
    print("1) 把 zip 发过去，或上传到 GitHub Releases")
    print("2) 朋友解压后双击 DesktopPetSetup.exe（推荐）或 DesktopPet.exe")
    print("3) 无需安装 Python")
    print()
    print("Share folder:", _rel_to_root(main_dir))
    return 0


def _ensure_app_icon() -> Path | None:
    """从 Kiki preview/idle 生成 packaging/app.ico。"""
    out = PKG_DIR / "app.ico"
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
            print(f"Generated icon: packaging/{out.name}")
        return out
    except Exception as exc:
        print(f"WARN: could not build app.ico: {exc}")
        return out if out.is_file() else None


def _copy_sources_beside_exe(main_dir: Path) -> None:
    """
    把可热更新的业务树平铺到 exe 旁（不保留 src/ 前缀）。
    external_source 约定：exe 旁有 app.py / utils/ 等。
    """
    root_files = [
        "main.py",
        "install_app.py",
        "VERSION",
        "requirements.txt",
        "README.md",
        "给朋友看.md",
        ".gitignore",
    ]
    src_files = ["app.py", "config.py"]
    src_dirs = ["core", "data", "ui", "utils"]
    root_dirs = ["characters"]

    for name in root_files:
        src = ROOT / name
        if src.is_file():
            shutil.copy2(src, main_dir / name)

    for name in src_files:
        src = SRC / name
        if src.is_file():
            shutil.copy2(src, main_dir / name)

    for d in src_dirs:
        src = SRC / d
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

    for d in root_dirs:
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

    # packaging 工具可选拷贝，方便有源码的用户二次打包（仅 portable 文件）
    pack_dst = main_dir / "packaging"
    if pack_dst.exists():
        shutil.rmtree(pack_dst, ignore_errors=True)
    pack_dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "build_app.py",
        "build_app.bat",
        "DesktopPet.spec",
        "DesktopPetSetup.spec",
        "build_app.spec",
        "README.md",
    ):
        src = PKG_DIR / name
        if src.is_file():
            shutil.copy2(src, pack_dst / name)
    # 图标可选
    ico = PKG_DIR / "app.ico"
    if ico.is_file():
        shutil.copy2(ico, pack_dst / "app.ico")

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
    # make_archive 的 base_name 用相对路径，避免日志/中间结果带盘符依赖
    base_name = str(ROOT / "dist" / f"DesktopPet-v{version}")
    archive = shutil.make_archive(
        base_name,
        "zip",
        root_dir=str(main_dir.parent),
        base_dir=main_dir.name,
    )
    generated = Path(archive)
    if generated.resolve() != out.resolve():
        if out.exists():
            out.unlink()
        generated.replace(out)
    size_mb = out.stat().st_size // (1024 * 1024)
    print(f"Friend zip: {_rel_to_root(out)} ({size_mb} MB)")
    return out


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print("Build failed with code", exc.returncode)
        raise SystemExit(exc.returncode)
