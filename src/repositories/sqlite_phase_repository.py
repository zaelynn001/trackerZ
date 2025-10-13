# Rev 0.5.1

# trackerZ – SQLitePhaseRepository (Rev 0.5.1)
# Minimal repo used by M4 (phase dropdowns, etc.)

from __future__ import annotations
import sqlite3
from typing import List, Optional, Dict, Any

class SQLitePhaseRepository:
    """
    Thin wrapper around the 'phases' table.
    Expected schema (minimum): phases(id INTEGER PRIMARY KEY, name TEXT NOT NULL)
    If you have extra columns (e.g., code, sort_order), this still works.
    """

    def __init__(self, db):
        """
        `db` is your Database wrapper (repositories/db.py).
        It may expose either `.conn` (sqlite3.Connection) or a `.connect()` method.
        """
        self._db = db

    # --- public API ---------------------------------------------------------

    def list_phases(self) -> List[Dict[str, Any]]:
        """
        Returns a list of {id, name} for all phases.
        """
        sql = "SELECT id, name FROM phases ORDER BY id;"
        return self._fetch_all(sql)

    def get_phase(self, phase_id: int) -> Optional[Dict[str, Any]]:
        """
        Returns a single {id, name} for the given phase_id, or None.
        """
        sql = "SELECT id, name FROM phases WHERE id = ?;"
        rows = self._fetch_all(sql, (phase_id,))
        return rows[0] if rows else None

    # --- internals ----------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        # Support either a direct .conn attribute or a .connect() method on your db wrapper
        if hasattr(self._db, "conn") and isinstance(self._db.conn, sqlite3.Connection):
            return self._db.conn
        if hasattr(self._db, "connect"):
            c = self._db.connect()
            if isinstance(c, sqlite3.Connection):
                return c
        raise RuntimeError("Database handle does not expose a sqlite3.Connection via .conn or .connect().")

    def _fetch_all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        con = self._conn()
        cur = con.execute(sql, params)
        cols = [d[0] for d in cur.description]
        out: List[Dict[str, Any]] = []
        for row in cur.fetchall():
            rec = {cols[i]: row[i] for i in range(len(cols))}
            # normalize minimal keys expected by UI
            if "name" not in rec and "title" in rec:
                rec["name"] = rec["title"]
            out.append(rec)
        return out

