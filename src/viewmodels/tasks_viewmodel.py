# Rev 0.5.1
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import QObject, Signal, Slot, QRunnable, QThreadPool


class _ReloadTasksJob(QRunnable):
    def __init__(self, repo, project_id: int, phase_id: Optional[int], callback):
        super().__init__()
        self._repo = repo
        self._project_id = project_id
        self._phase_id = phase_id
        self._callback = callback

    def run(self):
        total = self._repo.count_tasks_total(project_id=self._project_id)
        rows = self._repo.list_tasks_filtered(project_id=self._project_id, phase_id=self._phase_id)
        self._callback(total, rows)


class TasksViewModel(QObject):
    # Signals for UI
    tasksReloaded = Signal(int, list)     # total, rows
    taskCreated = Signal(int)             # task_id
    taskUpdated = Signal(int)
    taskDeleted = Signal(int)
    taskPhaseChanged = Signal(int, int, int)  # task_id, old_phase_id, new_phase_id
    noteAdded = Signal(int, int)          # task_id, note_id
    timelineLoaded = Signal(int, list)    # task_id, updates

    def __init__(self, repo, thread_pool: Optional[QThreadPool] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._repo = repo
        self._project_id: Optional[int] = None
        self._phase_id: Optional[int] = None
        self._pool = thread_pool or QThreadPool.globalInstance()

    # ------------ Listing ------------
    def set_filters(self, project_id: int, phase_id: Optional[int] = None):
        self._project_id = project_id
        self._phase_id = phase_id

    @Slot()
    def reload(self):
        if self._project_id is None:
            self.tasksReloaded.emit(0, [])
            return
        job = _ReloadTasksJob(self._repo, self._project_id, self._phase_id, self.tasksReloaded.emit)
        self._pool.start(job)

    # ------------ CRUD ------------
    @Slot(int, str, str, int)
    def create_task(self, project_id: int, name: str, description: str, phase_id: int = 1):
        task_id = self._repo.create_task(project_id, name, description, phase_id)
        self.taskCreated.emit(task_id)
        self.reload()

    @Slot(int, str, str)
    def edit_task(self, task_id: int, name: str, description: str):
        self._repo.update_task(task_id, name=name, description=description)
        self.taskUpdated.emit(task_id)
        self.reload()

    @Slot(int)
    def delete_task(self, task_id: int):
        self._repo.delete_task(task_id)
        self.taskDeleted.emit(task_id)
        self.reload()

    # ------------ Phase change ------------
    @Slot(int, int, str)
    def change_phase(self, task_id: int, new_phase_id: int, note: str = ""):
        # Fetch current phase to emit both old and new
        row = self._repo._conn.execute("SELECT phase_id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        old_phase_id = row[0] if row else -1
        self._repo.change_task_phase(task_id, new_phase_id, note)
        self.taskPhaseChanged.emit(task_id, old_phase_id, new_phase_id)
        self.reload()

    # ------------ Timeline ------------
    @Slot(int)
    def load_timeline(self, task_id: int):
        updates = self._repo.list_task_updates(task_id)
        self.timelineLoaded.emit(task_id, updates)

    @Slot(int, str)
    def add_note(self, task_id: int, note: str):
        note_id = self._repo.add_task_note(task_id, note)
        self.noteAdded.emit(task_id, note_id)
        self.load_timeline(task_id)
