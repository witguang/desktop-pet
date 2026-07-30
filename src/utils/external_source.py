"""
打包版（PyInstaller）优先加载「安装目录旁」的 .py 源码。

GitHub 源码 zip 更新只会覆盖 exe 旁的 .py，不会重写 exe 内 PYZ。
若不走本加载器，桌宠永远跑打包时的旧逻辑（例如一直提示「请关闭后重启」）。
"""
from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
import sys
from pathlib import Path

# 允许从安装目录热更新的顶层包/模块
_OUR_TOP = frozenset(
    {
        "app",
        "config",
        "main",
        "core",
        "data",
        "ui",
        "utils",
    }
)


class _ExternalSourceFinder(importlib.abc.MetaPathFinder):
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def find_spec(self, fullname: str, path, target=None):  # noqa: ANN001
        top = fullname.split(".", 1)[0]
        if top not in _OUR_TOP:
            return None

        parts = fullname.split(".")
        # package: root/a/b/__init__.py  or module: root/a/b.py
        pkg_dir = self.root.joinpath(*parts)
        init_py = pkg_dir / "__init__.py"
        mod_py = self.root.joinpath(*parts[:-1], parts[-1] + ".py") if len(parts) >= 1 else None

        if init_py.is_file():
            # package
            return importlib.util.spec_from_file_location(
                fullname,
                str(init_py),
                submodule_search_locations=[str(pkg_dir)],
            )
        if mod_py is not None and mod_py.is_file():
            return importlib.util.spec_from_file_location(fullname, str(mod_py))
        # namespace package without __init__ (rare)
        if pkg_dir.is_dir():
            spec = importlib.machinery.ModuleSpec(fullname, None, is_package=True)
            spec.submodule_search_locations = [str(pkg_dir)]
            return spec
        return None


def install_dir_for_frozen() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    return Path(sys.executable).resolve().parent


def enable_external_sources() -> bool:
    """
    若为打包版且 exe 旁存在 app.py，则优先从磁盘加载业务代码。
    必须在 import app / config 等之前调用。
    """
    root = install_dir_for_frozen()
    if root is None:
        return False
    if not (root / "app.py").is_file():
        return False

    # 清掉可能已从 PYZ 载入的旧业务模块，强制之后走磁盘
    for name in list(sys.modules):
        top = name.split(".", 1)[0]
        if top in _OUR_TOP:
            del sys.modules[name]

    finder = _ExternalSourceFinder(root)
    # 插到最前，优先于 PyInstaller FrozenImporter
    sys.meta_path.insert(0, finder)

    root_s = str(root)
    if root_s in sys.path:
        sys.path.remove(root_s)
    sys.path.insert(0, root_s)
    return True
