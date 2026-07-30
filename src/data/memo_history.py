"""
备忘录历史版本：类似 GitHub 的增删记录 + 可恢复快照。

每次内容变化保存时写入一条版本：
- 全文快照 .md
- 相对上一版的 +added / -removed 行级 diff 摘要
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from config import DATA_DIR

HISTORY_ROOT = DATA_DIR / "memo_history"
MAX_VERSIONS_PER_NOTE = 80

_ITEM_LINE_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")


def _note_key(note_path: Path) -> str:
    """用笔记绝对路径生成稳定目录名。"""
    resolved = str(note_path.resolve()).lower().replace("\\", "/")
    digest = hashlib.sha1(resolved.encode("utf-8")).hexdigest()[:12]
    stem = re.sub(r"[^\w\-]+", "_", note_path.stem)[:40] or "note"
    return f"{stem}_{digest}"


def history_dir_for(note_path: Path) -> Path:
    return HISTORY_ROOT / _note_key(note_path)


def _index_path(hdir: Path) -> Path:
    return hdir / "index.json"


def _load_index(hdir: Path) -> dict[str, Any]:
    path = _index_path(hdir)
    if not path.exists():
        return {"note": "", "versions": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"note": "", "versions": []}
        data.setdefault("versions", [])
        return data
    except (json.JSONDecodeError, OSError):
        return {"note": "", "versions": []}


def _save_index(hdir: Path, data: dict[str, Any]) -> None:
    hdir.mkdir(parents=True, exist_ok=True)
    _index_path(hdir).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def content_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def extract_item_lines(text: str) -> list[str]:
    """提取列表项正文（忽略标题/空行），用于增删 diff。"""
    items: list[str] = []
    for line in text.splitlines():
        m = _ITEM_LINE_RE.match(line)
        if m:
            items.append(m.group(1).strip())
    return items


def line_diff(old_text: str, new_text: str) -> tuple[list[str], list[str]]:
    """简单行级增删（基于列表项；若无列表则全文行）。"""
    old_items = extract_item_lines(old_text)
    new_items = extract_item_lines(new_text)
    if not old_items and not new_items:
        old_set = [ln.rstrip() for ln in old_text.splitlines() if ln.strip()]
        new_set = [ln.rstrip() for ln in new_text.splitlines() if ln.strip()]
    else:
        old_set, new_set = old_items, new_items

    from collections import Counter

    oc, nc = Counter(old_set), Counter(new_set)
    added: list[str] = []
    removed: list[str] = []
    for item, count in nc.items():
        delta = count - oc.get(item, 0)
        if delta > 0:
            added.extend([item] * delta)
    for item, count in oc.items():
        delta = count - nc.get(item, 0)
        if delta > 0:
            removed.extend([item] * delta)
    return added, removed


@dataclass
class HistoryVersion:
    id: str
    time: str
    hash: str
    summary: str
    added: list[str]
    removed: list[str]
    content_file: str
    note_path: str = ""

    def full_path(self, hdir: Path) -> Path:
        return hdir / self.content_file


def list_versions(note_path: Path) -> list[HistoryVersion]:
    hdir = history_dir_for(note_path)
    data = _load_index(hdir)
    versions: list[HistoryVersion] = []
    for raw in data.get("versions") or []:
        if not isinstance(raw, dict):
            continue
        versions.append(
            HistoryVersion(
                id=str(raw.get("id", "")),
                time=str(raw.get("time", "")),
                hash=str(raw.get("hash", "")),
                summary=str(raw.get("summary", "")),
                added=list(raw.get("added") or []),
                removed=list(raw.get("removed") or []),
                content_file=str(raw.get("content_file", "")),
                note_path=str(raw.get("note_path", note_path)),
            )
        )
    # 新 → 旧（按时间，同秒再比 id）
    versions.sort(key=lambda v: (v.time, v.id), reverse=True)
    return versions


def read_version_content(note_path: Path, version: HistoryVersion) -> str | None:
    hdir = history_dir_for(note_path)
    path = version.full_path(hdir)
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def record_version(note_path: Path, new_text: str, *, force: bool = False) -> HistoryVersion | None:
    """
    若内容相对最新快照有变化，则写入新版本。
    返回新建的版本；无变化返回 None。
    """
    if not new_text.endswith("\n"):
        new_text = new_text + "\n"

    hdir = history_dir_for(note_path)
    hdir.mkdir(parents=True, exist_ok=True)
    data = _load_index(hdir)
    data["note"] = str(note_path)
    versions = data.get("versions") or []

    new_hash = content_hash(new_text)
    if versions and not force:
        last = versions[-1] if isinstance(versions[-1], dict) else {}
        if str(last.get("hash", "")) == new_hash:
            return None

    # 上一版全文
    old_text = ""
    if versions:
        last = versions[-1]
        if isinstance(last, dict) and last.get("content_file"):
            prev = hdir / str(last["content_file"])
            if prev.exists():
                try:
                    old_text = prev.read_text(encoding="utf-8")
                except OSError:
                    old_text = ""

    added, removed = line_diff(old_text, new_text)
    now = datetime.now()
    vid = now.strftime("%Y%m%dT%H%M%S") + f"_{new_hash[:6]}"
    # 避免同秒冲突
    content_file = f"{vid}.md"
    i = 1
    while (hdir / content_file).exists():
        content_file = f"{vid}_{i}.md"
        i += 1
        vid = f"{vid}_{i}"

    (hdir / content_file).write_text(new_text, encoding="utf-8")

    if not old_text.strip():
        summary = "初始版本" if not versions else f"更新 +{len(added)} -{len(removed)}"
    else:
        summary = f"+{len(added)} -{len(removed)}"
        if added and not removed:
            summary = f"新增 {len(added)} 条"
        elif removed and not added:
            summary = f"删除 {len(removed)} 条"
        elif added or removed:
            summary = f"变更 +{len(added)} -{len(removed)}"
        else:
            summary = "正文调整"

    entry = {
        "id": vid,
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "hash": new_hash,
        "summary": summary,
        "added": added[:50],
        "removed": removed[:50],
        "content_file": content_file,
        "note_path": str(note_path),
    }
    versions.append(entry)

    # 裁剪过旧版本
    while len(versions) > MAX_VERSIONS_PER_NOTE:
        old = versions.pop(0)
        if isinstance(old, dict) and old.get("content_file"):
            stale = hdir / str(old["content_file"])
            try:
                if stale.exists():
                    stale.unlink()
            except OSError:
                pass

    data["versions"] = versions
    _save_index(hdir, data)

    return HistoryVersion(
        id=entry["id"],
        time=entry["time"],
        hash=entry["hash"],
        summary=entry["summary"],
        added=list(entry["added"]),
        removed=list(entry["removed"]),
        content_file=entry["content_file"],
        note_path=entry["note_path"],
    )


def restore_version(note_path: Path, version: HistoryVersion) -> str:
    """读取历史内容并写入笔记文件，同时记一条「从历史恢复」版本。"""
    content = read_version_content(note_path, version)
    if content is None:
        raise FileNotFoundError(f"历史快照不存在: {version.id}")
    note_path.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content = content + "\n"
    note_path.write_text(content, encoding="utf-8")
    # 恢复也记一笔，方便再回退
    record_version(note_path, content, force=True)
    return content
