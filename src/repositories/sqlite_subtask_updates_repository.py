# Rev 0.6.5
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union


class SQLiteSubtaskUpdatesRepository:
    """
    Read/append timeline entries for subtask_updates.

    Schema expectation (Rev 0.6.5):

      subtask_updates(
        id INTEGER PRIMARY KEY,
        subtask_id INTEGER NOT NULL,
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

    # ---- conn ----
    def _conn(self) -> sqlite3.Connection:
        if isinstance(self._db_or_conn, sqlite3.Connection):
            return self._db_or_conn
        if hasattr(self._db_or_conn, "conn") and isinstance(self._db_or_conn.conn, sqlite3.Connection):
            return self._db_or_conn.conn
        if hasattr(self._db_or_conn, "connect"):
            maybe = self._db_or_conn.connect()
            if isinstance(maybe, sqlite3.Connection):
                return maybe
        raise RuntimeError("SQLiteSubtaskUpdatesRepository: could not obtain sqlite3.Connection.")

    @staticmethod
    def _row_to_dict(row: Union[sqlite3.Row, Tuple]) -> Dict[str, Any]:
        if isinstance(row, sqlite3.Row):
            return dict(row)
        return {
            "id": row[0],
            "subtask_id": row[1],
            "updated_at_utc": row[2],
            "note": row[3],
            "reason": row[4],
            "old_phase_id": row[5],
            "new_phase_id": row[6],
            "old_priority_id": row[7],
            "new_priority_id": row[8],
        }

    # ---- queries ----
    def list_updates_for_subtask(
        self,
        subtask_id: int,
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
            SELECT id, subtask_id, updated_at_utc, note, reason,
                   old_phase_id, new_phase_id, old_priority_id, new_priority_id
            FROM subtask_updates
            WHERE subtask_id = ?
            ORDER BY datetime(updated_at_utc) {order}, id {order}
            LIMIT ? OFFSET ?
            """,
            (subtask_id, limit, offset),
        )
        rows = cur.fetchall()
        return [self._row_to_dict(r) for r in rows]

    # ---- commands ----
    def add_note(
        self,
        subtask_id: int,
        note: str,
        *,
        reason: str = "note",
        phase_id: int = 1,
        priority_id: int = 2,
    ) -> int:
        """
        Adds a simple note-only update. You must pass current phase_id/priority_id to satisfy NOT NULLs.
        """
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO subtask_updates(
              subtask_id, updated_at_utc, note, reason,
              old_phase_id, new_phase_id,
              old_priority_id, new_priority_id
            )
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
            """,
            (subtask_id, note, reason, phase_id, phase_id, priority_id, priority_id),
        )
        con.commit()
        return cur.lastrowid

    def add_update(
        self,
        subtask_id: int,
        *,
        note: Optional[str] = None,
        reason: str = "update",
        old_phase_id: int = 1,
        new_phase_id: int = 1,
        old_priority_id: int = 2,
        new_priority_id: int = 2,
    ) -> int:
        """
        Adds a structured update entry with explicit old/new phase and priority IDs.
        """
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO subtask_updates(
              subtask_id, updated_at_utc, note, reason,
              old_phase_id, new_phase_id,
              old_priority_id, new_priority_id
            )
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
            """,
            (
                subtask_id,
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
