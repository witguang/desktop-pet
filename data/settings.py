
"""用户设置（当前角色、Obsidian 笔记目录、更新源等）持久化。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import DATA_DIR, DEFAULT_CHARACTER_ID, DEFAULT_MEMO_DIR_NAME, SETTINGS_FILE
from utils.updater import BUILTIN_GH_PROXIES, DEFAULT_GITHUB_BRANCH, DEFAULT_GITHUB_REPO


def default_memo_dir() -> Path:
    return DATA_DIR / DEFAULT_MEMO_DIR_NAME


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
        """Obsidian / 备忘录 .md 存放目录。"""
        raw = self._data.get("memo_dir") or self._data.get("obsidian_dir")
        if raw and str(raw).strip():
            return Path(str(raw).strip()).expanduser()
        return default_memo_dir()

    @memo_dir.setter
    def memo_dir(self, value: str | Path) -> None:
        self._data["memo_dir"] = str(Path(value).expanduser())
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

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()
