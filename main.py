"""桌宠入口。开发时从 src/ 加载；打包版优先加载 exe 旁已更新的源码。"""
from __future__ import annotations

import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _ensure_src_on_path() -> None:
    """开发布局：业务代码在 src/，把其加入 import 路径。"""
    if getattr(sys, "frozen", False):
        return
    src = _project_root() / "src"
    if not src.is_dir():
        return
    src_s = str(src.resolve())
    if src_s in sys.path:
        sys.path.remove(src_s)
    sys.path.insert(0, src_s)


def _bootstrap_external_sources() -> None:
    """打包 exe 若旁边有更新后的 app.py，则优先从磁盘加载，而不是 PYZ 旧代码。"""
    if not getattr(sys, "frozen", False):
        return
    root = Path(sys.executable).resolve().parent
    if not (root / "app.py").is_file():
        return

    # 直接从磁盘加载加载器，避免先 import 到 PYZ 里的旧 utils
    loader_py = root / "utils" / "external_source.py"
    if loader_py.is_file():
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "_desktop_pet_external_source",
            str(loader_py),
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.enable_external_sources()
            return

    # 无独立文件时：最小内联逻辑
    root_s = str(root)
    if root_s in sys.path:
        sys.path.remove(root_s)
    sys.path.insert(0, root_s)
    for name in list(sys.modules):
        top = name.split(".", 1)[0]
        if top in {"app", "config", "core", "data", "ui", "utils", "main"}:
            del sys.modules[name]


_ensure_src_on_path()
_bootstrap_external_sources()

from app import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
