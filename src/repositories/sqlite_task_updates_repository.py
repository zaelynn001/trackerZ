# Rev 0.5.1
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional


class SQLiteTaskUpdatesRepository:
    """
    Read/append timeline entries for tasks (task_updates).
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    def list_updates_for_task(
        self,
        task_id: int,
        *,
        limit: int = 200,
        offset: int = 0,
        order_desc: bool = True,
    ) -> List[Dict[str, Any]]:
        order = "DESC" if order_desc else "ASC"
        cur = self._conn.cursor()
        cur.execute(
            f"""
            SELECT id,
                   task_id,
                   updated_at_utc,
                   note,
                   reason,
                   old_phase_id,
                   new_phase_id
            FROM task_updates
            WHERE task_id = ?
            ORDER BY datetime(updated_at_utc) {order}, id {order}
            LIMIT ? OFFSET ?
            """,
            (task_id, limit, offset),
        )
        return [dict(r) for r in cur.fetchall()]

    def add_note(
        self,
        task_id: int,
        note: str,
        *,
        reason: str = "note",
    ) -> int:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO task_updates(task_id, updated_at_utc, note, reason, old_phase_id, new_phase_id)
            VALUES (?, datetime('now'), ?, ?, NULL, NULL)
            """,
            (task_id, note, reason),
        )
        self._conn.commit()
        return cur.lastrowid

    def add_update(
        self,
        task_id: int,
        *,
        note: Optional[str] = None,
        reason: Optional[str] = "update",
        old_phase_id: Optional[int] = None,
        new_phase_id: Optional[int] = None,
    ) -> int:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO task_updates(task_id, updated_at_utc, note, reason, old_phase_id, new_phase_id)
            VALUES (?, datetime('now'), ?, ?, ?, ?)
            """,
            (task_id, note, reason, old_phase_id, new_phase_id),
        )
        self._conn.commit()
        return cur.lastrowid
