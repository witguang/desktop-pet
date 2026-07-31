"""安装向导入口（开发调试用）。生产分发已合并进 DesktopPet.exe 首次启动。

  python packaging/entry_install.py
"""
from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    if getattr(sys, "frozen", False):
        return
    root = Path(__file__).resolve().parent.parent
    src = root / "src"
    if src.is_dir():
        s = str(src.resolve())
        if s in sys.path:
            sys.path.remove(s)
        sys.path.insert(0, s)


def main() -> int:
    _ensure_src_on_path()
    from ui.setup_wizard import SetupWizard

    ok = SetupWizard(mode="install").run()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
