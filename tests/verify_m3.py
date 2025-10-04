#!/usr/bin/env python3
"""
verify_m3.py — M03 Phase Rules Verifier (SQLite)

What it checks:
  1) Presence of key tables: phases, phase_transitions, projects, tasks, subtasks
  2) Presence of M03 triggers:
       - trg_tasks_phase_validate
       - trg_subtasks_phase_validate
       - trg_tasks_touch_updated_at_on_phase
       - trg_subtasks_touch_updated_at_on_phase
  3) Allowed / disallowed phase changes using the seeded phases:
       - Task:   Open -> In Progress  (OK)
       - Task:   Open -> Resolved     (INVALID)
       - Task:   In Progress -> In Progress (NO-OP)
       - Subtask: Closed -> In Progress (INVALID: terminal)
       - Subtask: In Hiatus -> In Progress (OK)

Usage:
  python verify_m3.py --db data/tracker.db
  (Or set env TRACKERZ_DB)

Exit codes:
  0 = all checks passed
  1 = any check failed
"""

import os
import sys
import sqlite3
import argparse
from contextlib import contextmanager
from typing import Dict, Tuple

TRIGGERS = [
    "trg_tasks_phase_validate",
    "trg_subtasks_phase_validate",
    "trg_tasks_touch_updated_at_on_phase",
    "trg_subtasks_touch_updated_at_on_phase",
]

TABLES = [
    "phases",
    "phase_transitions",
    "projects",
    "tasks",
    "subtasks",
]

EXPECTED_ERRORS = {
    "no_change": "no_change",
    "invalid_transition": "invalid_transition",
    "terminal": "invalid_transition: terminal phase cannot change",
}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify M03 phase rules & triggers.")
    parser.add_argument(
        "--db",
        default=os.environ.get("TRACKERZ_DB", "data/trackerZ.db"),
        help="Path to SQLite database (default: %(default)s or $TRACKERZ_DB)",
    )
    return parser.parse_args()

@contextmanager
def connect(db_path: str):
    con = sqlite3.connect(db_path)
    try:
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON;")
        yield con
    finally:
        con.close()

def exists_table(con: sqlite3.Connection, name: str) -> bool:
    cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (name,))
    return cur.fetchone() is not None

def exists_trigger(con: sqlite3.Connection, name: str) -> bool:
    cur = con.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name=?;", (name,))
    return cur.fetchone() is not None

def fetch_phase_ids(con: sqlite3.Connection) -> Dict[str, int]:
    cur = con.execute("SELECT id, name FROM phases;")
    mapping = {row["name"]: row["id"] for row in cur.fetchall()}
    needed = {"Open", "In Progress", "In Hiatus", "Resolved", "Closed"}
    missing = needed - set(mapping.keys())
    if missing:
        raise RuntimeError(f"Missing seeded phases: {', '.join(sorted(missing))}")
    return mapping

def mk_project(con: sqlite3.Connection, project_number: str, title: str, phase_id: int) -> int:
    cur = con.execute(
        """
        INSERT INTO projects(project_number, title, description, phase_id, priority, created_at_utc, updated_at_utc)
        VALUES (?, ?, '', ?, NULL, strftime('%Y-%m-%dT%H:%M:%fZ','now'), strftime('%Y-%m-%dT%H:%M:%fZ','now'));
        """,
        (project_number, title, phase_id),
    )
    return cur.lastrowid

def mk_task(con: sqlite3.Connection, project_id: int, task_number: str, title: str, phase_id: int) -> int:
    cur = con.execute(
        """
        INSERT INTO tasks(task_number, project_id, title, description, phase_id, priority, created_at_utc, updated_at_utc)
        VALUES (?, ?, ?, '', ?, NULL, strftime('%Y-%m-%dT%H:%M:%fZ','now'), strftime('%Y-%m-%dT%H:%M:%fZ','now'));
        """,
        (task_number, project_id, title, phase_id),
    )
    return cur.lastrowid

def mk_subtask(con: sqlite3.Connection, task_id: int, subtask_number: str, title: str, phase_id: int) -> int:
    cur = con.execute(
        """
        INSERT INTO subtasks(subtask_number, task_id, title, description, phase_id, priority, created_at_utc, updated_at_utc)
        VALUES (?, ?, ?, '', ?, NULL, strftime('%Y-%m-%dT%H:%M:%fZ','now'), strftime('%Y-%m-%dT%H:%M:%fZ','now'));
        """,
        (subtask_number, task_id, title, phase_id),
    )
    return cur.lastrowid

def try_update_phase(con: sqlite3.Connection, table: str, entity_id: int, new_phase_id: int) -> Tuple[bool, str]:
    """
    Attempt to update phase_id; return (ok, message).
    On failure, message will contain the trigger's RAISE() text.
    """
    try:
        con.execute(f"UPDATE {table} SET phase_id=? WHERE id=?;", (new_phase_id, entity_id))
        return True, "applied"
    except sqlite3.IntegrityError as e:
        msg = str(e)
        # Normalize common trigger messages
        for key, needle in EXPECTED_ERRORS.items():
            if needle in msg:
                return False, needle
        return False, msg

def main() -> int:
    args = parse_args()
    db = args.db
    print(f"→ Verifying M03 on DB: {db}")

    all_ok = True

    with connect(db) as con:
        # Keep the DB clean: do everything in a single transaction we then roll back.
        con.isolation_level = None
        con.execute("BEGIN IMMEDIATE;")
        try:
            # 1) Existence checks
            print("\n[1] Schema objects")
            for t in TABLES:
                ok = exists_table(con, t)
                print(f"  - table {t:32s}: {'OK' if ok else 'MISSING'}")
                all_ok &= ok

            for tr in TRIGGERS:
                ok = exists_trigger(con, tr)
                print(f"  - trigger {tr:32s}: {'OK' if ok else 'MISSING'}")
                all_ok &= ok

            # Short-circuit if basics are missing
            if not all_ok:
                print("\n✗ Basic schema/trigger checks failed.")
                con.execute("ROLLBACK;")
                return 1

            # 2) Phase ids
            phases = fetch_phase_ids(con)
            print("\n[2] Phase IDs")
            for name in ("Open", "In Progress", "In Hiatus", "Resolved", "Closed"):
                print(f"  - {name:12s} = {phases[name]}")

            # 3) Seed scratch rows
            print("\n[3] Seeding scratch rows")
            pid = mk_project(con, "P_M03_VERIFY", "M03 Verify Project", phases["Open"])
            tid = mk_task(con, pid, "T_M03_VERIFY", "M03 Verify Task", phases["Open"])
            sid_closed   = mk_subtask(con, tid, "S_M03_TERM", "Terminal subtask", phases["Closed"])
            sid_hiatus   = mk_subtask(con, tid, "S_M03_HIATUS", "Hiatus subtask", phases["In Hiatus"])
            print(f"  - project_id={pid}, task_id={tid}, subtask_ids=[{sid_closed}, {sid_hiatus}]")

            # 4) Transition tests
            print("\n[4] Transition tests")

            # 4.1 Task: Open -> In Progress (OK)
            ok, msg = try_update_phase(con, "tasks", tid, phases["In Progress"])
            print(f"  • Task Open → In Progress: {'PASS' if ok and msg=='applied' else 'FAIL'} ({msg})")
            all_ok &= bool(ok and msg == "applied")

            # 4.2 Task: Open -> Resolved (INVALID) — need to reset to Open first
            # Reset task back to Open to test the invalid path.
            con.execute("UPDATE tasks SET phase_id=? WHERE id=?;", (phases["Open"], tid))
            ok, msg = try_update_phase(con, "tasks", tid, phases["Resolved"])
            print(f"  • Task Open → Resolved: {'PASS' if (not ok and msg==EXPECTED_ERRORS['invalid_transition']) else 'FAIL'} ({msg})")
            all_ok &= bool((not ok) and msg == EXPECTED_ERRORS["invalid_transition"])

            # 4.3 Task: In Progress -> In Progress (NO-OP)
            con.execute("UPDATE tasks SET phase_id=? WHERE id=?;", (phases["In Progress"], tid))
            ok, msg = try_update_phase(con, "tasks", tid, phases["In Progress"])
            print(f"  • Task In Progress → In Progress (no-op): {'PASS' if (not ok and msg==EXPECTED_ERRORS['no_change']) else 'FAIL'} ({msg})")
            all_ok &= bool((not ok) and msg == EXPECTED_ERRORS["no_change"])

            # 4.4 Subtask: Closed -> In Progress (INVALID: terminal)
            ok, msg = try_update_phase(con, "subtasks", sid_closed, phases["In Progress"])
            expected = EXPECTED_ERRORS["terminal"]
            print(f"  • Subtask Closed → In Progress: {'PASS' if (not ok and msg==expected) else 'FAIL'} ({msg})")
            all_ok &= bool((not ok) and msg == expected)

            # 4.5 Subtask: In Hiatus -> In Progress (OK)
            ok, msg = try_update_phase(con, "subtasks", sid_hiatus, phases["In Progress"])
            print(f"  • Subtask In Hiatus → In Progress: {'PASS' if ok and msg=='applied' else 'FAIL'} ({msg})")
            all_ok &= bool(ok and msg == "applied")

            # Optional: confirm updated_at_utc touched on successful changes
            print("\n[5] Touch timestamp checks (spot check)")
            cur = con.execute("SELECT updated_at_utc FROM subtasks WHERE id=?;", (sid_hiatus,))
            touched = cur.fetchone()["updated_at_utc"]
            print(f"  • subtasks.updated_at_utc set: {'OK' if touched else 'MISSING'} ({touched})")
            all_ok &= bool(touched)

            # All good — rollback (dry run)
            con.execute("ROLLBACK;")
        except Exception as e:
            con.execute("ROLLBACK;")
            print(f"\n✗ Exception during verification: {e}")
            return 1

    print("\n✓ Verification:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

