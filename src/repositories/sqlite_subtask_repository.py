# Rev 0.5.1

# trackerZ – SQLiteSubtaskRepository (Rev 0.5.1)
from __future__ import annotations
import sqlite3
from typing import List, Dict, Any, Optional, Tuple

class SQLiteSubtaskRepository:
    """
    Minimal read API used by M4:
      - count_subtasks_total(project_id)
      - list_subtasks_for_project(project_id)
    Works with a raw sqlite3.Connection OR a Database wrapper exposing .conn or .connect().
    """
    def __init__(self, db_or_conn):
        self._db = db_or_conn

    # ---------- Public API ----------

    def count_subtasks_total(self, project_id: int) -> int:
        """
        Counts all subtasks that belong to tasks in the given project.
        """
        sql = """
            SELECT COUNT(*)
            FROM subtasks st
            JOIN tasks t ON t.id = st.task_id
            WHERE t.project_id = ?;
        """
        con = self._conn()
        cur = con.execute(sql, (project_id,))
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    def list_subtasks_for_project(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Returns rows shaped like:
          { id, task_id, name, phase_name, task_name }
        """
        sql = """
            SELECT
                st.id                                        AS id,
                st.task_id                                   AS task_id,
                st.name                                      AS name,
                COALESCE(p.name, '')                         AS phase_name,
                COALESCE(t.name, 'Task ' || t.id)   AS task_name
            FROM subtasks st
            JOIN tasks t   ON t.id = st.task_id
            LEFT JOIN phases p ON p.id = st.phase_id
            WHERE t.project_id = ?
            ORDER BY st.id DESC;
        """
        return self._fetch_all(sql, (project_id,))

    # Optional helper if you need a single subtask later
    def get_subtask(self, subtask_id: int) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT
                st.id                                        AS id,
                st.task_id                                   AS task_id,
                st.name                                      AS name,
                st.phase_id                                  AS phase_id
            FROM subtasks st
            WHERE st.id = ?;
        """
        rows = self._fetch_all(sql, (subtask_id,))
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
        raise RuntimeError("SQLiteSubtaskRepository: could not obtain sqlite3.Connection (.conn or .connect()).")

    def _fetch_all(self, sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        con = self._conn()
        cur = con.execute(sql, params)
        cols = [d[0] for d in cur.description]
        out: List[Dict[str, Any]] = []
        for row in cur.fetchall():
            rec = {cols[i]: row[i] for i in range(len(cols))}
            if "name" not in rec and "title" in rec:
                rec["name"] = rec["title"]
            out.append(rec)
        return out

