"""Standalone installer entry: choose install + memo dirs, copy app, shortcut."""
from __future__ import annotations

import sys


def main() -> int:
    from ui.setup_wizard import SetupWizard

    ok = SetupWizard(mode="install").run()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
