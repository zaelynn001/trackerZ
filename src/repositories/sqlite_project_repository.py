# Rev 0.6.7
# trackerZ – SQLiteProjectRepository (Rev 0.6.7, aligned with schema Rev 1.1.0)
from __future__ import annotations
import sqlite3
from typing import List, Dict, Any, Optional


class SQLiteProjectRepository:
    """
    Project repository.
    Handles new schema fields: phase_id, priority_id.
    """

    def __init__(self, db_or_conn):
        self._db = db_or_conn

    # ---------- public API ----------

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        Returns all projects with id, name, description, phase_id, priority_id.
        """
        sql = """
            SELECT
                id,
                name,
                description,
                phase_id,
                priority_id
            FROM projects
            ORDER BY id DESC;
        """
        return self._fetch_all(sql)

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        Returns a single project by ID.
        """
        sql = """
            SELECT
                id,
                name,
                description,
                phase_id,
                priority_id
            FROM projects
            WHERE id = ?;
        """
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
        # ---------- mutations: project-level phase/priority ----------

    def set_project_phase(self, project_id: int, new_phase_id: int, *, reason: str = "phase_change", note: str | None = None) -> bool:
        con = self._conn()
        cur = con.cursor()
        cur.execute("SELECT phase_id, priority_id FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
        if not row:
            return False
        old_phase_id, priority_id = row[0], row[1]

        if old_phase_id == new_phase_id:
            if note or reason:
                cur.execute("""
                    INSERT INTO project_updates(project_id, updated_at_utc, note, reason,
                                                old_phase_id, new_phase_id, old_priority_id, new_priority_id)
                    VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
                """, (project_id, note, reason, old_phase_id, new_phase_id, priority_id, priority_id))
                con.commit()
            return True

        # validate phase transition
        cur.execute("""
            SELECT 1 FROM phase_transitions WHERE from_phase_id = ? AND to_phase_id = ?
        """, (old_phase_id, new_phase_id))
        if cur.fetchone() is None:
            return False

        cur.execute("UPDATE projects SET phase_id = ? WHERE id = ?", (new_phase_id, project_id))
        cur.execute("""
            INSERT INTO project_updates(project_id, updated_at_utc, note, reason,
                                        old_phase_id, new_phase_id, old_priority_id, new_priority_id)
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
        """, (project_id, note, reason, old_phase_id, new_phase_id, priority_id, priority_id))
        con.commit()
        return True

    def set_project_priority(self, project_id: int, new_priority_id: int, *, reason: str = "priority_change", note: str | None = None) -> bool:
        con = self._conn()
        cur = con.cursor()
        cur.execute("SELECT phase_id, priority_id FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
        if not row:
            return False
        phase_id, old_priority_id = row[0], row[1]

        if old_priority_id == new_priority_id:
            if note or reason:
                cur.execute("""
                    INSERT INTO project_updates(project_id, updated_at_utc, note, reason,
                                                old_phase_id, new_phase_id, old_priority_id, new_priority_id)
                    VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
                """, (project_id, note, reason, phase_id, phase_id, old_priority_id, new_priority_id))
                con.commit()
            return True

        cur.execute("UPDATE projects SET priority_id = ? WHERE id = ?", (new_priority_id, project_id))
        cur.execute("""
            INSERT INTO project_updates(project_id, updated_at_utc, note, reason,
                                        old_phase_id, new_phase_id, old_priority_id, new_priority_id)
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
        """, (project_id, note, reason, phase_id, phase_id, old_priority_id, new_priority_id))
        con.commit()
        return True

    def add_project_note(self, project_id: int, *, note: str, reason: str = "note") -> int:
        """Note-only entry; fills all NOT NULLs from current row."""
        con = self._conn()
        cur = con.cursor()
        cur.execute("SELECT phase_id, priority_id FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Project not found")
        phase_id, priority_id = row[0], row[1]
        cur.execute("""
            INSERT INTO project_updates(project_id, updated_at_utc, note, reason,
                                        old_phase_id, new_phase_id, old_priority_id, new_priority_id)
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
        """, (project_id, note, reason, phase_id, phase_id, priority_id, priority_id))
        con.commit()
        return cur.lastrowid

