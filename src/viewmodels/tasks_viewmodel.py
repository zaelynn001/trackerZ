# Rev 0.1.1
# src/viewmodels/tasks_viewmodel.py
from __future__ import annotations

DEFAULT_PHASE_OPEN = 1  # phase_id for "Open"

class TasksViewModel:
    def __init__(self, tasks_repo, phases_repo, subtasks_repo):
        """
        tasks_repo:
          count_tasks_total(project_id:int) -> int
          list_tasks_filtered(project_id:int, phase_id:int|None) -> [(id,title,phase,updated)]
        phases_repo:
          list_phases() -> [(id,name)]
        subtasks_repo:
          count_subtasks_total(task_id:int) -> int
          list_subtasks_filtered(task_id:int, phase_id:int|None) -> [(id,title,phase,updated)]
        """
        self._tasks_repo = tasks_repo
        self._subtasks_repo = subtasks_repo
        self._phases_repo = phases_repo

    def list_phases(self):
        return self._phases_repo.list_phases()

    def list_tasks(self, project_id: int, phase_id: int | None):
        return self._tasks_repo.list_tasks_filtered(project_id=project_id, phase_id=phase_id)


    def list_subtasks(self, *args, **kwargs):
        project_id = kwargs.get("project_id")
        task_id    = kwargs.get("task_id")
        phase_id   = kwargs.get("phase_id")
        if project_id is not None:
            return self._subtasks_repo.list_subtasks_for_project(project_id, phase_id)
        if task_id is None and args:
            task_id = args[0]; 
            if len(args) > 1: phase_id = args[1]
        return self._subtasks_repo.list_subtasks_for_task(task_id, phase_id)
        
    def create_task(self, project_id: int, name: str, note: str | None, phase_id: int = DEFAULT_PHASE_OPEN) -> int:
        if not name:
            raise ValueError("name required")
        return self._tasks_repo.insert_task(project_id, name, phase_id, note)

    def create_subtask(self, task_id: int, name: str, note: str | None, phase_id: int = DEFAULT_PHASE_OPEN) -> int:
        if not name:
            raise ValueError("name required")
        return self._subtasks_repo.insert_subtask(task_id, name, phase_id, note)
