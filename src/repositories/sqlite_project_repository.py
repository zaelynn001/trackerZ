# Rev 0.4.1

# trackerZ – SQLiteProjectRepository (Rev 0.4.1)
from __future__ import annotations
import sqlite3
from typing import List, Dict, Any, Optional

class SQLiteProjectRepository:
    """
    Read-only bits needed for M4 (list projects, get one).
    Works whether you pass:
      - a Database wrapper exposing `.conn` (sqlite3.Connection) OR `.connect() -> sqlite3.Connection`
      - a raw sqlite3.Connection
    """

    def __init__(self, db_or_conn):
        self._db = db_or_conn

    # ---------- public API ----------

    def list_projects(self) -> List[Dict[str, Any]]:
        sql = "SELECT id, name, description FROM projects ORDER BY id DESC;"
        return self._fetch_all(sql)

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        sql = "SELECT id, name, description FROM projects WHERE id = ?;"
        rows = self._fetch_all(sql, (project_id,))
        return rows[0] if rows else None

    # ---------- internals ----------

    def _conn(self) -> sqlite3.Connection:
        # You can pass a raw sqlite3.Connection directly
        if isinstance(self._db, sqlite3.Connection):
            return self._db

        # Or a wrapper with .conn (property) or .connect() (method)
        if hasattr(self._db, "conn") and isinstance(self._db.conn, sqlite3.Connection):
            return self._db.conn
        if hasattr(self._db, "connect"):
            c = self._db.connect()
            if isinstance(c, sqlite3.Connection):
                return c

        raise RuntimeError(
            "SQLiteProjectRepository: could not obtain sqlite3.Connection "
            "from db wrapper (.conn or .connect())."
        )

    def _fetch_all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        con = self._conn()
        cur = con.execute(sql, params)
        cols = [d[0] for d in cur.description]
        out: List[Dict[str, Any]] = []
        for row in cur.fetchall():
            rec = {cols[i]: row[i] for i in range(len(cols))}
            # normalize name/title just in case
            if "name" not in rec and "title" in rec:
                rec["name"] = rec["title"]
            out.append(rec)
        return out

