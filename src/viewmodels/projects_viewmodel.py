# Rev 0.1.1
# src/viewmodels/projects_viewmodel.py
from __future__ import annotations

class ProjectsViewModel:
    def __init__(self, projects_repo):
        """
        projects_repo must expose:
          list_projects() -> list[tuple[int, str]]
        """
        self._repo = projects_repo

    def list_projects(self) -> list[tuple[int, str]]:
        return self._repo.list_projects()
        
    def create_project(self, name: str, note: str | None) -> int:
        if not name:
            raise ValueError("name required")
        return self._projects_repo.insert_project(name, note)
