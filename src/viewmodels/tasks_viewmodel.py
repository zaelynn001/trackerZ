# Rev 0.6.5 — Fix repo attr + wire phase/priority ops
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from repositories.sqlite_task_updates_repository import SQLiteTaskUpdatesRepository


class TasksViewModel(QObject):
    """
    ViewModel that fronts Task CRUD and exposes a simple timeline loader.

    Emits:
      - tasksReloaded(total: int, rows: list[dict])
      - timelineLoaded(task_id: int, updates: list[dict])
    """

    tasksReloaded = Signal(int, list)
    timelineLoaded = Signal(int, list)

    def __init__(self, tasks_repo):
        super().__init__()
        self._tasks = tasks_repo  # <-- correct attribute
        self._project_id: Optional[int] = None
        self._phase_id: Optional[int] = None
        self._search: Optional[str] = None
        self._updates_repo: Optional[SQLiteTaskUpdatesRepository] = None

    # -------------------------
    # Filters / state
    # -------------------------
    def set_filters(
        self,
        project_id: int,
        phase_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> None:
        self._project_id = project_id
        self._phase_id = phase_id
        self._search = search

    # -------------------------
    # Queries
    # -------------------------
    def reload(self) -> None:
        if self._project_id is None:
            self.tasksReloaded.emit(0, [])
            return

        total = self._tasks.count_tasks_total(
            project_id=self._project_id,
            phase_id=self._phase_id,
            search=self._search,
        )
        rows = self._tasks.list_tasks_filtered(
            project_id=self._project_id,
            phase_id=self._phase_id,
            search=self._search,
            limit=500,
            offset=0,
        )
        self.tasksReloaded.emit(total, rows)

    # -------------------------
    # Commands (CRUD)
    # -------------------------
    def create_task(
        self,
        *,
        project_id: int,
        name: str,
        description: str | None,
        phase_id: int = 1,
        note_on_create: str | None = None,
        priority_id: int | None = None,
    ) -> int | None:
        """
        Create a task and reload the list. priority_id is optional; defaults to 2 (Medium).
        """
        try:
            tid = self._tasks.create_task(
                project_id=project_id,
                name=name,
                description=description or "",
                phase_id=phase_id,
                priority_id=(priority_id if priority_id is not None else 2),
                note_on_create=note_on_create,
            )
            self.reload()
            return tid
        except Exception:
            self.reload()
            return None

    def update_task_fields(
        self,
        *,
        task_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        note: Optional[str] = None,
    ) -> bool:
        ok = self._tasks.update_task_fields(
            task_id,
            name=name,
            description=description,
            note=note,
        )
        if ok:
            self.reload()
        return ok

    def delete_task(self, task_id: int) -> bool:
        ok = self._tasks.delete_task(task_id)
        if ok:
            self.reload()
        return ok

    # -------------------------
    # Phase / Priority ops
    # -------------------------
    def change_task_phase(
        self,
        *,
        task_id: int,
        new_phase_id: int,
        reason: Optional[str] = None,
        note: Optional[str] = None,
    ) -> bool:
        try:
            ok = self._tasks.change_task_phase(task_id, new_phase_id, reason=reason or "phase_change", note=note)
            if ok:
                self.reload()
            return ok
        except Exception:
            self.reload()
            return False

    def set_task_priority(self, *, task_id: int, new_priority_id: int, note: str | None = None) -> bool:
        try:
            ok = self._tasks.set_task_priority(task_id, new_priority_id, note=note)
            if ok:
                self.reload()
            return bool(ok)
        except Exception:
            self.reload()
            return False

    # -------------------------
    # Timeline
    # -------------------------
    def load_timeline(self, task_id: int, *, newest_first: bool = True) -> None:
        repo = self._get_updates_repo()
        updates = repo.list_updates_for_task(task_id, order_desc=newest_first)
        self.timelineLoaded.emit(task_id, updates)

    # -------------------------
    # Internals
    # -------------------------
    def _get_updates_repo(self) -> SQLiteTaskUpdatesRepository:
        if self._updates_repo is not None:
            return self._updates_repo

        # Reuse the same DB handle the tasks repo was built with.
        db_handle = getattr(self._tasks, "_db_or_conn", None)
        if db_handle is None:
            possible = getattr(self._tasks, "_conn", None)
            db_handle = possible if possible is not None else db_handle

        if db_handle is None:
            raise RuntimeError(
                "TasksViewModel: unable to locate DB handle from tasks repo for timeline access."
            )

        self._updates_repo = SQLiteTaskUpdatesRepository(db_handle)
        return self._updates_repo
