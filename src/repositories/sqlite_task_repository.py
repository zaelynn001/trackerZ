# Rev 0.5.1
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional


class SQLiteTaskRepository:
    """
    Task CRUD + filtered listing + mirrored timeline inserts.

    Schema expectations:
      tasks(
        id INTEGER PRIMARY KEY,
        project_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT NULL,
        phase_id INTEGER NOT NULL,
        created_at_utc TEXT NOT NULL,
        updated_at_utc TEXT NOT NULL
      )
      task_updates(
        id INTEGER PRIMARY KEY,
        task_id INTEGER NOT NULL,
        updated_at_utc TEXT NOT NULL,
        note TEXT NULL,
        reason TEXT NULL,
        old_phase_id INTEGER NULL,
        new_phase_id INTEGER NULL
      )
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    # -------------------------
    # CRUD
    # -------------------------
    def create_task(
        self,
        *,
        project_id: int,
        name: str,
        description: Optional[str] = None,
        phase_id: int = 1,  # Open
        note_on_create: Optional[str] = None,
    ) -> int:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO tasks(project_id, name, description, phase_id, created_at_utc, updated_at_utc)
            VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (project_id, name, description, phase_id),
        )
        task_id = cur.lastrowid

        # Mirror initial timeline entry
        cur.execute(
            """
            INSERT INTO task_updates(task_id, updated_at_utc, note, reason, old_phase_id, new_phase_id)
            VALUES (?, datetime('now'), ?, 'create', NULL, ?)
            """,
            (task_id, note_on_create, phase_id),
        )
        self._conn.commit()
        return task_id

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT id, project_id, name, description, phase_id, created_at_utc, updated_at_utc
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def update_task_fields(
        self,
        task_id: int,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        note: Optional[str] = None,
    ) -> bool:
        sets: List[str] = []
        params: List[Any] = []

        if name is not None:
            sets.append("name = ?")
            params.append(name)
        if description is not None:
            sets.append("description = ?")
            params.append(description)

        cur = self._conn.cursor()

        if sets:
            sets.append("updated_at_utc = datetime('now')")
            sql = f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?"
            params.append(task_id)
            cur.execute(sql, params)
            changed = cur.rowcount > 0
            if changed and note:
                self._insert_generic_update(task_id, note=note, reason="update")
            self._conn.commit()
            return changed

        # No field changes, but caller may still want to drop a note
        if note:
            self._insert_generic_update(task_id, note=note, reason="update")
            self._conn.commit()
            return True
        return False

    def change_task_phase(
        self,
        task_id: int,
        new_phase_id: int,
        *,
        reason: Optional[str] = None,
        note: Optional[str] = None,
    ) -> bool:
        cur = self._conn.cursor()
        cur.execute("SELECT phase_id FROM tasks WHERE id = ?", (task_id,))
        r = cur.fetchone()
        if not r:
            return False

        old_phase_id = r["phase_id"]
        if old_phase_id == new_phase_id:
            # Still record a note if provided.
            if note or reason:
                self._insert_generic_update(task_id, note=note, reason=reason or "update")
                self._conn.commit()
            return True

        # DB triggers validate phase rules and touch updated_at_utc
        cur.execute("UPDATE tasks SET phase_id = ? WHERE id = ?", (new_phase_id, task_id))

        # Mirror phase change
        cur.execute(
            """
            INSERT INTO task_updates(task_id, updated_at_utc, note, reason, old_phase_id, new_phase_id)
            VALUES (?, datetime('now'), ?, ?, ?, ?)
            """,
            (task_id, note, reason or "phase_change", old_phase_id, new_phase_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self._conn.commit()
        return cur.rowcount > 0

    # -------------------------
    # Listings
    # -------------------------
    def list_tasks_filtered(
        self,
        *,
        project_id: int,
        phase_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "updated_at_utc DESC",
    ) -> List[Dict[str, Any]]:
        where = ["project_id = ?"]
        params: List[Any] = [project_id]

        if phase_id is not None:
            where.append("phase_id = ?")
            params.append(phase_id)
        if search:
            where.append("(name LIKE ? OR COALESCE(description, '') LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like])

        sql = f"""
            SELECT id, project_id, name, description, phase_id, created_at_utc, updated_at_utc
            FROM tasks
            WHERE {' AND '.join(where)}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cur = self._conn.cursor()
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def count_tasks_total(
        self,
        *,
        project_id: int,
        phase_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> int:
        where = ["project_id = ?"]
        params: List[Any] = [project_id]

        if phase_id is not None:
            where.append("phase_id = ?")
            params.append(phase_id)
        if search:
            where.append("(name LIKE ? OR COALESCE(description, '') LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like])

        cur = self._conn.cursor()
        cur.execute(f"SELECT COUNT(1) AS c FROM tasks WHERE {' AND '.join(where)}", params)
        r = cur.fetchone()
        return int(r["c"] if r else 0)

    # -------------------------
    # Internals
    # -------------------------
    def _insert_generic_update(self, task_id: int, *, note: Optional[str], reason: Optional[str]):
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO task_updates(task_id, updated_at_utc, note, reason, old_phase_id, new_phase_id)
            VALUES (?, datetime('now'), ?, ?, NULL, NULL)
            """,
            (task_id, note, reason),
        )
