"""
agent/memory.py
---------------
JSON-based session memory for TaskMind.
All file I/O lives here — no other module writes to disk directly.
"""

import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Subtask:
    id: str
    description: str
    status: str = "pending"       # pending | in_progress | done | skipped
    completed_at: Optional[float] = None


@dataclass
class Task:
    id: str
    raw_input: str
    title: str
    priority_score: float         # 0.0 – 10.0
    urgency: int                  # 1–5
    impact: int                   # 1–5
    effort: int                   # 1–5  (lower = easier)
    subtasks: list[Subtask] = field(default_factory=list)
    status: str = "pending"       # pending | in_progress | done
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    ai_notes: str = ""


@dataclass
class Session:
    tasks: list[Task] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    total_tasks_added: int = 0
    total_tasks_completed: int = 0


SESSION_FILE = os.getenv("TASKMIND_SESSION_FILE", ".taskmind_session.json")


def _load_raw() -> dict:
    if not os.path.exists(SESSION_FILE):
        return {}
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_raw(data: dict) -> None:
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_session() -> Session:
    """Load session from disk, or return a fresh one."""
    raw = _load_raw()
    if not raw:
        return Session()

    tasks = []
    for t in raw.get("tasks", []):
        subtasks = [Subtask(**s) for s in t.get("subtasks", [])]
        t_copy = {k: v for k, v in t.items() if k != "subtasks"}
        tasks.append(Task(**t_copy, subtasks=subtasks))

    return Session(
        tasks=tasks,
        created_at=raw.get("created_at", time.time()),
        last_updated=raw.get("last_updated", time.time()),
        total_tasks_added=raw.get("total_tasks_added", 0),
        total_tasks_completed=raw.get("total_tasks_completed", 0),
    )


def save_session(session: Session) -> None:
    """Persist the current session to disk."""
    session.last_updated = time.time()
    data = asdict(session)
    _save_raw(data)


def get_task_by_id(session: Session, task_id: str) -> Optional[Task]:
    for task in session.tasks:
        if task.id == task_id:
            return task
    return None


def mark_task_done(session: Session, task_id: str) -> bool:
    task = get_task_by_id(session, task_id)
    if task:
        task.status = "done"
        task.completed_at = time.time()
        for sub in task.subtasks:
            if sub.status != "done":
                sub.status = "done"
                sub.completed_at = time.time()
        session.total_tasks_completed += 1
        save_session(session)
        return True
    return False


def mark_subtask_done(session: Session, task_id: str, subtask_id: str) -> bool:
    task = get_task_by_id(session, task_id)
    if task:
        for sub in task.subtasks:
            if sub.id == subtask_id:
                sub.status = "done"
                sub.completed_at = time.time()
                # If all subtasks done, mark parent done too
                if all(s.status == "done" for s in task.subtasks):
                    task.status = "done"
                    task.completed_at = time.time()
                    session.total_tasks_completed += 1
                save_session(session)
                return True
    return False


def clear_session(session: Session) -> None:
    """Wipe all tasks from the session."""
    session.tasks = []
    session.total_tasks_added = 0
    session.total_tasks_completed = 0
    save_session(session)
