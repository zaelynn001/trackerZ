# -*- coding: utf-8 -*-
# File: src/viewmodels/tasks_viewmodel.py
# M04: ViewModel for listing tasks with filters and keeping Total • Filtered counters in sync.

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from PySide6.QtCore import QObject, Signal, Slot, QRunnable, QThreadPool

from src.repositories.sqlite_task_repository import SQLiteTaskRepository


@dataclass(frozen=True)
class TaskRow:
    id: int
    project_id: int
    title: str
    phase: str
    created_at: str
    updated_at: str


class _LoadTasksJob(QRunnable):
    """
    Background job: fetch total count, filtered rows, and filtered count.
    Emits back via the provided callback (Qt signal).
    """

    def __init__(
        self,
        repo: SQLiteTaskRepository,
        project_id: Optional[int],
        phase_id: Optional[int],
        search_text: str,
        on_result,
    ):
        super().__init__()
        self._repo = repo
        self._project_id = project_id
        self._phase_id = phase_id
        self._search_text = search_text
        self._on_result = on_result

    def run(self) -> None:
        total = self._repo.count_tasks_total(project_id=self._project_id)
        rows = self._repo.list_tasks_filtered(
            project_id=self._project_id,
            phase_id=self._phase_id,
            search=self._search_text or None,
            limit=500,  # pragmatic cap; adjust as needed
            offset=0,
        )
        filtered = len(rows)
        self._on_result(total, rows, filtered)


class TasksViewModel(QObject):
    """
    Exposes:
      - countersChanged(total:int, filtered:int)
      - rowsChanged(rows:list[TaskRow])
      - busyChanged(bool)
    Inputs:
      - setProject(project_id)
      - setPhaseFilter(phase_id or None)
      - setSearch(text)
      - refresh()
    """

    countersChanged = Signal(int, int)  # total, filtered
    rowsChanged = Signal(list)          # list[TaskRow]
    busyChanged = Signal(bool)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._repo = SQLiteTaskRepository()
        self._pool = QThreadPool.globalInstance()

        self._project_id: Optional[int] = None
        self._phase_id: Optional[int] = None
        self._search: str = ""

        self._is_busy = False
        self._last_total = 0
        self._last_filtered = 0

    # -------- Public API --------

    @Slot(int)
    def setProject(self, project_id: int) -> None:
        if self._project_id != project_id:
            self._project_id = project_id
            self.refresh()

    @Slot(object)  # None or int
    def setPhaseFilter(self, phase_id: Optional[int]) -> None:
        if self._phase_id != phase_id:
            self._phase_id = phase_id
            self.refresh()

    @Slot(str)
    def setSearch(self, text: str) -> None:
        text = text.strip()
        if self._search != text:
            self._search = text
            self.refresh()

    @Slot()
    def refresh(self) -> None:
        if self._is_busy:
            # keep it simple: allow the current run to finish, then the next UI action will retrigger
            return
        if self._project_id is None:
            # Nothing to load yet; emit zeros to keep UI consistent
            self._emit_counters(0, 0)
            self.rowsChanged.emit([])
            return

        self._set_busy(True)

        def on_result(total: int, raw_rows: List[dict], filtered: int):
            rows = [
                TaskRow(
                    id=r["id"],
                    project_id=r["project_id"],
                    title=r["title"],
                    phase=r["phase_name"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
                for r in raw_rows
            ]
            self._last_total = total
            self._last_filtered = filtered
            self._emit_counters(total, filtered)
            self.rowsChanged.emit(rows)
            self._set_busy(False)

        job = _LoadTasksJob(
            repo=self._repo,
            project_id=self._project_id,
            phase_id=self._phase_id,
            search_text=self._search,
            on_result=on_result,
        )
        self._pool.start(job)

    # -------- Internals --------

    def _emit_counters(self, total: int, filtered: int) -> None:
        self.countersChanged.emit(total, filtered)

    def _set_busy(self, value: bool) -> None:
        if self._is_busy != value:
            self._is_busy = value
            self.busyChanged.emit(value)

