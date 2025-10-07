# trackerZ DAO
# Rev 0.1.1

from __future__ import annotations
from dataclasses import dataclass
from .db import DB

@dataclass
class DAO:
    """Direct SQL accessors used by services."""
    db: DB

    # Phase transitions
    def allowed_transitions(self) -> set[tuple[int, int]]:
        rows = self.db.execute(
            "SELECT from_phase_id, to_phase_id FROM phase_transitions"
        ).fetchall()
        return {(int(r[0]), int(r[1])) for r in rows}

    # Projects
    def list_projects(self):
        return self.db.execute(
            "SELECT id, name, created_at, updated_at FROM projects ORDER BY created_at DESC"
        ).fetchall()

    # Tasks
    def get_task(self, task_id: int):
        return self.db.execute(
            "SELECT id, project_id, phase_id FROM tasks WHERE id=?",
            (task_id,),
        ).fetchone()

    def set_task_phase(self, task_id: int, phase_id: int) -> None:
        self.db.execute(
            "UPDATE tasks SET phase_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (phase_id, task_id),
        )
        self.db.commit()

    # Subtasks
    def get_subtask(self, subtask_id: int):
        return self.db.execute(
            "SELECT id, task_id, phase_id FROM subtasks WHERE id=?",
            (subtask_id,),
        ).fetchone()

    def set_subtask_phase(self, subtask_id: int, phase_id: int) -> None:
        self.db.execute(
            "UPDATE subtasks SET phase_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (phase_id, subtask_id),
        )
        self.db.commit()

