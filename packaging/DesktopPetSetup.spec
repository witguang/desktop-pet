# -*- mode: python ; coding: utf-8 -*-
# 可移植 onefile：安装向导 DesktopPetSetup.exe
# 用法（项目根）:
#   pyinstaller --noconfirm --clean packaging/DesktopPetSetup.spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

pkg = Path(SPECPATH)
root = pkg.parent
src = root / "src"
icon = pkg / "app.ico"

datas = [
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
    [str(root / "install_app.py")],
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
    name="DesktopPetSetup",
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
