# Rev 0.5.1
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal


class TaskTimelineViewModel(QObject):
    """
    Read/append updates for a task's timeline (task_updates).
    """

    changed = Signal()

    def __init__(self, task_updates_repo):
        super().__init__()
        self._updates = task_updates_repo
        self._task_id: Optional[int] = None

    def set_task(self, task_id: int) -> None:
        self._task_id = task_id

    def list_updates(self, task_id: Optional[int] = None, *, newest_first: bool = True) -> List[Dict[str, Any]]:
        tid = task_id if task_id is not None else self._task_id
        if tid is None:
            return []
        return self._updates.list_updates_for_task(tid, order_desc=newest_first)

    def add_note(self, note: str) -> int:
        if self._task_id is None:
            raise ValueError("TaskTimelineViewModel has no task selected.")
        new_id = self._updates.add_note(self._task_id, note=note)
        self.changed.emit()
        return new_id

    def add_update(
        self,
        *,
        note: Optional[str] = None,
        reason: Optional[str] = "update",
        old_phase_id: Optional[int] = None,
        new_phase_id: Optional[int] = None,
    ) -> int:
        if self._task_id is None:
            raise ValueError("TaskTimelineViewModel has no task selected.")
        new_id = self._updates.add_update(
            self._task_id,
            note=note,
            reason=reason,
            old_phase_id=old_phase_id,
            new_phase_id=new_phase_id,
        )
        self.changed.emit()
        return new_id
