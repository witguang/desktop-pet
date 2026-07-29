
"""用户设置（当前角色、Obsidian 笔记目录、更新源等）持久化。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import (
    DATA_DIR,
    DEFAULT_CHARACTER_ID,
    DEFAULT_MEMO_DIR_NAME,
    MEAL_REMINDERS,
    SETTINGS_FILE,
    WATER_REMINDERS,
)
from utils.updater import BUILTIN_GH_PROXIES, DEFAULT_GITHUB_BRANCH, DEFAULT_GITHUB_REPO


def default_memo_dir() -> Path:
    return DATA_DIR / DEFAULT_MEMO_DIR_NAME


def _resolve_user_path(raw: str | Path) -> Path:
    """Expand ~ / 相对路径；相对路径以 DATA_DIR 为基准（可移植）。"""
    p = Path(str(raw).strip()).expanduser()
    if not p.is_absolute():
        p = DATA_DIR / p
    try:
        return p.resolve()
    except OSError:
        return p


def portable_path_str(path: Path) -> str:
    """
    写入设置时尽量可移植：
    - 默认备忘录目录 → 只存相对名 memos
    - 位于用户主目录下 → 存 ~/...
    - 其余 → 绝对路径（本机自定义位置）
    """
    path = Path(path).expanduser()
    try:
        path = path.resolve()
    except OSError:
        pass

    default = default_memo_dir()
    try:
        if path.resolve() == default.resolve():
            return DEFAULT_MEMO_DIR_NAME
    except OSError:
        pass

    # data_store 下的相对路径
    try:
        rel_data = path.resolve().relative_to(DATA_DIR.resolve())
        return str(rel_data).replace("\\", "/")
    except (ValueError, OSError):
        pass

    try:
        home = Path.home().resolve()
        rel_home = path.resolve().relative_to(home)
        return str(Path("~") / rel_home).replace("\\", "/")
    except (ValueError, OSError):
        pass

    return str(path)


def _parse_schedule(raw: Any, fallback: list[tuple[str, str]]) -> list[tuple[str, str]]:
    if not isinstance(raw, list) or not raw:
        return list(fallback)
    out: list[tuple[str, str]] = []
    for item in raw:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            t, p = str(item[0]).strip(), str(item[1]).strip()
            if t:
                out.append((t, p or "提醒"))
        elif isinstance(item, dict):
            t = str(item.get("time") or item.get("t") or "").strip()
            p = str(item.get("period") or item.get("label") or "提醒").strip()
            if t:
                out.append((t, p))
    return out or list(fallback)


class Settings:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or SETTINGS_FILE
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"character_id": DEFAULT_CHARACTER_ID}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {"character_id": DEFAULT_CHARACTER_ID}
            return data
        except (json.JSONDecodeError, OSError):
            return {"character_id": DEFAULT_CHARACTER_ID}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    @property
    def character_id(self) -> str:
        return str(self._data.get("character_id") or DEFAULT_CHARACTER_ID)

    @character_id.setter
    def character_id(self, value: str) -> None:
        self._data["character_id"] = value
        self.save()

    @property
    def memo_dir(self) -> Path:
        """Obsidian / 备忘录 .md 存放目录（支持 ~/相对路径）。"""
        raw = self._data.get("memo_dir") or self._data.get("obsidian_dir")
        if raw and str(raw).strip():
            return _resolve_user_path(raw)
        return default_memo_dir()

    @memo_dir.setter
    def memo_dir(self, value: str | Path) -> None:
        self._data["memo_dir"] = portable_path_str(Path(value))
        # 清理旧键，避免两套路径并存
        self._data.pop("obsidian_dir", None)
        self.save()

    # ---- 更新 / GitHub ----
    @property
    def github_repo(self) -> str:
        return str(self._data.get("github_repo") or DEFAULT_GITHUB_REPO).strip()

    @github_repo.setter
    def github_repo(self, value: str) -> None:
        self._data["github_repo"] = (value or DEFAULT_GITHUB_REPO).strip()
        self.save()

    @property
    def github_branch(self) -> str:
        return str(self._data.get("github_branch") or DEFAULT_GITHUB_BRANCH).strip() or "main"

    @github_branch.setter
    def github_branch(self, value: str) -> None:
        self._data["github_branch"] = (value or "main").strip()
        self.save()

    @property
    def gh_proxy(self) -> str:
        """当前选用的代理前缀；空或 direct = 直连。"""
        return str(self._data.get("gh_proxy") or BUILTIN_GH_PROXIES[0]).strip()

    @gh_proxy.setter
    def gh_proxy(self, value: str) -> None:
        self._data["gh_proxy"] = (value or "").strip()
        self.save()

    @property
    def custom_gh_proxies(self) -> list[str]:
        raw = self._data.get("custom_gh_proxies") or []
        if isinstance(raw, str):
            return [x.strip() for x in raw.splitlines() if x.strip()]
        if isinstance(raw, list):
            return [str(x).strip() for x in raw if str(x).strip()]
        return []

    @custom_gh_proxies.setter
    def custom_gh_proxies(self, value: list[str] | str) -> None:
        if isinstance(value, str):
            items = [x.strip() for x in value.splitlines() if x.strip()]
        else:
            items = [str(x).strip() for x in value if str(x).strip()]
        self._data["custom_gh_proxies"] = items
        self.save()

    # ---- 吃喝提醒时刻表 ----
    @property
    def water_reminders(self) -> list[tuple[str, str]]:
        return _parse_schedule(self._data.get("water_reminders"), list(WATER_REMINDERS))

    @water_reminders.setter
    def water_reminders(self, value: list[tuple[str, str]]) -> None:
        self._data["water_reminders"] = [[t, p] for t, p in value]
        self.save()

    @property
    def meal_reminders(self) -> list[tuple[str, str]]:
        return _parse_schedule(self._data.get("meal_reminders"), list(MEAL_REMINDERS))

    @meal_reminders.setter
    def meal_reminders(self, value: list[tuple[str, str]]) -> None:
        self._data["meal_reminders"] = [[t, p] for t, p in value]
        self.save()

    # ---- 开机自启（偏好；实际以系统 Startup 快捷方式为准）----
    @property
    def autostart(self) -> bool:
        return bool(self._data.get("autostart", False))

    @autostart.setter
    def autostart(self, value: bool) -> None:
        self._data["autostart"] = bool(value)
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()
