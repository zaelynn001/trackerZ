# Rev 0.1.1
# src/repositories/sqlite_task_repository.py
from __future__ import annotations
import sqlite3, datetime as _dt
from typing import List, Tuple, Optional, Dict, Iterable
from datetime import datetime, timezone

PREF_TASK_TITLES: tuple[str, ...] = ("title", "name", "summary", "label")
PREF_TASK_PHASE:  tuple[str, ...] = ("phase_id", "phase")
PREF_TASK_UPDATED: tuple[str, ...] = ("updated_at_utc_utc", "updated_at_utc", "modified_at", "updated_ts")
PREF_UPD_TASK_ID: tuple[str, ...] = ("task_id",)
PREF_UPD_TS: tuple[str, ...]      = ("created_at_utc", "created_at", "updated_at_utc_utc", "updated_at_utc", "timestamp", "ts")

def _to_iso_utc(ts) -> str:
    if ts is None:
        return ""
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    s = str(ts)
    if "T" in s:
        return s
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
    return s

def _cols(conn: sqlite3.Connection, table: str) -> Dict[str, bool]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table});")
    return {str(r[1]): True for r in cur.fetchall()}

def _first_present(prefs: Iterable[str], present: Dict[str, bool]) -> Optional[str]:
    for c in prefs:
        if present.get(c):
            return c
    return None

class SQLiteTaskRepository:
    """
    count_tasks_total(project_id:int) -> int
    list_tasks_filtered(project_id:int, phase_id:int|None) -> list[(id, title, phase_name, updated_iso)]
    """
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn  # private handle to the database
        self._tasks_cols = _cols(conn, "tasks")
        self._phases_cols = _cols(conn, "phases") if self._table_exists("phases") else {}
        self._updates_cols = _cols(conn, "task_updates") if self._table_exists("task_updates") else {}

        # Resolve columns present
        self._task_phase_col  = _first_present(PREF_TASK_PHASE, self._tasks_cols) or "phase_id"
        self._task_updated_col = _first_present(PREF_TASK_UPDATED, self._tasks_cols)
        self._has_phase_name = bool(self._phases_cols.get("name"))
        self._has_updates = bool(self._updates_cols)

        # Title expression built from actually present columns
        title_candidates = [c for c in PREF_TASK_TITLES if self._tasks_cols.get(c)]
        if title_candidates:
            coalesce_list = ", ".join(f"t.{c}" for c in title_candidates)
            self._title_expr = f"COALESCE({coalesce_list}, '')"
        else:
            self._title_expr = "''"  # last resort, schema has no recognizable title column

        if self._has_updates:
            self._upd_task_id_col = _first_present(PREF_UPD_TASK_ID, self._updates_cols) or "task_id"
            self._upd_ts_col      = _first_present(PREF_UPD_TS, self._updates_cols) or "created_at"
        else:
            self._upd_task_id_col = None
            self._upd_ts_col = None

    def _table_exists(self, name: str) -> bool:
        cur = self._conn.cursor()
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1;", (name,))
        return cur.fetchone() is not None

    def count_tasks_total(self, project_id: int) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(1) FROM tasks WHERE project_id = ?", (project_id,))
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    def list_tasks_filtered(self, project_id: int, phase_id: int | None):
        sql = """
        SELECT t.id, t.name, p.name AS phase_name, t.updated_at_utc
        FROM tasks t
        JOIN phases p ON p.id = t.phase_id
        WHERE t.project_id = ?
        """
        params = [project_id]
        if phase_id is not None:
            sql += " AND t.phase_id = ?"
            params.append(phase_id)
        sql += " ORDER BY t.updated_at_utc DESC NULLS LAST, t.id DESC"
        cur = self._conn.execute(sql, params)
        return [(r[0], r[1], r[2], r[3]) for r in cur.fetchall()]
        
    def insert_task(self, project_id: int, name: str, phase_id: int, note: str | None) -> int:
        now = _dt.datetime.utcnow().isoformat(timespec="seconds")
        cur = self._conn.execute(
            "INSERT INTO tasks (project_id, name, phase_id, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, name, phase_id, note, now, now),
        )
        self._conn.commit()
        return int(cur.lastrowid)
