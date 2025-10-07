# trackerZ phase rule unit tests
# Rev 0.1.1

import sqlite3
import pytest
from pathlib import Path
from src.models.db import DB
from src.models.dao import DAO
from src.services.phase_service import PhaseService

@pytest.fixture()
def mem_dao():
    """In-memory DAO for phase validation tests."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.executescript(
        """
        CREATE TABLE phase_transitions(
            from_phase_id INTEGER NOT NULL,
            to_phase_id   INTEGER NOT NULL
        );
        CREATE TABLE tasks(
            id INTEGER PRIMARY KEY,
            project_id INTEGER,
            phase_id INTEGER,
            updated_at TEXT
        );
        CREATE TABLE subtasks(
            id INTEGER PRIMARY KEY,
            task_id INTEGER,
            phase_id INTEGER,
            updated_at TEXT
        );
        INSERT INTO phase_transitions VALUES (1,2),(2,3),(3,4),(4,5);
        INSERT INTO tasks(id, project_id, phase_id) VALUES (1, 1, 1);
        INSERT INTO subtasks(id, task_id, phase_id) VALUES (1, 1, 1);
        """
    )
    db = DB(Path(":memory:"))
    db.conn = conn
    return DAO(db)

def test_validate_allows_known_transition(mem_dao):
    svc = PhaseService(mem_dao)
    assert svc.validate(1, 2) is True

def test_change_phase_task_ok(mem_dao):
    mem_dao.db.execute("INSERT INTO tasks(id, project_id, phase_id) VALUES (2, 1, 1)")
    svc = PhaseService(mem_dao)
    svc.change_phase("task", 2, 2)
    row = mem_dao.db.execute("SELECT phase_id FROM tasks WHERE id=2").fetchone()
    assert row[0] == 2

def test_change_phase_blocked(mem_dao):
    svc = PhaseService(mem_dao)
    mem_dao.db.execute("INSERT INTO tasks(id, project_id, phase_id) VALUES (3, 1, 1)")
    with pytest.raises(PermissionError):
        svc.change_phase("task", 3, 3)

