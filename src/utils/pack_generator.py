"""生成内置角色占位包（当 characters/ 为空时）。"""
from __future__ import annotations

from pathlib import Path

from config import CHARACTERS_DIR


def generate_all() -> None:
    """占位：角色包应已存在于 characters/。保留接口兼容。"""
    root = Path(CHARACTERS_DIR)
    root.mkdir(parents=True, exist_ok=True)
    print(f"characters dir: {root}")


if __name__ == "__main__":
    generate_all()
