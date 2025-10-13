# Rev 0.5.1

from __future__ import annotations
import sqlite3
import pytest


from src.services.phase_service import PhaseService




def seed_project(conn) -> int:
    cur = conn.execute("INSERT INTO projects(name) VALUES(?)", ("Demo",))
    return int(cur.lastrowid)




def seed_task(conn, project_id: int, phase_id: int = 1) -> int:
    cur = conn.execute(
        "INSERT INTO tasks(project_id, name, phase_id) VALUES(?,?,?)",
        (project_id, "T", phase_id),
    )
    return int(cur.lastrowid)




def seed_subtask(conn, task_id: int, phase_id: int = 1) -> int:
    cur = conn.execute(
        "INSERT INTO subtasks(task_id, name, phase_id) VALUES(?,?,?)",
        (task_id, "S", phase_id),
    )
    return int(cur.lastrowid)

# --- M3: phase rules ---------------------------------------------------------

def test_phases_seeded(db_conn):
    rows = db_conn.execute("SELECT id, name FROM phases ORDER BY id").fetchall()
    assert rows == [
        (1, "Open"), (2, "In Progress"), (3, "In Hiatus"), (4, "Resolved"), (5, "Closed")
    ]

def test_phase_service_allowed_and_disallowed(db_conn):
    svc = PhaseService(db_conn)
    assert svc.is_allowed(1, 2) is True # Open -> In Progress
    assert svc.is_allowed(2, 3) is True # In Progress -> In Hiatus
    assert svc.is_allowed(2, 4) is True # In Progress -> Resolved
    assert svc.is_allowed(3, 2) is True # In Hiatus -> In Progress
    assert svc.is_allowed(4, 5) is True # Resolved -> Closed
    assert svc.is_allowed(1, 5) is True # Open -> Closed


    # Some disallowed examples
    assert svc.is_allowed(2, 1) is False
    assert svc.is_allowed(5, 1) is False




def test_task_phase_change_allowed_and_touches_timestamp(db_conn):
    pid = seed_project(db_conn)
    tid = seed_task(db_conn, pid, phase_id=1)


    ts0 = db_conn.execute("SELECT updated_at_utc FROM tasks WHERE id=?", (tid,)).fetchone()[0]
    assert ts0 is None


    # Allowed update: 1 -> 2
    db_conn.execute("UPDATE tasks SET phase_id=? WHERE id=?", (2, tid))
    phase, ts1 = db_conn.execute(
        "SELECT phase_id, updated_at_utc FROM tasks WHERE id=?", (tid,)
    ).fetchone()
    assert phase == 2
    assert ts1 is not None




def test_task_phase_change_disallowed_raises(db_conn):
    pid = seed_project(db_conn)
    tid = seed_task(db_conn, pid, phase_id=2)


    with pytest.raises(sqlite3.IntegrityError):
        # 2 -> 1 not permitted by seed policy
        db_conn.execute("UPDATE tasks SET phase_id=? WHERE id=?", (1, tid))




def test_subtask_phase_change_allowed_and_disallowed(db_conn):
    pid = seed_project(db_conn)
    tid = seed_task(db_conn, pid, phase_id=1)
    sid = seed_subtask(db_conn, tid, phase_id=1)


# Allowed: 1 -> 2
    db_conn.execute("UPDATE subtasks SET phase_id=? WHERE id=?", (2, sid))
    phase = db_conn.execute("SELECT phase_id FROM subtasks WHERE id=?", (sid,)).fetchone()[0]
    assert phase == 2


    # Disallowed: 2 -> 1
    with pytest.raises(sqlite3.IntegrityError):
        db_conn.execute("UPDATE subtasks SET phase_id=? WHERE id=?", (1, sid))

# --- Reason autofill semantics ----------------------------------------------


def test_reason_autofill_project_updates(db_conn):
    pid = seed_project(db_conn)


# phase_change
    db_conn.execute(
        "INSERT INTO project_updates(project_id, old_phase_id, new_phase_id, note, reason) VALUES(?,?,?,?,?)",
        (pid, 1, 2, None, None),
    )
    r = db_conn.execute("SELECT reason FROM project_updates ORDER BY id DESC LIMIT 1").fetchone()[0]
    assert r == "phase_change"


# note
    db_conn.execute(
        "INSERT INTO project_updates(project_id, old_phase_id, new_phase_id, note, reason) VALUES(?,?,?,?,?)",
        (pid, None, None, "hello", None),
    )
    r = db_conn.execute("SELECT reason FROM project_updates ORDER BY id DESC LIMIT 1").fetchone()[0]
    assert r == "note"


    # update fallback
    db_conn.execute(
        "INSERT INTO project_updates(project_id, old_phase_id, new_phase_id, note, reason) VALUES(?,?,?,?,?)",
        (pid, None, None, None, None),
    )
    r = db_conn.execute("SELECT reason FROM project_updates ORDER BY id DESC LIMIT 1").fetchone()[0]
    assert r == "update"




def test_reason_autofill_task_and_subtask_updates(db_conn):
    pid = seed_project(db_conn)
    tid = seed_task(db_conn, pid)
    sid = seed_subtask(db_conn, tid)


    # task: phase_change
    db_conn.execute(
        "INSERT INTO task_updates(task_id, old_phase_id, new_phase_id, note, reason) VALUES(?,?,?,?,?)",
        (tid, 1, 2, None, None),
    )
    r = db_conn.execute("SELECT reason FROM task_updates ORDER BY id DESC LIMIT 1").fetchone()[0]
    assert r == "phase_change"


    # subtask: note
    db_conn.execute(
        "INSERT INTO subtask_updates(subtask_id, old_phase_id, new_phase_id, note, reason) VALUES(?,?,?,?,?)",
        (sid, None, None, "memo", None),
    )
    r = db_conn.execute("SELECT reason FROM subtask_updates ORDER BY id DESC LIMIT 1").fetchone()[0]
    assert r == "note"


    # task: update fallback
    db_conn.execute(
        "INSERT INTO task_updates(task_id, old_phase_id, new_phase_id, note, reason) VALUES(?,?,?,?,?)",
        (tid, None, None, None, None),
    )
    r = db_conn.execute("SELECT reason FROM task_updates ORDER BY id DESC LIMIT 1").fetchone()[0]
    assert r == "update"
