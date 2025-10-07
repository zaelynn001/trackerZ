# src/repositories/sqlite_phase_repository.py
# Rev 0.1.1
from __future__ import annotations
import sqlite3
from typing import List, Tuple

class SQLitePhaseRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn  # private handle to the database

    def list_phases(self) -> List[Tuple[int, str]]:
        """
        Returns [(phase_id, phase_name)] ordered by id.
        """
        cur = self._conn.cursor()
        cur.execute("""
            SELECT id, COALESCE(name, '') AS name
            FROM phases
            ORDER BY id ASC
        """)
        return [(int(r[0]), r[1] or "") for r in cur.fetchall()]

