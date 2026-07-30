# -*- mode: python ; coding: utf-8 -*-
# 用法: pyinstaller --noconfirm packaging/build_app.spec
# SPECPATH = packaging/

from pathlib import Path

block_cipher = None
pkg = Path(SPECPATH)
root = pkg.parent
src = root / "src"

a = Analysis(
    [str(root / "main.py")],
    pathex=[str(src), str(root)],
    binaries=[],
    datas=[
        (str(root / "characters"), "characters"),
        (str(root / "VERSION"), "."),
    ],
    hiddenimports=["PIL._tkinter_finder"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    cipher=block_cipher,
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
