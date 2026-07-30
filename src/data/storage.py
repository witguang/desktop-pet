
"""
本地任务 / 番茄钟日志存储（JSON）。

时光机功能从此处读取历史记录。
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from config import DATA_DIR, LOG_FILE


class TaskStorage:
    """线程安全的轻量 JSON 存储。"""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or LOG_FILE
        self._lock = threading.RLock()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"version": 1, "sessions": [], "tasks": []})

    # ------------------------------------------------------------------
    # 内部 IO
    # ------------------------------------------------------------------
    def _read(self) -> dict[str, Any]:
        with self._lock:
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                data = {"version": 1, "sessions": [], "tasks": []}
                self._write(data)
                return data

    def _write(self, data: dict[str, Any]) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp.replace(self.path)

    # ------------------------------------------------------------------
    # 任务
    # ------------------------------------------------------------------
    def add_task(self, title: str, note: str = "") -> dict[str, Any]:
        """登记一个新任务（未完成）。"""
        task = {
            "id": str(uuid.uuid4()),
            "title": title.strip() or "未命名任务",
            "note": note,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "date": date.today().isoformat(),
            "completed": False,
            "completed_at": None,
            "focus_sessions": 0,
            "focus_minutes": 0,
        }
        data = self._read()
        data["tasks"].append(task)
        self._write(data)
        return task

    def complete_task(self, task_id: str) -> bool:
        data = self._read()
        for task in data["tasks"]:
            if task["id"] == task_id:
                task["completed"] = True
                task["completed_at"] = datetime.now().isoformat(timespec="seconds")
                self._write(data)
                return True
        return False

    def get_tasks_by_date(self, day: date | str) -> list[dict[str, Any]]:
        day_str = day.isoformat() if isinstance(day, date) else day
        data = self._read()
        return [t for t in data["tasks"] if t.get("date") == day_str]

    def get_today_tasks(self) -> list[dict[str, Any]]:
        return self.get_tasks_by_date(date.today())

    def attach_session_to_task(self, task_id: str, minutes: int) -> None:
        data = self._read()
        for task in data["tasks"]:
            if task["id"] == task_id:
                task["focus_sessions"] = int(task.get("focus_sessions", 0)) + 1
                task["focus_minutes"] = int(task.get("focus_minutes", 0)) + minutes
                self._write(data)
                return

    # ------------------------------------------------------------------
    # 番茄钟会话
    # ------------------------------------------------------------------
    def log_pomodoro_session(
        self,
        *,
        task_title: str,
        task_id: str | None,
        mode: str,
        planned_minutes: int,
        actual_seconds: int,
        completed: bool,
    ) -> dict[str, Any]:
        """
        记录一次专注/休息会话。

        mode: "focus" | "break"
        """
        session = {
            "id": str(uuid.uuid4()),
            "task_id": task_id,
            "task_title": task_title,
            "mode": mode,
            "planned_minutes": planned_minutes,
            "actual_seconds": actual_seconds,
            "completed": completed,
            "started_at": (
                datetime.now() - timedelta(seconds=actual_seconds)
            ).isoformat(timespec="seconds"),
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "date": date.today().isoformat(),
        }
        data = self._read()
        data["sessions"].append(session)
        self._write(data)

        if completed and mode == "focus" and task_id:
            self.attach_session_to_task(task_id, planned_minutes)

        return session

    def get_sessions_by_date(self, day: date | str) -> list[dict[str, Any]]:
        day_str = day.isoformat() if isinstance(day, date) else day
        data = self._read()
        return [s for s in data["sessions"] if s.get("date") == day_str]

    def list_available_dates(self) -> list[str]:
        """返回有记录的日期列表（倒序）。"""
        data = self._read()
        days = set()
        for t in data["tasks"]:
            if t.get("date"):
                days.add(t["date"])
        for s in data["sessions"]:
            if s.get("date"):
                days.add(s["date"])
        return sorted(days, reverse=True)

    def get_day_summary(self, day: date | str) -> dict[str, Any]:
        """时光机面板用：某日汇总。"""
        day_str = day.isoformat() if isinstance(day, date) else day
        tasks = self.get_tasks_by_date(day_str)
        sessions = self.get_sessions_by_date(day_str)
        focus_sessions = [s for s in sessions if s.get("mode") == "focus"]
        completed_focus = [s for s in focus_sessions if s.get("completed")]
        total_focus_seconds = sum(int(s.get("actual_seconds", 0)) for s in completed_focus)
        return {
            "date": day_str,
            "tasks": tasks,
            "sessions": sessions,
            "task_count": len(tasks),
            "completed_task_count": sum(1 for t in tasks if t.get("completed")),
            "focus_count": len(completed_focus),
            "focus_minutes": round(total_focus_seconds / 60, 1),
        }
