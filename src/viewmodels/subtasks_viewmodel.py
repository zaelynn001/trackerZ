# Rev 0.6.8
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from repositories.sqlite_subtask_updates_repository import SQLiteSubtaskUpdatesRepository


class SubtasksViewModel(QObject):
    """
    VM for Subtasks of a given Task.
    Emits:
      - subtasksReloaded(total: int, rows: list[dict])
      - timelineLoaded(subtask_id: int, updates: list[dict])
    """

    subtasksReloaded = Signal(int, list)
    timelineLoaded = Signal(int, list)

    def __init__(self, subtasks_repo):
        super().__init__()
        self._subs = subtasks_repo
        self._task_id: Optional[int] = None
        self._phase_id: Optional[int] = None
        self._search: Optional[str] = None
        self._updates_repo: Optional[SQLiteSubtaskUpdatesRepository] = None

    # ---- filters ----
    def set_filters(self, task_id: int, phase_id: Optional[int] = None, search: Optional[str] = None) -> None:
        self._task_id = task_id
        self._phase_id = phase_id
        self._search = search

    # ---- queries ----
    def reload(self) -> None:
        if self._task_id is None:
            self.subtasksReloaded.emit(0, [])
            return
        total = self._subs.count_subtasks_total(task_id=self._task_id, phase_id=self._phase_id, search=self._search)
        rows = self._subs.list_subtasks_filtered(task_id=self._task_id, phase_id=self._phase_id, search=self._search)
        self.subtasksReloaded.emit(total, rows)

    # ---- commands ----
    def create_subtask(self, *, task_id: int, name: str, description: str | None,
                       phase_id: int = 1, priority_id: int | None = None, note_on_create: str | None = None) -> int | None:
        try:
            sid = self._repo.create_subtask(
                task_id=task_id,
                name=name,
                description=description,
                phase_id=phase_id,
                priority_id=(priority_id if priority_id is not None else 2),
                note_on_create=note_on_create,
            )
            self.reload()
            return sid
        except Exception:
            self.reload()
            return None

    def set_subtask_priority(self, *, subtask_id: int, new_priority_id: int, note: str | None = None) -> bool:
        try:
            ok = self._repo.set_subtask_priority(subtask_id, new_priority_id, note=note)
            self.reload()
            return bool(ok)
        except Exception:
            self.reload()
            return False


    def update_subtask_fields(
        self,
        *,
        subtask_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        note: Optional[str] = None,
    ) -> bool:
        ok = self._subs.update_subtask_fields(subtask_id, name=name, description=description, note=note)
        if ok:
            self.reload()
        return ok

    def change_subtask_phase(
        self,
        *,
        subtask_id: int,
        new_phase_id: int,
        reason: Optional[str] = None,
        note: Optional[str] = None,
    ) -> bool:
        ok = self._subs.change_subtask_phase(subtask_id, new_phase_id, reason=reason, note=note)
        if ok:
            self.reload()
        return ok

    def delete_subtask(self, subtask_id: int) -> bool:
        ok = self._subs.delete_subtask(subtask_id)
        if ok:
            self.reload()
        return ok

    # ---- timeline ----
    def load_timeline(self, subtask_id: int, *, newest_first: bool = True) -> None:
        repo = self._get_updates_repo()
        updates = repo.list_updates_for_subtask(subtask_id, order_desc=newest_first)
        self.timelineLoaded.emit(subtask_id, updates)

    # ---- internals ----
    def _get_updates_repo(self) -> SQLiteSubtaskUpdatesRepository:
        if self._updates_repo is not None:
            return self._updates_repo

        db_handle = getattr(self._subs, "_db_or_conn", None)
        if db_handle is None:
            possible = getattr(self._subs, "_conn", None)
            db_handle = possible if possible is not None else db_handle
        if db_handle is None:
            raise RuntimeError("SubtasksViewModel: unable to locate DB handle from subtask repo for timeline access.")

        self._updates_repo = SQLiteSubtaskUpdatesRepository(db_handle)
        return self._updates_repo
