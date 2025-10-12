# Rev 0.4.1

# trackerZ – TasksViewModel (Rev 0.4.1)
# Thin coordinator between the TasksView and the tasks repository.

from typing import Optional, Tuple

class TasksViewModel:
    def __init__(self, tasks_repo):
        self._repo = tasks_repo

    def list_tasks(self, project_id: int, phase_id: Optional[int]) -> Tuple[int, list[dict]]:
        """
        Returns (total_count_for_project, filtered_rows).
        Each row should include at least: {id, name, phase_name}
        """
        # Total for the project, regardless of filters
        total = self._repo.count_tasks_total(project_id=project_id)

        # Filtered rows for current UI selection
        rows = self._repo.list_tasks_filtered(project_id=project_id, phase_id=phase_id)
        # Normalize keys defensively to keep the UI happy
        for row in rows:
            # Prefer 'name' over legacy 'title'
            if "name" not in row and "title" in row:
                row["name"] = row["title"]
            # Prefer 'phase_name' if only 'phase' exists
            if "phase_name" not in row and "phase" in row:
                row["phase_name"] = row["phase"]

        return total, rows

