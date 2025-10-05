# tests/test_phase_sqlite_integration.py
# Integration test for SQLitePhaseRepository against real schema + migrations

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Callable

import pytest

from src.repositories.sqlite_phase_repository import SQLitePhaseRepository

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SCHEMA_SQL = DATA_DIR / "schema.sql"
MIGRATIONS_DIR = DATA_DIR / "migrations"


def _apply_sql(con: sqlite3.Connection, sql_path: Path) -> None:
    with open(sql_path, "r", encoding="utf-8") as f:
        con.executescript(f.read())


def _apply_migrations(con: sqlite3.Connection) -> None:
    # Apply files that match your runner convention "000N_*.sql"
    files = sorted([p for p in MIGRATIONS_DIR.glob("*.sql") if p.name[:4].isdigit() and "_" in p.name])
    for p in files:
        _apply_sql(con, p)

def _has_column(con: sqlite3.Connection, table: str, col: str) -> bool:
    row = con.execute(f"PRAGMA table_info({table})").fetchall()
    return any(c["name"] == col for c in row)

def _first_existing_column(con: sqlite3.Connection, table: str, candidates: list[str]) -> str:
    for c in candidates:
        if _has_column(con, table, c):
            return c
    cols = [r["name"] for r in con.execute(f"PRAGMA table_info({table})")]
    raise AssertionError(f"No expected column found on {table}. Expected one of {candidates}, found {cols}")

def _required_cols_without_defaults(con: sqlite3.Connection, table: str) -> list[str]:
    """
    Return NOT NULL columns (excluding the INTEGER PRIMARY KEY) that also lack a default,
    so tests can provide seed values.
    """
    rows = con.execute(f"PRAGMA table_info({table})").fetchall()
    required = []
    for r in rows:
        # r: cid, name, type, notnull(0/1), dflt_value, pk(0/1)
        if r["pk"] == 1:
            continue
        if r["notnull"] == 1 and r["dflt_value"] is None:
            required.append(r["name"])
    return required

def _defaults_for_table(table: str) -> dict[str, str | int]:
    """
    Provide minimal, schema-agnostic defaults for required columns commonly present.
    Expand as needed; harmless extras are ignored when column not present.
    """
    base = {
        "created_at_utc": "1970-01-01T00:00:00Z",
        "updated_at_utc": "1970-01-01T00:00:00Z",
        "phase_id": 1,              # Open
        "priority_id": 2,           # Medium (if present)
        "project_id": 1,
        "task_id": 1,
        "assignee_id": 1,
        "verified_by": None,
        "note": None,
    }
    if table == "projects":
        base.update({
            "project_number": "P001",
            "code": "P001",         # in case schema uses an alt code field
        })
    if table == "tasks":
        base.update({
            "task_number": "T001",
        })
    if table == "subtasks":
        base.update({
            "subtask_number": "S001",
        })
    return base

def _insert_row(con: sqlite3.Connection, table: str, values: dict[str, object]) -> None:
    cols = ", ".join(values.keys())
    placeholders = ", ".join(["?"] * len(values))
    con.execute(f"INSERT INTO {table}({cols}) VALUES ({placeholders})", tuple(values.values()))
    
def _debug_dump(con: sqlite3.Connection) -> str:
    lines = []
    lines.append("== phases ==")
    for r in con.execute("SELECT id, name FROM phases ORDER BY id"):
        lines.append(f"{r['id']}: {r['name']}")
    lines.append("== phase_transitions ==")
    for r in con.execute("SELECT from_phase_id, to_phase_id FROM phase_transitions ORDER BY 1,2"):
        lines.append(f"{r['from_phase_id']} -> {r['to_phase_id']}")
    lines.append("== triggers (tasks/subtasks) ==")
    trig_rows = con.execute(
        "SELECT name, tbl_name, sql FROM sqlite_master "
        "WHERE type='trigger' AND tbl_name IN ('tasks','subtasks') ORDER BY tbl_name, name"
    ).fetchall()
    for r in trig_rows:
        lines.append(f"{r['tbl_name']}: {r['name']}")
    lines.append('== trigger SQL ==')
    for r in trig_rows:
        lines.append(f"-- {r['tbl_name']}: {r['name']}\n{r['sql']}\n")
    return "\n".join(lines)
# ---------- Phase discovery / transition ensure ----------

def _norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())

def _phase_id_by_name(con: sqlite3.Connection, wanted: str) -> int | None:
    want = _norm(wanted)
    rows = con.execute("SELECT id, name FROM phases").fetchall()
    for r in rows:
        if _norm(r["name"]) == want:
            return int(r["id"])
    return None

def _ensure_phase_transitions(con: sqlite3.Connection) -> dict[str, int]:
    """
    Return a dict of canonical phase name -> id and ensure the standard transitions exist.
    Works even if IDs differ from 1..5 or names have punctuation/spacing variants.
    """
    names = ["Open", "In Progress", "In Hiatus", "Resolved", "Closed"]
    ids: dict[str, int] = {}
    for n in names:
        pid = _phase_id_by_name(con, n)
        if pid is None:
            raise AssertionError(f"Phase '{n}' not found in phases table.")
        ids[n] = pid

    # transitions we expect
    transitions = [
        (ids["Open"],        ids["In Progress"]),
        (ids["In Progress"], ids["In Hiatus"]),
        (ids["In Progress"], ids["Resolved"]),
        (ids["In Hiatus"],   ids["In Progress"]),
        (ids["Resolved"],    ids["Closed"]),
    ]

    existing = {
        (int(r["from_phase_id"]), int(r["to_phase_id"]))
        for r in con.execute("SELECT from_phase_id, to_phase_id FROM phase_transitions").fetchall()
    }
    to_add = [t for t in transitions if t not in existing]
    if to_add:
        con.executemany(
            "INSERT INTO phase_transitions(from_phase_id, to_phase_id) VALUES (?, ?)",
            to_add,
        )
        con.commit()
    return ids
    
@pytest.fixture
def fresh_db(tmp_path: Path) -> Callable[[], sqlite3.Connection]:
    db_file = tmp_path / "tracker.db"
    con = sqlite3.connect(str(db_file))
    con.row_factory = sqlite3.Row
    try:
        # baseline + migrations
        assert SCHEMA_SQL.exists(), f"Missing schema.sql at {SCHEMA_SQL}"
        _apply_sql(con, SCHEMA_SQL)
        if MIGRATIONS_DIR.exists():
            _apply_migrations(con)
        # Make sure the canonical transitions exist and get canonical IDs
        ids = _ensure_phase_transitions(con)
        open_id       = ids["Open"]
        inprog_id     = ids["In Progress"]
        hiatus_id     = ids["In Hiatus"]
        resolved_id   = ids["Resolved"]
        closed_id     = ids["Closed"]
        # seed minimal data (phases & transitions should already be in schema/migrations)
        # Insert one project, one task in Open(1), one subtask in Open(1)
        project_label_col = _first_existing_column(con, "projects", ["title", "name"])
        task_label_col = _first_existing_column(con, "tasks", ["title", "name"])
        subtask_label_col = _first_existing_column(con, "subtasks", ["title", "name"])

        # Build seed rows with required NOT NULL cols
        proj_required = set(_required_cols_without_defaults(con, "projects"))
        task_required = set(_required_cols_without_defaults(con, "tasks"))
        sub_required  = set(_required_cols_without_defaults(con, "subtasks"))

        proj_values = {project_label_col: "Test Project"}
        proj_values.update({k: v for k, v in _defaults_for_table("projects").items() if k in proj_required})
        _insert_row(con, "projects", proj_values)

        task_values = {"project_id": 1, task_label_col: "Task A", "phase_id": 1}
        task_values.update({k: v for k, v in _defaults_for_table("tasks").items() if k in task_required and k not in task_values})
        _insert_row(con, "tasks", task_values)

        sub_values = {"task_id": 1, subtask_label_col: "Sub A", "phase_id": open_id}
        sub_values.update({k: v for k, v in _defaults_for_table("subtasks").items() if k in sub_required and k not in sub_values})
        _insert_row(con, "subtasks", sub_values)
        con.commit()
        yield lambda: sqlite3.connect(str(db_file))
    finally:
        con.close()


def test_task_phase_transitions_sqlite_repo(fresh_db):
    repo = SQLitePhaseRepository(conn_factory=fresh_db)

    # Start wherever the task is; follow whatever the DB allows.
    tid = 1
    cur = repo.get_task_phase(tid)
    assert cur is not None
    
    # DIAGNOSTIC: show what the DB and repo say is allowed
    with repo._connect() as con:
        diag = _debug_dump(con)
        allowed = repo.allowed_next_phases(cur)
        print("\n--- DEBUG (task) ---")
        print(diag)
        print(f"current phase: {cur}, allowed_next: {allowed}")
        print("--- END DEBUG ---\n")
    

    visited = {cur}
    # Try up to 5 transitions by always picking the first allowed next phase.
    for _ in range(5):
        allowed = repo.allowed_next_phases(cur)
        # If nothing allowed, stop here.
        if not allowed:
            break
        nxt = allowed[0]
        res = repo.set_task_phase(tid, nxt)
        assert res.ok, f"transition {cur}->{nxt} rejected: {res.reason}"
        cur = repo.get_task_phase(tid)
        visited.add(cur)

    # If we ever reached a phase that has no allowed next steps (terminal),
    # verify that trying to move away is rejected.
    allowed_from_cur = repo.allowed_next_phases(cur)
    if not allowed_from_cur:
        # pick any different phase id to attempt leaving terminal
        candidate = cur + 1 if cur != 1 else cur + 2
        res = repo.set_task_phase(tid, candidate)
        assert not res.ok and res.reason in {"invalid_transition", "no_change"}

    # History rows written
    with repo._connect() as con:
        cnt = con.execute("SELECT COUNT(*) AS c FROM task_updates WHERE task_id = 1").fetchone()["c"]
        assert cnt >= 3  # three successful changes


def test_subtask_phase_transitions_sqlite_repo(fresh_db):
    repo = SQLitePhaseRepository(conn_factory=fresh_db)

    sid = 1
    cur = repo.get_subtask_phase(sid)
    assert cur is not None
    
    # DIAGNOSTIC
    with repo._connect() as con:
        diag = _debug_dump(con)
        allowed = repo.allowed_next_phases(cur)
        print("\n--- DEBUG (subtask) ---")
        print(diag)
        print(f"current phase: {cur}, allowed_next: {allowed}")
        print("--- END DEBUG ---\n")


    # Walk allowed transitions as the DB defines them.
    for _ in range(5):
        allowed = repo.allowed_next_phases(cur)
        if not allowed:
            break
        nxt = allowed[0]
        res = repo.set_subtask_phase(sid, nxt)
        assert res.ok, f"transition {cur}->{nxt} rejected: {res.reason}"
        cur = repo.get_subtask_phase(sid)

    # Try a no-op: should be blocked as 'no_change' or equivalent.
    res = repo.set_subtask_phase(sid, cur)
    assert not res.ok and res.reason in {"no_change", "invalid_transition"}

    # History rows written
    with repo._connect() as con:
        cnt = con.execute("SELECT COUNT(*) AS c FROM subtask_updates WHERE subtask_id = 1").fetchone()["c"]
        assert cnt >= 3

