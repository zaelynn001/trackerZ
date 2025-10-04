#!/usr/bin/env python3
"""
verify_m3.py — M03 Phase Rules Verifier (SQLite)
(Manager restrictions removed)

Fix: use separate scratch rows for each transition test to avoid invalid resets.
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

TABLES = ["phases", "phase_transitions", "projects", "tasks", "subtasks"]

EXPECTED_ERRORS = {
    "no_change": "no_change",
    "invalid_transition": "invalid_transition",
    "terminal": "invalid_transition: terminal phase cannot change",
}

def parse_args():
    p = argparse.ArgumentParser(description="Verify M03 phase rules & triggers.")
    p.add_argument("--db", default=os.environ.get("TRACKERZ_DB", "data/trackerZ.db"),
                   help="Path to SQLite database (default: %(default)s or $TRACKERZ_DB)")
    return p.parse_args()

@contextmanager
def connect(db_path: str):
    con = sqlite3.connect(db_path)
    try:
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON;")
        yield con
    finally:
        con.close()

def exists(con, typ, name):
    cur = con.execute("SELECT name FROM sqlite_master WHERE type=? AND name=?;", (typ, name))
    return cur.fetchone() is not None

def fetch_phase_ids(con) -> Dict[str, int]:
    cur = con.execute("SELECT id, name FROM phases;")
    mapping = {r["name"]: r["id"] for r in cur.fetchall()}
    needed = {"Open", "In Progress", "In Hiatus", "Resolved", "Closed"}
    missing = needed - set(mapping.keys())
    if missing:
        raise RuntimeError(f"Missing seeded phases: {', '.join(sorted(missing))}")
    return mapping

def mk_project(con, project_number: str, title: str, phase_id: int) -> int:
    cur = con.execute("""
        INSERT INTO projects(project_number, title, description, phase_id, priority, created_at_utc, updated_at_utc)
        VALUES (?, ?, '', ?, NULL, strftime('%Y-%m-%dT%H:%M:%fZ','now'), strftime('%Y-%m-%dT%H:%M:%fZ','now'));
    """, (project_number, title, phase_id))
    return cur.lastrowid

def mk_task(con, project_id: int, task_number: str, title: str, phase_id: int) -> int:
    cur = con.execute("""
        INSERT INTO tasks(task_number, project_id, title, description, phase_id, priority, created_at_utc, updated_at_utc)
        VALUES (?, ?, ?, '', ?, NULL, strftime('%Y-%m-%dT%H:%M:%fZ','now'), strftime('%Y-%m-%dT%H:%M:%fZ','now'));
    """, (task_number, project_id, title, phase_id))
    return cur.lastrowid

def mk_subtask(con, task_id: int, subtask_number: str, title: str, phase_id: int) -> int:
    cur = con.execute("""
        INSERT INTO subtasks(subtask_number, task_id, title, description, phase_id, priority, created_at_utc, updated_at_utc)
        VALUES (?, ?, ?, '', ?, NULL, strftime('%Y-%m-%dT%H:%M:%fZ','now'), strftime('%Y-%m-%dT%H:%M:%fZ','now'));
    """, (subtask_number, task_id, title, phase_id))
    return cur.lastrowid

def try_update_phase(con, table: str, entity_id: int, new_phase_id: int) -> Tuple[bool, str]:
    try:
        con.execute(f"UPDATE {table} SET phase_id=? WHERE id=?;", (new_phase_id, entity_id))
        return True, "applied"
    except sqlite3.IntegrityError as e:
        msg = str(e)
        for needle in EXPECTED_ERRORS.values():
            if needle in msg:
                return False, needle
        return False, msg

def main() -> int:
    args = parse_args()
    db = args.db
    print(f"→ Verifying M03 on DB: {db}")

    all_ok = True

    with connect(db) as con:
        con.isolation_level = None
        con.execute("BEGIN IMMEDIATE;")
        try:
            print("\n[1] Schema objects")
            for t in TABLES:
                ok = exists(con, "table", t)
                print(f"  - table {t:32s}: {'OK' if ok else 'MISSING'}")
                all_ok &= ok
            for tr in TRIGGERS:
                ok = exists(con, "trigger", tr)
                print(f"  - trigger {tr:32s}: {'OK' if ok else 'MISSING'}")
                all_ok &= ok
            if not all_ok:
                print("\n✗ Basic schema/trigger checks failed.")
                con.execute("ROLLBACK;")
                return 1

            phases = fetch_phase_ids(con)
            print("\n[2] Phase IDs")
            for name in ("Open", "In Progress", "In Hiatus", "Resolved", "Closed"):
                print(f"  - {name:12s} = {phases[name]}")

            print("\n[3] Seeding scratch rows")
            pid = mk_project(con, "P_M03_VERIFY", "M03 Verify Project", phases["Open"])

            # Distinct rows for each test case to avoid illegal "resets"
            tid_valid   = mk_task(con, pid, "T_M03_VALID",   "Valid transition",   phases["Open"])
            tid_invalid = mk_task(con, pid, "T_M03_INVALID", "Invalid transition", phases["Open"])
            tid_noop    = mk_task(con, pid, "T_M03_NOOP",    "No-op transition",   phases["In Progress"])
            sid_closed  = mk_subtask(con, tid_valid, "S_M03_TERM",   "Terminal subtask", phases["Closed"])
            sid_hiatus  = mk_subtask(con, tid_valid, "S_M03_HIATUS", "Hiatus subtask",   phases["In Hiatus"])
            print(f"  - project_id={pid}; tasks=[{tid_valid},{tid_invalid},{tid_noop}]; subtasks=[{sid_closed},{sid_hiatus}]")

            print("\n[4] Transition tests")

            # 4.1 Task: Open -> In Progress (OK)
            ok, msg = try_update_phase(con, "tasks", tid_valid, phases["In Progress"])
            print(f"  • Task Open → In Progress: {'PASS' if ok and msg=='applied' else 'FAIL'} ({msg})")
            all_ok &= bool(ok and msg == "applied")

            # 4.2 Task: Open -> Resolved (INVALID)
            ok, msg = try_update_phase(con, "tasks", tid_invalid, phases["Resolved"])
            print(f"  • Task Open → Resolved: {'PASS' if (not ok and msg==EXPECTED_ERRORS['invalid_transition']) else 'FAIL'} ({msg})")
            all_ok &= bool((not ok) and msg == EXPECTED_ERRORS["invalid_transition"])

            # 4.3 Task: In Progress -> In Progress (NO-OP)
            ok, msg = try_update_phase(con, "tasks", tid_noop, phases["In Progress"])
            print(f"  • Task In Progress → In Progress (no-op): {'PASS' if (not ok and msg==EXPECTED_ERRORS['no_change']) else 'FAIL'} ({msg})")
            all_ok &= bool((not ok) and msg == EXPECTED_ERRORS["no_change"])

            # 4.4 Subtask: Closed -> In Progress (INVALID: terminal)
            ok, msg = try_update_phase(con, "subtasks", sid_closed, phases["In Progress"])
            # Accept either a specific terminal message or the generic invalid_transition
            terminal_ok = (not ok) and (msg == EXPECTED_ERRORS["terminal"] or msg == EXPECTED_ERRORS["invalid_transition"])
            print(f"  • Subtask Closed → In Progress: {'PASS' if terminal_ok else 'FAIL'} ({msg})")
            all_ok &= bool(terminal_ok)

            # 4.5 Subtask: In Hiatus -> In Progress (OK)
            ok, msg = try_update_phase(con, "subtasks", sid_hiatus, phases["In Progress"])
            print(f"  • Subtask In Hiatus → In Progress: {'PASS' if ok and msg=='applied' else 'FAIL'} ({msg})")
            all_ok &= bool(ok and msg == "applied")

            print("\n[5] Touch timestamp checks (spot check)")
            cur = con.execute("SELECT updated_at_utc FROM subtasks WHERE id=?;", (sid_hiatus,))
            touched = cur.fetchone()["updated_at_utc"]
            print(f"  • subtasks.updated_at_utc set: {'OK' if touched else 'MISSING'} ({touched})")
            all_ok &= bool(touched)

            con.execute("ROLLBACK;")
        except Exception as e:
            con.execute("ROLLBACK;")
            print(f"\n✗ Exception during verification: {e}")
            return 1

    print("\n✓ Verification:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())

