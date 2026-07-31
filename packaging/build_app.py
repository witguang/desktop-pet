"""
打包桌宠：只产出一个 DesktopPet.exe（onefile）。

Run from project root:
  python packaging/build_app.py
  or: 打包给朋友.bat

朋友拿到的就是这一个 exe：
  - 首次运行会弹出设置向导（安装位置 / 备忘录 / 快捷方式 / 打开桌宠）
  - 窗口左上角图标为 app.ico（Kiki），不是 Python 羽毛
  - 安装目录也只保留 DesktopPet.exe（+ 运行后的 data_store）
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
ROOT = PKG_DIR.parent
SRC = ROOT / "src"

SPEC_MAIN = "packaging/DesktopPet.spec"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=str(ROOT))


def _rel_to_root(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def main() -> int:
    print(f"Python: {sys.executable}")
    print(f"Root:   {_rel_to_root(ROOT) or '.'}")

    if not SRC.is_dir():
        print("ERROR: missing src/")
        return 1
    if not (ROOT / SPEC_MAIN).is_file():
        print("ERROR: missing", SPEC_MAIN)
        return 1

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Installing PyInstaller ...")
        run([sys.executable, "-m", "pip", "install", "-U", "pyinstaller"])

    for name in ("build", "dist"):
        p = ROOT / name
        if p.exists():
            print(f"Removing {_rel_to_root(p)} ...")
            shutil.rmtree(p, ignore_errors=True)

    icon_path = _ensure_app_icon()
    if icon_path is None or not icon_path.is_file():
        print("ERROR: packaging/app.ico missing")
        return 1
    print(f"Icon: packaging/app.ico ({icon_path.stat().st_size} bytes) → embed + window title")

    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            "dist",
            "--workpath",
            "build",
            SPEC_MAIN,
        ]
    )

    main_exe = ROOT / "dist" / "DesktopPet.exe"
    if not main_exe.is_file():
        print("ERROR: DesktopPet.exe not found")
        return 1

    # 只打包这一个 exe（不要 Setup / 说明 / ico 散文件）
    version = _read_version()
    zip_path = ROOT / "dist" / f"DesktopPet-v{version}-windows.zip"
    if zip_path.exists():
        zip_path.unlink()

    import zipfile

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(main_exe, arcname="DesktopPet.exe")

    size_mb = max(1, zip_path.stat().st_size // (1024 * 1024))
    print("OK:", _rel_to_root(main_exe), f"({main_exe.stat().st_size // (1024 * 1024)} MB)")
    print("OK:", _rel_to_root(zip_path), f"({size_mb} MB)  ← 里面只有 DesktopPet.exe")
    print()
    print("=== 给朋友 ===")
    print("请发 zip（浏览器不易拦截）：", _rel_to_root(zip_path))
    print("勿让朋友从网页直接下裸 .exe（会提示「通常不会下载」）")
    print("解压后双击 DesktopPet.exe → 首次设置 → 完成")
    print("安装目录只有 DesktopPet.exe（运行后才有 data_store）")
    print("GitHub Release 建议只上传 zip：")
    print(f"  gh release create v{version} dist/DesktopPet-v{version}-windows.zip")
    return 0


def _ensure_app_icon() -> Path | None:
    out = PKG_DIR / "app.ico"
    sources = [
        ROOT / "characters" / "kiki" / "assets" / "preview.png",
        ROOT / "characters" / "kiki" / "assets" / "idle.png",
    ]
    src = next((p for p in sources if p.is_file()), None)
    if src is None:
        return out if out.is_file() else None
    try:
        need = (not out.is_file()) or (out.stat().st_mtime < src.stat().st_mtime)
        if need:
            from PIL import Image

            img = Image.open(src).convert("RGBA")
            w, h = img.size
            side = min(w, h)
            img = img.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
            sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            out.parent.mkdir(parents=True, exist_ok=True)
            img.save(out, format="ICO", sizes=sizes)
            print("Generated packaging/app.ico")
        return out
    except Exception as exc:
        print(f"WARN: app.ico: {exc}")
        return out if out.is_file() else None


def _read_version() -> str:
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print("Build failed with code", exc.returncode)
        raise SystemExit(exc.returncode)
