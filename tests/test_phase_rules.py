# tests/test_phase_rules.py
import os
import sqlite3
import tempfile
from pathlib import Path
import subprocess

import pytest

# Point imports at your package
from src.models.db import set_db_path, DB_PATH
from src.models import dao

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SQL = PROJECT_ROOT / "data" / "schema.sql"

@pytest.fixture()
def temp_db():
    """Create a temp DB from schema.sql and yield its path, then clean up."""
    if not SCHEMA_SQL.exists():
        pytest.skip("schema.sql not found; run from project root with data/schema.sql present")

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test_tracker.db"
        # Apply schema.sql to temp DB
        cmd = f'sqlite3 "{db_path}" < "{SCHEMA_SQL}"'
        # Use shell=True only for the redirection; this is test-local
        subprocess.check_call(cmd, shell=True)
        # Seed a minimal project/task/subtask (similar to seed.sql but inline here)
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.executescript("""
                INSERT INTO projects (project_number, title, description, phase_id, priority, created_at_utc, updated_at_utc)
                VALUES ('P9999','Test Project','Testing phases',1,'Medium',strftime('%Y-%m-%dT%H:%M:%SZ','now'),strftime('%Y-%m-%dT%H:%M:%SZ','now'));
                INSERT INTO tasks (task_number, project_id, title, description, phase_id, priority, created_at_utc, updated_at_utc)
                SELECT 'T999999', id, 'Test Task','desc',1,'Low',strftime('%Y-%m-%dT%H:%M:%SZ','now'),strftime('%Y-%m-%dT%H:%M:%SZ','now') FROM projects WHERE project_number='P9999';
                INSERT INTO subtasks (subtask_number, task_id, title, description, phase_id, priority, created_at_utc, updated_at_utc)
                SELECT 'S999999', t.id, 'Test Subtask','desc',1,'Low',strftime('%Y-%m-%dT%H:%M:%SZ','now'),strftime('%Y-%m-%dT%H:%M:%SZ','now')
                FROM tasks t WHERE t.task_number='T999999';
            """)
            conn.commit()

        # Point the app at the temp DB
        set_db_path(str(db_path))
        yield str(db_path)

        # Restore env for any subsequent runs (not strictly necessary in isolated test)
        set_db_path(os.environ.get("TRACKERZ_DB", str(db_path)))

def _get_ids():
    rows = dao.list_projects_flat()
    assert rows, "No projects found"
    pr_id = rows[0]["id"]
    tasks = dao.list_tasks_for_project(pr_id)
    assert tasks, "No tasks found"
    t_id = tasks[0]["id"]
    subs = dao.list_subtasks_for_project(pr_id)
    assert subs, "No subtasks found"
    s_id = subs[0]["id"]
    return pr_id, t_id, s_id

def test_phase_transitions_allow_open_to_in_progress(temp_db):
    pr_id, t_id, s_id = _get_ids()
    in_progress = dao.get_phase_id_by_name("In Progress")
    assert in_progress is not None
    old, new = dao.change_task_phase(t_id, actor="tester", new_phase_id=in_progress, note="moving forward")
    assert old == 1 and new == in_progress

def test_phase_transitions_block_illegal_backwards(temp_db):
    pr_id, t_id, s_id = _get_ids()
    # Move task to In Progress first (allowed)
    in_progress = dao.get_phase_id_by_name("In Progress")
    dao.change_task_phase(t_id, actor="tester", new_phase_id=in_progress)
    # Try to move back to Open (not defined in default rules)
    with pytest.raises(ValueError):
        dao.change_task_phase(t_id, actor="tester", new_phase_id=1)

def test_subtask_phase_change_and_logging(temp_db):
    pr_id, t_id, s_id = _get_ids()
    resolved = dao.get_phase_id_by_name("Resolved")
    in_progress = dao.get_phase_id_by_name("In Progress")
    # First, subtask must go Open -> In Progress (allowed)
    dao.change_subtask_phase(s_id, actor="tester", new_phase_id=in_progress, note="start work")
    # Then In Progress -> Resolved (allowed)
    dao.change_subtask_phase(s_id, actor="tester", new_phase_id=resolved, note="done")
    # Verify latest phase is Resolved
    subs = dao.list_subtasks_for_project(pr_id)
    target = [x for x in subs if x["id"] == s_id][0]
    assert target["phase"] == "Resolved"

