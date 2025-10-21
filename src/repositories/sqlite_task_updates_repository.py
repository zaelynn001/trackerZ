# Rev 0.6.8 — schema Rev 1.1.0 alignment
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union


class SQLiteTaskUpdatesRepository:
    """
    Read/append timeline entries for task_updates.

    Schema expectation (Rev 0.6.8):

      task_updates(
        id INTEGER PRIMARY KEY,
        task_id INTEGER NOT NULL,
        updated_at_utc TEXT NOT NULL,
        note TEXT NULL,
        reason TEXT NOT NULL,
        old_phase_id INTEGER NOT NULL,
        new_phase_id INTEGER NOT NULL,
        old_priority_id INTEGER NOT NULL,
        new_priority_id INTEGER NOT NULL
      )
    """

    def __init__(self, db_or_conn: Union[sqlite3.Connection, Any]):
        self._db_or_conn = db_or_conn

    # -------------------------
    # Connection handling
    # -------------------------
    def _conn(self) -> sqlite3.Connection:
        if isinstance(self._db_or_conn, sqlite3.Connection):
            return self._db_or_conn
        if hasattr(self._db_or_conn, "conn") and isinstance(self._db_or_conn.conn, sqlite3.Connection):
            return self._db_or_conn.conn
        if hasattr(self._db_or_conn, "connect"):
            maybe = self._db_or_conn.connect()
            if isinstance(maybe, sqlite3.Connection):
                return maybe
        raise RuntimeError(
            "SQLiteTaskUpdatesRepository: could not obtain sqlite3.Connection "
            "(expected .conn or .connect() on wrapper, or a raw Connection)."
        )

    @staticmethod
    def _row_to_update_dict(row: Union[sqlite3.Row, Tuple]) -> Dict[str, Any]:
        if isinstance(row, sqlite3.Row):
            return dict(row)
        return {
            "id": row[0],
            "task_id": row[1],
            "updated_at_utc": row[2],
            "note": row[3],
            "reason": row[4],
            "old_phase_id": row[5],
            "new_phase_id": row[6],
            "old_priority_id": row[7],
            "new_priority_id": row[8],
        }

    # -------------------------
    # Queries
    # -------------------------
    def list_updates_for_task(
        self,
        task_id: int,
        *,
        limit: int = 200,
        offset: int = 0,
        order_desc: bool = True,
    ) -> List[Dict[str, Any]]:
        con = self._conn()
        cur = con.cursor()
        order = "DESC" if order_desc else "ASC"
        cur.execute(
            f"""
            SELECT id,
                   task_id,
                   updated_at_utc,
                   note,
                   reason,
                   old_phase_id,
                   new_phase_id,
                   old_priority_id,
                   new_priority_id
            FROM task_updates
            WHERE task_id = ?
            ORDER BY datetime(updated_at_utc) {order}, id {order}
            LIMIT ? OFFSET ?
            """,
            (task_id, limit, offset),
        )
        rows = cur.fetchall()
        return [self._row_to_update_dict(r) for r in rows]

    # -------------------------
    # Commands
    # -------------------------
    def add_note(
        self,
        task_id: int,
        note: str,
        *,
        reason: str = "note",
        phase_id: int = 1,
        priority_id: int = 2,
    ) -> int:
        """Add a simple note-only entry, supplying current phase and priority IDs."""
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO task_updates(
              task_id, updated_at_utc, note, reason,
              old_phase_id, new_phase_id,
              old_priority_id, new_priority_id
            )
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
            """,
            (task_id, note, reason, phase_id, phase_id, priority_id, priority_id),
        )
        con.commit()
        return cur.lastrowid

    def add_update(
        self,
        task_id: int,
        *,
        note: Optional[str] = None,
        reason: str = "update",
        old_phase_id: int = 1,
        new_phase_id: int = 1,
        old_priority_id: int = 2,
        new_priority_id: int = 2,
    ) -> int:
        """Add a full update record with explicit old/new phase and priority IDs."""
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO task_updates(
              task_id, updated_at_utc, note, reason,
              old_phase_id, new_phase_id,
              old_priority_id, new_priority_id
            )
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                note,
                reason,
                old_phase_id,
                new_phase_id,
                old_priority_id,
                new_priority_id,
            ),
        )
        con.commit()
        return cur.lastrowid
