from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from PySide6.QtCore import QObject, Signal, QRunnable, Slot, QThreadPool

@dataclass
class Filters:
    phase: Optional[str] = None
    search: str = ""

class _LoadTasksJob(QRunnable):
    def __init__(self, repo, project_id: int, filters: Filters, cb):
        super().__init__()
        self.repo = repo
        self.project_id = project_id
        self.filters = filters
        self.cb = cb
    def run(self):
        tasks = self.repo.list_tasks(self.project_id, self.filters.phase, self.filters.search)
        total = self.repo.count_tasks_total(self.project_id)
        self.cb(tasks, total)

class TasksViewModel(QObject):
    projectsChanged = Signal(list)
    phasesChanged = Signal(list)
    tasksChanged = Signal(list, int)  # tasks, total_count
    projectChanged = Signal(int)
    filtersChanged = Signal(object)

    def __init__(self, repo, thread_pool: QThreadPool):
        super().__init__()
        self.repo = repo
        self.tp = thread_pool
        self.current_project_id: Optional[int] = None
        self.filters = Filters()

    def bootstrap(self):
        projects = self.repo.list_projects()
        phases = self.repo.list_phases()
        self.projectsChanged.emit(projects)
        self.phasesChanged.emit(phases)
        if projects:
            self.set_project(projects[0]["id"])

    @Slot(int)
    def set_project(self, project_id: int):
        self.current_project_id = project_id
        self.projectChanged.emit(project_id)
        self.reload_tasks()

    @Slot(str)
    def set_phase(self, phase: Optional[str]):
        self.filters.phase = phase or None
        self.filtersChanged.emit(self.filters)
        self.reload_tasks()

    @Slot(str)
    def set_search(self, text: str):
        self.filters.search = text or ""
        self.filtersChanged.emit(self.filters)
        self.reload_tasks()

    def reload_tasks(self):
        if self.current_project_id is None: return
        job = _LoadTasksJob(self.repo, self.current_project_id, self.filters, self._on_tasks_loaded)
        self.tp.start(job)

    def _on_tasks_loaded(self, tasks, total_count):
        self.tasksChanged.emit(tasks, total_count)

