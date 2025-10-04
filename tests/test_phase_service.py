# tests/test_phase_service.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Tuple, List

import pytest

from src.services.phase_service import (
    PhaseService,
    PhaseChangeRequest,
    PhaseRepository,
    Phase,
)

# --- A tiny in-memory stub repo just for unit tests ------------------------

class _StubRepo(PhaseRepository):
    def __init__(self):
        # id -> phase
        self.tasks: Dict[int, Phase] = {}
        self.subtasks: Dict[int, Phase] = {}
        # history logs
        self.task_updates: List[Tuple[int, Phase, Phase, Optional[str], Optional[int], datetime]] = []
        self.subtask_updates: List[Tuple[int, Phase, Phase, Optional[str], Optional[int], datetime]] = []

    # TASKS
    def get_task_phase(self, task_id: int) -> Optional[Phase]:
        return self.tasks.get(task_id)

    def set_task_phase(self, task_id: int, new_phase: Phase, updated_at_utc: datetime) -> bool:
        if task_id not in self.tasks:
            return False
        self.tasks[task_id] = new_phase
        return True

    def add_task_update(self, task_id: int, phase_from: Phase, phase_to: Phase, note, actor_user_id, created_at_utc) -> bool:
        self.task_updates.append((task_id, phase_from, phase_to, note, actor_user_id, created_at_utc))
        return True

    # SUBTASKS
    def get_subtask_phase(self, subtask_id: int) -> Optional[Phase]:
        return self.subtasks.get(subtask_id)

    def set_subtask_phase(self, subtask_id: int, new_phase: Phase, updated_at_utc: datetime) -> bool:
        if subtask_id not in self.subtasks:
            return False
        self.subtasks[subtask_id] = new_phase
        return True

    def add_subtask_update(self, subtask_id: int, phase_from: Phase, phase_to: Phase, note, actor_user_id, created_at_utc) -> bool:
        self.subtask_updates.append((subtask_id, phase_from, phase_to, note, actor_user_id, created_at_utc))
        return True


# --- Fixtures --------------------------------------------------------------

@pytest.fixture()
def repo() -> _StubRepo:
    stub = _StubRepo()
    # seed some rows
    stub.tasks[1] = "Open"
    stub.tasks[2] = "In Progress"
    stub.tasks[3] = "Resolved"
    stub.tasks[4] = "Closed"

    stub.subtasks[10] = "In Hiatus"
    stub.subtasks[11] = "Closed"
    return stub


@pytest.fixture()
def service(repo: _StubRepo) -> PhaseService:
    return PhaseService(repo)


# --- Tests: allowed graph --------------------------------------------------

@pytest.mark.parametrize(
    "current,target,ok",
    [
        ("Open", "In Progress", True),
        ("In Progress", "In Hiatus", True),
        ("In Progress", "Resolved", True),
        ("In Hiatus", "In Progress", True),
        ("Resolved", "Closed", True),
        ("Closed", "Open", False),
        ("Closed", "In Progress", False),
        ("Open", "Resolved", False),
        ("Resolved", "In Progress", False),
    ],
)
def test_can_change_matrix(service: PhaseService, current, target, ok):
    allowed, _ = service.can_change(current, target)
    assert allowed is ok


def test_apply_valid_task_transition(service: PhaseService, repo: _StubRepo):
    req = PhaseChangeRequest(
        entity_kind="task",
        entity_id=1,
        current_phase="Open",      # UI-provided; service will look up actual current anyway
        target_phase="In Progress",
        user_id=99,
        note="Start work",
    )
    result = service.apply(req)
    assert result.ok
    assert result.code == "applied"
    assert repo.tasks[1] == "In Progress"
    assert len(repo.task_updates) == 1
    (task_id, p_from, p_to, note, actor_id, ts) = repo.task_updates[0]
    assert (task_id, p_from, p_to, note, actor_id) == (1, "Open", "In Progress", "Start work", 99)
    assert ts.tzinfo is timezone.utc


def test_apply_invalid_transition(service: PhaseService, repo: _StubRepo):
    # Open -> Resolved is not allowed
    req = PhaseChangeRequest(
        entity_kind="task",
        entity_id=1,
        current_phase="Open",
        target_phase="Resolved",
    )
    result = service.apply(req)
    assert not result.ok
    assert result.code == "invalid_transition"
    assert repo.tasks[1] == "Open"
    assert len(repo.task_updates) == 0


def test_apply_no_change(service: PhaseService, repo: _StubRepo):
    req = PhaseChangeRequest(
        entity_kind="task",
        entity_id=4,
        current_phase="Closed",
        target_phase="Closed",
    )
    result = service.apply(req)
    assert not result.ok
    assert result.code == "no_change"


def test_apply_entity_not_found(service: PhaseService):
    req = PhaseChangeRequest(
        entity_kind="task",
        entity_id=999,
        current_phase="Open",
        target_phase="In Progress",
    )
    result = service.apply(req)
    assert not result.ok
    assert result.code == "entity_not_found"


def test_apply_subtask_valid(service: PhaseService, repo: _StubRepo):
    # In Hiatus -> In Progress is allowed
    req = PhaseChangeRequest(
        entity_kind="subtask",
        entity_id=10,
        current_phase="In Hiatus",
        target_phase="In Progress",
        note="Resuming",
    )
    result = service.apply(req)
    assert result.ok
    assert repo.subtasks[10] == "In Progress"
    assert len(repo.subtask_updates) == 1
    (sid, p_from, p_to, note, actor_id, ts) = repo.subtask_updates[0]
    assert (sid, p_from, p_to, note, actor_id) == (10, "In Hiatus", "In Progress", "Resuming", None)
    assert ts.tzinfo is timezone.utc


def test_closed_is_terminal(service: PhaseService, repo: _StubRepo):
    # any move out of Closed is invalid
    req = PhaseChangeRequest(
        entity_kind="subtask",
        entity_id=11,
        current_phase="Closed",
        target_phase="In Progress",
    )
    result = service.apply(req)
    assert not result.ok
    assert result.code == "invalid_transition"
    assert repo.subtasks[11] == "Closed"
    assert len(repo.subtask_updates) == 0

