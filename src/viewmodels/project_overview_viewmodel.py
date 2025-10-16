# Rev 0.6.5 — include phase_id, priority_id in emitted info
from __future__ import annotations
from typing import Optional, Dict, Any
from PySide6.QtCore import QObject, Signal

class ProjectOverviewViewModel(QObject):
    """
    Emits:
      loaded({
        "id": int,
        "name": str,
        "description": str|None,
        "tasks_total": int,
        "subtasks_total": int,
        "phase_id": int,        # NEW
        "priority_id": int,     # NEW
      })
    """
    loaded = Signal(dict)

    def __init__(self, projects_repo, tasks_repo, subtasks_repo):
        super().__init__()
        self._projects = projects_repo
        self._tasks = tasks_repo
        self._subs = subtasks_repo
        self._last: Optional[Dict[str, Any]] = None

    def load(self, project_id: int) -> None:
        proj = self._projects.get_project(project_id)
        if not proj:
            self._last = None
            self.loaded.emit({})
            return

        tasks_total = self._tasks.count_tasks_total(project_id=project_id)
        if hasattr(self._subs, "count_subtasks_total_by_project"):
            subtasks_total = self._subs.count_subtasks_total_by_project(project_id=project_id)
        else:
            subtasks_total = 0

        info = {
            "id": int(proj.get("id")),
            "name": proj.get("name") or "",
            "description": proj.get("description"),
            "tasks_total": int(tasks_total),
            "subtasks_total": int(subtasks_total),
            "phase_id": int(proj.get("phase_id", 1)),
            "priority_id": int(proj.get("priority_id", 2)),
        }
        self._last = info
        self.loaded.emit(info)

    def last(self) -> Optional[Dict[str, Any]]:
        return self._last
