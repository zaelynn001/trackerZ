# src/repositories/sqlite_phase_repository.py
# Revision: M03 close-out (schema-adaptive updates history)
# Purpose: Concrete SQLite repository used by PhaseService to read/set phases
#          and to append history rows for tasks and subtasks.
#
# This version ADAPTS to your actual schema by inspecting table columns at runtime.
# It supports common variations:
#   - timestamp column: one of ["changed_at_utc","changed_at","created_at_utc","created_at","ts_utc","ts"]
#   - old/new phase columns: ["old_phase_id" | "from_phase_id"], ["new_phase_id" | "to_phase_id"]
#   - optional "note" column
#
# Assumed base tables exist:
#   tasks(id, phase_id, updated_at_utc, ...)
#   subtasks(id, task_id, phase_id, updated_at_utc, ...)
#
# History tables (any of these column variants are OK):
#   task_updates(task_id, <ts?>, <old_phase?>, <new_phase?>, <note?>)
#   subtask_updates(subtask_id, <ts?>, <old_phase?>, <new_phase?>, <note?>)
#
# Manager-based restrictions are intentionally NOT implemented.

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Dict, List

from datetime import datetime, timezone

from src.models.db import get_connection


def _utcnow_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class PhaseChangeResult:
    ok: bool
    reason: Optional[str] = None  # "invalid_transition" | "no_change" | "not_found" | sqlite error message
    old_phase_id: Optional[int] = None
    new_phase_id: Optional[int] = None


class SQLitePhaseRepository:
    """
    Minimal concrete repo for PhaseService with schema-adaptive history inserts.

    Initialize with:
        - db_path (Path or str), or
        - conn_factory callable returning sqlite3.Connection (preferred for tests)
    """

    # Candidate column names the repo can use (first found wins)
    _TS_CANDIDATES: List[str] = [
        "changed_at_utc", "changed_at", "created_at_utc", "created_at", "ts_utc", "ts"
    ]
    _OLD_CANDIDATES: List[str] = ["old_phase_id", "from_phase_id"]
    _NEW_CANDIDATES: List[str] = ["new_phase_id", "to_phase_id"]

    def __init__(self, db_path: Optional[Path | str] = None, conn_factory: Optional[callable] = None):
        if not db_path and not conn_factory:
            raise ValueError("Provide either db_path or conn_factory.")
        self._db_path = Path(db_path) if db_path else None
        self._conn_factory = conn_factory

    @contextmanager
    def _connect(self) -> Iterable[sqlite3.Connection]:
        if self._conn_factory:
            con = self._conn_factory()
        else:
            con = sqlite3.connect(str(self._db_path))
        try:
            con.row_factory = sqlite3.Row
            yield con
        finally:
            if not self._conn_factory:
                con.close()

    # ---------- helpers: schema adaptation ----------

    @staticmethod
    def _table_cols(con: sqlite3.Connection, table: str) -> Dict[str, sqlite3.Row]:
        rows = con.execute(f"PRAGMA table_info({table})").fetchall()
        # map name -> row
        return {str(r["name"]): r for r in rows}

    @classmethod
    def _pick_col(cls, cols: Dict[str, sqlite3.Row], candidates: List[str]) -> Optional[str]:
        for c in candidates:
            if c in cols:
                return c
        return None

    @staticmethod
    def _insert_dynamic(con: sqlite3.Connection, table: str, values: Dict[str, object]) -> None:
        if not values:
            return
        cols = ", ".join(values.keys())
        qmarks = ", ".join(["?"] * len(values))
        con.execute(f"INSERT INTO {table}({cols}) VALUES ({qmarks})", tuple(values.values()))
        


    # ---------- Tasks ----------

    def get_task_phase(self, task_id: int) -> Optional[int]:
        with self._connect() as con:
            cur = con.execute("SELECT phase_id FROM tasks WHERE id = ?", (task_id,))
            row = cur.fetchone()
            return None if row is None else int(row["phase_id"])

    def set_task_phase(self, task_id: int, phase_id: int) -> PhaseChangeResult:
        """
        Attempts to set the task phase. DB triggers are expected to enforce valid transitions.
        We detect outcomes by comparing pre/post values and catching errors.
        History insert adapts to actual schema.
        """
        with self._connect() as con:
            cur = con.execute("SELECT phase_id FROM tasks WHERE id = ?", (task_id,))
            row = cur.fetchone()
            if row is None:
                return PhaseChangeResult(ok=False, reason="not_found")
            old_pid = int(row["phase_id"])

            if old_pid == phase_id:
                return PhaseChangeResult(ok=False, reason="no_change", old_phase_id=old_pid, new_phase_id=phase_id)

            try:
                con.execute("BEGIN")
                con.execute("UPDATE OR ABORT tasks SET phase_id = ? WHERE id = ?", (phase_id, task_id))


                # If the update didn't affect a row, treat as invalid (trigger blocked)
                if con.total_changes == 0:
                    con.execute("ROLLBACK")
                    return PhaseChangeResult(ok=False, reason="invalid_transition", old_phase_id=old_pid, new_phase_id=phase_id)

                # Confirm new phase
                new_pid = int(con.execute("SELECT phase_id FROM tasks WHERE id = ?", (task_id,)).fetchone()["phase_id"])

                # Build a schema-adaptive history row
                cols = self._table_cols(con, "task_updates")
                data: Dict[str, object] = {"task_id": task_id}

                ts_col = self._pick_col(cols, self._TS_CANDIDATES)
                if ts_col:
                    data[ts_col] = _utcnow_str()

                old_col = self._pick_col(cols, self._OLD_CANDIDATES)
                new_col = self._pick_col(cols, self._NEW_CANDIDATES)

                # Only include old/new if such columns exist in your schema
                if old_col:
                    data[old_col] = old_pid
                if new_col:
                    data[new_col] = new_pid

                # Add note=None if supported
                if "note" in cols:
                    data["note"] = None

                self._insert_dynamic(con, "task_updates", data)

                con.execute("COMMIT")
                return PhaseChangeResult(ok=True, old_phase_id=old_pid, new_phase_id=new_pid)

            except sqlite3.IntegrityError as e:
                con.execute("ROLLBACK")
                # Surface the trigger message when present; fall back to 'invalid_transition'
                msg = (e.args[0] if e.args else "") or "invalid_transition"
                return PhaseChangeResult(ok=False, reason=msg, old_phase_id=old_pid, new_phase_id=phase_id)
            except Exception as e:  # pragma: no cover
                con.execute("ROLLBACK")
                return PhaseChangeResult(ok=False, reason=str(e), old_phase_id=old_pid, new_phase_id=phase_id)

    def add_task_update(self, task_id: int, old_phase_id: int, new_phase_id: int, note: Optional[str] = None) -> None:
        with self._connect() as con:
            cols = self._table_cols(con, "task_updates")
            data: Dict[str, object] = {"task_id": task_id}

            ts_col = self._pick_col(cols, self._TS_CANDIDATES)
            if ts_col:
                data[ts_col] = _utcnow_str()

            old_col = self._pick_col(cols, self._OLD_CANDIDATES)
            new_col = self._pick_col(cols, self._NEW_CANDIDATES)
            if old_col:
                data[old_col] = old_phase_id
            if new_col:
                data[new_col] = new_phase_id

            if "note" in cols:
                data["note"] = note

            self._insert_dynamic(con, "task_updates", data)

    # ---------- Subtasks ----------

    def get_subtask_phase(self, subtask_id: int) -> Optional[int]:
        with self._connect() as con:
            cur = con.execute("SELECT phase_id FROM subtasks WHERE id = ?", (subtask_id,))
            row = cur.fetchone()
            return None if row is None else int(row["phase_id"])

    def set_subtask_phase(self, subtask_id: int, phase_id: int) -> PhaseChangeResult:
        with self._connect() as con:
            cur = con.execute("SELECT phase_id FROM subtasks WHERE id = ?", (subtask_id,))
            row = cur.fetchone()
            if row is None:
                return PhaseChangeResult(ok=False, reason="not_found")
            old_pid = int(row["phase_id"])

            if old_pid == phase_id:
                return PhaseChangeResult(ok=False, reason="no_change", old_phase_id=old_pid, new_phase_id=phase_id)

            try:
                con.execute("BEGIN")
                con.execute("UPDATE subtasks SET phase_id = ? WHERE id = ?", (phase_id, subtask_id))
                if con.total_changes == 0:
                    con.execute("ROLLBACK")
                    return PhaseChangeResult(ok=False, reason="invalid_transition", old_phase_id=old_pid, new_phase_id=phase_id)

                new_pid = int(con.execute("SELECT phase_id FROM subtasks WHERE id = ?", (subtask_id,)).fetchone()["phase_id"])

                cols = self._table_cols(con, "subtask_updates")
                data: Dict[str, object] = {"subtask_id": subtask_id}

                ts_col = self._pick_col(cols, self._TS_CANDIDATES)
                if ts_col:
                    data[ts_col] = _utcnow_str()

                old_col = self._pick_col(cols, self._OLD_CANDIDATES)
                new_col = self._pick_col(cols, self._NEW_CANDIDATES)
                if old_col:
                    data[old_col] = old_pid
                if new_col:
                    data[new_col] = new_pid

                if "note" in cols:
                    data["note"] = None

                self._insert_dynamic(con, "subtask_updates", data)

                con.execute("COMMIT")
                return PhaseChangeResult(ok=True, old_phase_id=old_pid, new_phase_id=new_pid)

            except sqlite3.IntegrityError:
                con.execute("ROLLBACK")
                return PhaseChangeResult(ok=False, reason="invalid_transition", old_phase_id=old_pid, new_phase_id=phase_id)
            except Exception as e:  # pragma: no cover
                con.execute("ROLLBACK")
                return PhaseChangeResult(ok=False, reason=str(e), old_phase_id=old_pid, new_phase_id=phase_id)

    def add_subtask_update(self, subtask_id: int, old_phase_id: int, new_phase_id: int, note: Optional[str] = None) -> None:
        with self._connect() as con:
            cols = self._table_cols(con, "subtask_updates")
            data: Dict[str, object] = {"subtask_id": subtask_id}

            ts_col = self._pick_col(cols, self._TS_CANDIDATES)
            if ts_col:
                data[ts_col] = _utcnow_str()

            old_col = self._pick_col(cols, self._OLD_CANDIDATES)
            new_col = self._pick_col(cols, self._NEW_CANDIDATES)
            if old_col:
                data[old_col] = old_phase_id
            if new_col:
                data[new_col] = new_phase_id

            if "note" in cols:
                data["note"] = note

            self._insert_dynamic(con, "subtask_updates", data)

    # ---------- Optional helper for UI ----------

    def allowed_next_phases(self, current_phase_id: int) -> list[int]:
        """Reads phase_transitions to inform UI/ViewModel (optional for M03)."""
        with self._connect() as con:
            cur = con.execute(
                "SELECT to_phase_id FROM phase_transitions WHERE from_phase_id = ? ORDER BY to_phase_id ASC",
                (current_phase_id,),
            )
            return [int(r["to_phase_id"]) for r in cur.fetchall()]
    @staticmethod
    def _dict_factory(cursor, row):
        """Return SQLite rows as dicts."""
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    def list_all_phases(self) -> list[dict]:
        sql = "SELECT id, name FROM phases ORDER BY id ASC;"
        with self._connect() as con:
            con.row_factory = self._dict_factory
            cur = con.execute(sql)
            return cur.fetchall()

