# -*- mode: python ; coding: utf-8 -*-
# 可移植 spec：路径全部相对 SPECPATH（本文件所在 packaging/），禁止硬编码绝对路径。
# 用法（在项目根）:
#   pyinstaller --noconfirm --clean packaging/DesktopPet.spec
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
    icon=str(icon) if icon.is_file() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DesktopPet",
)
