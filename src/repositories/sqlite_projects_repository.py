# src/repositories/sqlite_projects_repository.py
# Rev 0.1.1
from __future__ import annotations
import sqlite3, datetime as _dt
from typing import List, Tuple

class SQLiteProjectsRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn  # private handle to the database

    def list_projects(self) -> List[Tuple[int, str]]:
        """
        Returns [(project_id, name)] ordered by name then id.
        Falls back to title if name missing.
        """
        cur = self._conn.cursor()
        # Prefer 'name', fallback to 'title'
        cur.execute("""
            SELECT id,
                   COALESCE(name, '') AS display_name
            FROM projects
            ORDER BY display_name COLLATE NOCASE ASC, id ASC
        """)
        return [(int(r[0]), r[1] or "") for r in cur.fetchall()]

    def insert_project(self, name: str, note: str | None) -> int:
       now = _dt.datetime.utcnow().isoformat(timespec="seconds")
       cur = self._conn.execute(
           """
           INSERT INTO projects (name, note, created_at, updated_at) 
           VALUES (?, ?, ?, ?)
           """,
           (name, note, now, now),
       )
       self._conn.commit()
       return int(cur.lastrowid)
