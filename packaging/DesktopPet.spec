# -*- mode: python ; coding: utf-8 -*-
# 可移植 spec：SPECPATH = packaging/，项目根为上一级
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

pkg = Path(SPECPATH)
root = pkg.parent
src = root / "src"

datas = [
    (str(root / "characters"), "characters"),
    (str(root / "VERSION"), "."),
]
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
    [],
    exclude_binaries=True,
    name="DesktopPet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DesktopPet",
)
