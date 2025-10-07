# src/repositories/sqlite_subtask_repository.py
# Rev 0.1.1
from __future__ import annotations
import sqlite3, datetime as _dt
from typing import List, Tuple, Optional, Dict, Iterable
from datetime import datetime, timezone

PREF_ST_TITLE  = ("title", "name", "summary", "label")
PREF_ST_PHASE  = ("phase_id", "phase")
PREF_ST_UPDATED= ("updated_at_utc_utc_utc", "updated_at_utc_utc", "modified_at", "updated_ts")
PREF_UPD_ST_ID = ("subtask_id",)
PREF_UPD_TS    = ("created_at_utc", "created_at", "updated_at_utc_utc_utc", "updated_at_utc_utc", "timestamp", "ts")

def _to_iso(ts)->str:
    if ts is None: return ""
    if isinstance(ts,(int,float)): return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    s=str(ts)
    if "T" in s: return s
    for fmt in ("%Y-%m-%d %H:%M:%S","%Y-%m-%d"):
        try: return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).isoformat()
        except Exception: pass
    return s

def _cols(c: sqlite3.Connection, table: str) -> Dict[str,bool]:
    cur=c.cursor(); cur.execute(f"PRAGMA table_info({table});")
    return {str(r[1]):True for r in cur.fetchall()}

def _first(prefs: Iterable[str], present: Dict[str,bool]) -> Optional[str]:
    for k in prefs:
        if present.get(k): return k
    return None

class SQLiteSubtaskRepository:
    """
    count_subtasks_total(task_id:int) -> int
    list_subtasks_filtered(task_id:int, phase_id:int|None) -> [(id, title, phase_name, updated_iso)]
    """
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn  # private handle to the database
        self._st_cols=_cols(conn,"subtasks")
        self._ph_cols=_cols(conn,"phases") if self._table_exists("phases") else {}
        self._upd_cols=_cols(conn,"subtask_updates") if self._table_exists("subtask_updates") else {}

        self._st_phase_col=_first(PREF_ST_PHASE,self._st_cols) or "phase_id"
        self._st_updated_col=_first(PREF_ST_UPDATED,self._st_cols)
        self._has_phase_name=bool(self._ph_cols.get("name"))
        self._has_updates=bool(self._upd_cols)

        titles=[c for c in PREF_ST_TITLE if self._st_cols.get(c)]
        self._title_expr= f"COALESCE({', '.join('s.'+c for c in titles)}, '')" if titles else "''"

        if self._has_updates:
            self._upd_st_id_col=_first(PREF_UPD_ST_ID,self._upd_cols) or "subtask_id"
            self._upd_ts_col=_first(PREF_UPD_TS,self._upd_cols) or "created_at"
        else:
            self._upd_st_id_col=self._upd_ts_col=None

    def _table_exists(self,name:str)->bool:
        cur=self._conn.cursor()
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1;",(name,))
        return cur.fetchone() is not None

    def count_subtasks_total(self, task_id:int)->int:
        cur=self._conn.cursor()
        cur.execute("SELECT COUNT(1) FROM subtasks WHERE task_id = ?",(task_id,))
        r=cur.fetchone()
        return int(r[0]) if r and r[0] is not None else 0

    def list_subtasks_for_project(self, project_id: int, phase_id: int | None = None):
        sql = """
        SELECT s.id, s.name, p.name, s.updated_at_utc
        FROM subtasks s
        JOIN tasks t ON t.id = s.task_id
        JOIN phases p ON p.id = s.phase_id
        WHERE t.project_id = ?
        """
        params = [project_id]
        if phase_id is not None:
            sql += " AND s.phase_id = ?"; params.append(phase_id)
        sql += " ORDER BY s.updated_at_utc DESC NULLS LAST, s.id DESC"
        cur = self._conn.execute(sql, params)
        return [(r[0], r[1], r[2], r[3]) for r in cur.fetchall()]
        
    def list_subtasks_for_task(self, task_id: int, phase_id: int | None = None):
        sql = """
        SELECT s.id, s.name, p.name, s.updated_at_utc
        FROM subtasks s
        JOIN phases p ON p.id = s.phase_id
        WHERE s.task_id = ?
        """
        params = [task_id]
        if phase_id is not None:
            sql += " AND s.phase_id = ?"; params.append(phase_id)
        sql += " ORDER BY s.updated_at_utc DESC NULLS LAST, s.id DESC"
        cur = self._conn.execute(sql, params)
        return [(r[0], r[1], r[2], r[3]) for r in cur.fetchall()]

    def list_subtasks_filtered(self, project_id: int, phase_id: int | None):
        sql = """
        SELECT t.id, t.name, p.name AS phase_name, t.updated_at_utc_utc
        FROM subtasks t
        JOIN phases p ON p.id = t.phase_id
        WHERE t.project_id = ?
        """
        params = [project_id]
        if phase_id is not None:
            sql += " AND t.phase_id = ?"
            params.append(phase_id)
        sql += " ORDER BY t.updated_at_utc_utc DESC NULLS LAST, t.id DESC"
        cur = self._conn.execute(sql, params)
        return [(r[0], r[1], r[2], r[3]) for r in cur.fetchall()]
        
    def insert_subtask(self, task_id: int, name: str, phase_id: int, note: str | None) -> int:
        now = _dt.datetime.utcnow().isoformat(timespec="seconds")
        cur = self._conn.execute(
            "INSERT INTO subtasks (task_id, name, phase_id, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (task_id, name, phase_id, note, now, now),
        )
        self._conn.commit()
        return int(cur.lastrowid)
