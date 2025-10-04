from __future__ import annotations
import sqlite3
from typing import List, Dict, Optional

class SqliteTaskRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON;")
        return con

    # Projects for picker
    def list_projects(self) -> List[Dict]:
        with self._connect() as con:
            cur = con.execute("""
                SELECT id, project_number, title
                FROM projects
                ORDER BY created_at_utc DESC
            """)
            return [dict(r) for r in cur.fetchall()]

    # Distinct phases for filter chips
    def list_phases(self) -> List[str]:
        with self._connect() as con:
            cur = con.execute("""SELECT name FROM phases ORDER BY sort_order ASC""")
            return [r["name"] for r in cur.fetchall()]

    # Count totals (per project)
    def count_tasks_total(self, project_id: int) -> int:
        with self._connect() as con:
            cur = con.execute("""SELECT COUNT(*) AS n FROM v_tasks_flat WHERE project_id=?""", (project_id,))
            return cur.fetchone()["n"]

    # Fetch tasks with optional filters
    def list_tasks(self, project_id: int, phase: Optional[str], search: str) -> List[Dict]:
        q = """
        SELECT id, task_number, project_id, project_number, title, description, phase,
               priority, created_at_utc, updated_at_utc
        FROM v_tasks_flat
        WHERE project_id = ?
        """
        args: List = [project_id]
        if phase:
            q += " AND phase = ?"
            args.append(phase)
        if search:
            q += " AND (title LIKE ? OR description LIKE ? OR task_number LIKE ?)"
            like = f"%{search}%"
            args += [like, like, like]
        q += " ORDER BY updated_at_utc DESC"
        with self._connect() as con:
            cur = con.execute(q, args)
            return [dict(r) for r in cur.fetchall()]

