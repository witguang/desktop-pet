# -*- mode: python ; coding: utf-8 -*-
# 可移植 onefile spec：安装目录 ideally 只有 DesktopPet.exe
# 路径相对 SPECPATH（packaging/），禁止硬编码绝对路径。
# 用法（项目根）:
#   pyinstaller --noconfirm --clean packaging/DesktopPet.spec
from pathlib import Path

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
# 只拉必要 PIL 钩子，避免 collect_all 把整个 Pillow 生态 + numpy 撑爆体积
hiddenimports = [
    "PIL._tkinter_finder",
    "PIL.Image",
    "PIL.ImageTk",
    "PIL.ImageSequence",
    "PIL.PngImagePlugin",
    "PIL.GifImagePlugin",
    "PIL.IcoImagePlugin",
    "PIL.JpegImagePlugin",
]

a = Analysis(
    [str(pkg / "entry_main.py")],
    pathex=[str(src), str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "numpy",
        "pytest",
        "unittest",
        "tkinter.test",
        "pydoc",
        "doctest",
        "IPython",
        "matplotlib",
        "scipy",
        "pandas",
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

# onefile：全部打进单个 DesktopPet.exe（无 _internal、无旁路 .py）
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
    upx=False,  # UPX 可能导致图标/杀软异常
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
