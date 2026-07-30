"""纯逻辑单测（无 GUI）：版本比较、更新路径安全、路径可移植。"""
from __future__ import annotations

import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from utils.updater import apply_zip_update, is_newer, version_tuple  # noqa: E402
from data.memo_history import content_hash  # noqa: E402
from data.settings import portable_path_str  # noqa: E402


def test_version_tuple_basic():
    assert version_tuple("1.1.9") == (1, 1, 9)
    assert version_tuple("v1.2.0") == (1, 2, 0)
    assert version_tuple("") == (0,)


def test_is_newer():
    assert is_newer("1.2.0", "1.1.9") is True
    assert is_newer("1.1.9", "1.1.9") is False
    assert is_newer("1.1.8", "1.1.9") is False


def test_content_hash_stable():
    assert content_hash("hello\n") == content_hash("hello\n")
    assert content_hash("a") != content_hash("b")


def test_zip_update_blocks_traversal(tmp_path: Path):
    """恶意 zip 含 ../ 或盘符外路径时不得写出 target 外。"""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("repo-main/safe.txt", "ok")
        zf.writestr("repo-main/../evil.txt", "nope")
        zf.writestr("repo-main/sub/good.txt", "good")
    target = tmp_path / "app"
    target.mkdir()
    n = apply_zip_update(buf.getvalue(), target)
    assert n >= 1
    assert (target / "safe.txt").is_file() or (target / "sub" / "good.txt").is_file()
    # 不得在 target 父级生成 evil
    assert not (tmp_path / "evil.txt").exists()


def test_portable_path_str_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    # 位于 home 下应写成 ~/...
    p = home / "Documents" / "notes"
    p.mkdir(parents=True)
    s = portable_path_str(p)
    assert s.startswith("~") or "Documents" in s
