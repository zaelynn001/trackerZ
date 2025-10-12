# Rev 0.4.1

from __future__ import annotations
import sqlite3
from typing import List, Dict, Any, Optional, Tuple

class SQLiteTaskRepository:
    """
    Minimal read API used by M4:
      - count_tasks_total(project_id)
      - list_tasks_filtered(project_id, phase_id)
    Works whether you pass a raw sqlite3.Connection or a Database wrapper
    that exposes .conn or .connect().
    """

    def __init__(self, db_or_conn):
        self._db = db_or_conn

    # ---------- Public API ----------

    def count_tasks_total(self, project_id: int) -> int:
        sql = "SELECT COUNT(*) FROM tasks WHERE project_id = ?;"
        con = self._conn()
        cur = con.execute(sql, (project_id,))
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    def list_tasks_filtered(self, project_id: int, phase_id: Optional[int]) -> List[Dict[str, Any]]:
        """
        Returns rows shaped like: {"id": int, "name": str, "phase_name": str}
        If your schema uses 'title' instead of 'name', we normalize.
        """
        params: List[Any] = [project_id]
        where = ["t.project_id = ?"]
        if phase_id is not None:
            where.append("t.phase_id = ?")
            params.append(phase_id)

        sql = f"""
            SELECT
                t.id                           AS id,
                t.name                         AS name,
                COALESCE(p.name, '')           AS phase_name
            FROM tasks t
            LEFT JOIN phases p ON p.id = t.phase_id
            WHERE {' AND '.join(where)}
            ORDER BY t.id DESC;
        """

        return self._fetch_all(sql, tuple(params))

    # Handy extras (not strictly required for M4, but useful)

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT
                t.id                           AS id,
                t.project_id                   AS project_id,
                t.name                         AS name,
                COALESCE(t.description, '')    AS description,
                t.phase_id                     AS phase_id
            FROM tasks t
            WHERE t.id = ?;
        """
        rows = self._fetch_all(sql, (task_id,))
        return rows[0] if rows else None

    # ---------- Internals ----------

    def _conn(self) -> sqlite3.Connection:
        if isinstance(self._db, sqlite3.Connection):
            return self._db
        if hasattr(self._db, "conn") and isinstance(self._db.conn, sqlite3.Connection):
            return self._db.conn
        if hasattr(self._db, "connect"):
            c = self._db.connect()
            if isinstance(c, sqlite3.Connection):
                return c
        raise RuntimeError("SQLiteTaskRepository: could not obtain sqlite3.Connection (.conn or .connect()).")

    def _fetch_all(self, sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        con = self._conn()
        cur = con.execute(sql, params)
        cols = [d[0] for d in cur.description]
        out: List[Dict[str, Any]] = []
        for row in cur.fetchall():
            rec = {cols[i]: row[i] for i in range(len(cols))}
            # normalize legacy keys if present
            if "name" not in rec and "title" in rec:
                rec["name"] = rec["title"]
            if "phase" in rec and "phase_name" not in rec:
                rec["phase_name"] = rec["phase"]
            out.append(rec)
        return out
