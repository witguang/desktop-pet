# -*- mode: python ; coding: utf-8 -*-
# 兼容入口：与 DesktopPet.spec 相同（onefile，可移植）
# 推荐: python packaging/build_app.py
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

pkg = Path(SPECPATH)
root = pkg.parent
src = root / "src"
icon = pkg / "app.ico"

datas = [
    (str(root / "characters"), "characters"),
    (str(root / "VERSION"), "."),
]
if icon.is_file():
    datas.append((str(icon), "."))

binaries = []
hiddenimports = ["PIL._tkinter_finder"]
tmp_ret = collect_all("PIL")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    [str(root / "main.py")],
    pathex=[str(src), str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DesktopPet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon) if icon.is_file() else "NONE",
)
