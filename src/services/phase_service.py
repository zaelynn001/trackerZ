# src/services/phase_service.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, Literal, Optional, Protocol, Tuple, Set

# Project-wide terminology:
# - "phase" instead of "status"
# - applies equally to tasks and subtasks

Phase = Literal["Open", "In Progress", "In Hiatus", "Resolved", "Closed"]
EntityKind = Literal["task", "subtask"]  # used to select repo + history table


@dataclass(frozen=True)
class PhaseChangeRequest:
    entity_kind: EntityKind          # "task" or "subtask"
    entity_id: int                   # task_id or subtask_id
    current_phase: Phase
    target_phase: Phase
    user_id: Optional[int] = None    # who performed the change (optional for now)
    note: Optional[str] = None       # free-form note to store in updates/history


@dataclass(frozen=True)
class PhaseChangeResult:
    ok: bool
    code: Literal[
        "applied",
        "no_change",
        "invalid_transition",
        "entity_not_found",
        "repo_error"
    ]
    message: str
    applied_at_utc: Optional[datetime] = None


class PhaseRepository(Protocol):
    """
    Narrow interface the service depends on.
    Your concrete repos can implement these against SQLite/Qt models.
    """

    # ---- TASKS ----
    def get_task_phase(self, task_id: int) -> Optional[Phase]: ...
    def set_task_phase(self, task_id: int, new_phase: Phase, updated_at_utc: datetime) -> bool: ...
    def add_task_update(
        self,
        task_id: int,
        phase_from: Phase,
        phase_to: Phase,
        note: Optional[str],
        actor_user_id: Optional[int],
        created_at_utc: datetime,
    ) -> bool: ...

    # ---- SUBTASKS ----
    def get_subtask_phase(self, subtask_id: int) -> Optional[Phase]: ...
    def set_subtask_phase(self, subtask_id: int, new_phase: Phase, updated_at_utc: datetime) -> bool: ...
    def add_subtask_update(
        self,
        subtask_id: int,
        phase_from: Phase,
        phase_to: Phase,
        note: Optional[str],
        actor_user_id: Optional[int],
        created_at_utc: datetime,
    ) -> bool: ...


class PhaseService:
    """
    Centralized business rules for allowed phase changes.
    No role gating: any caller may request any allowed transition.
    """

    # Finite-state graph shared by tasks and subtasks
    _ALLOWED: Dict[Phase, Set[Phase]] = {
        "Open": {"In Progress"},
        "In Progress": {"In Hiatus", "Resolved"},
        "In Hiatus": {"In Progress"},
        "Resolved": {"Closed"},
        "Closed": set(),  # terminal
    }

    def __init__(self, repo: PhaseRepository):
        self._repo = repo

    # -- Public API ---------------------------------------------------------

    def can_change(self, current: Phase, target: Phase) -> Tuple[bool, str]:
        """Check if a transition is valid according to the FSM."""
        if current == target:
            return False, "Target phase equals current phase."
        allowed = self._ALLOWED.get(current, set())
        if target in allowed:
            return True, "Valid phase change."
        return False, f"Invalid phase change: {current} → {target}."

    def apply(self, req: PhaseChangeRequest) -> PhaseChangeResult:
        """
        Validate and (if valid) persist the phase change + write history.
        Returns a result suitable for UI messaging.
        """
        # Fetch current phase from the source of truth (DB) to avoid stale UI
        actual_current = self._get_current_phase(req.entity_kind, req.entity_id)
        if actual_current is None:
            return PhaseChangeResult(
                ok=False, code="entity_not_found",
                message=f"{req.entity_kind.capitalize()} #{req.entity_id} not found."
            )

        if req.target_phase == actual_current:
            return PhaseChangeResult(
                ok=False, code="no_change",
                message="Phase is already set to the requested value."
            )

        allowed, why = self.can_change(actual_current, req.target_phase)
        if not allowed:
            return PhaseChangeResult(ok=False, code="invalid_transition", message=why)

        now_utc = datetime.now(timezone.utc)

        # Persist phase to the correct table
        ok_set = self._set_phase(req.entity_kind, req.entity_id, req.target_phase, now_utc)
        if not ok_set:
            return PhaseChangeResult(ok=False, code="repo_error", message="Failed to update phase in repository.")

        # Log to the correct updates/history table
        ok_log = self._log_update(
            req.entity_kind,
            req.entity_id,
            actual_current,
            req.target_phase,
            req.note,
            req.user_id,
            now_utc,
        )
        if not ok_log:
            # Consider: you may choose to rollback the phase set if logging fails.
            # For now we return repo_error while the phase has changed.
            return PhaseChangeResult(ok=False, code="repo_error", message="Phase updated, but failed to write history.")

        return PhaseChangeResult(
            ok=True, code="applied", message="Phase updated.", applied_at_utc=now_utc
        )

    # -- Internals ----------------------------------------------------------

    def _get_current_phase(self, kind: EntityKind, entity_id: int) -> Optional[Phase]:
        if kind == "task":
            return self._repo.get_task_phase(entity_id)
        return self._repo.get_subtask_phase(entity_id)

    def _set_phase(self, kind: EntityKind, entity_id: int, target: Phase, ts_utc: datetime) -> bool:
        if kind == "task":
            return self._repo.set_task_phase(entity_id, target, ts_utc)
        return self._repo.set_subtask_phase(entity_id, target, ts_utc)

    def _log_update(
        self,
        kind: EntityKind,
        entity_id: int,
        phase_from: Phase,
        phase_to: Phase,
        note: Optional[str],
        actor_user_id: Optional[int],
        ts_utc: datetime,
    ) -> bool:
        if kind == "task":
            return self._repo.add_task_update(entity_id, phase_from, phase_to, note, actor_user_id, ts_utc)
        return self._repo.add_subtask_update(entity_id, phase_from, phase_to, note, actor_user_id, ts_utc)

