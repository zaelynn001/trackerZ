# trackerZ phase service
# Rev 0.0.1

from __future__ import annotations
from dataclasses import dataclass
from ..models.types import EntityType
from ..models.dao import DAO

@dataclass
class PhaseService:
    """Implements allowed phase validation and updates for tasks/subtasks."""
    dao: DAO

    def validate(self, from_phase_id: int, to_phase_id: int) -> bool:
        """Return True if phase change is valid."""
        return (from_phase_id, to_phase_id) in self.dao.allowed_transitions()

    def change_phase(self, entity: EntityType, entity_id: int, to_phase_id: int) -> None:
        """Perform validated phase change for entity."""
        if entity == "task":
            rec = self.dao.get_task(entity_id)
            if not rec:
                raise ValueError("task not found")
            if not self.validate(int(rec["phase_id"]), to_phase_id):
                raise PermissionError("invalid phase change")
            self.dao.set_task_phase(entity_id, to_phase_id)
            return

        if entity == "subtask":
            rec = self.dao.get_subtask(entity_id)
            if not rec:
                raise ValueError("subtask not found")
            if not self.validate(int(rec["phase_id"]), to_phase_id):
                raise PermissionError("invalid phase change")
            self.dao.set_subtask_phase(entity_id, to_phase_id)
            return

        raise ValueError("unsupported entity type")

