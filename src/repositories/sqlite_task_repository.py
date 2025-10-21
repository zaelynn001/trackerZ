# Rev 0.6.8
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union


class SQLiteTaskRepository:
    """
    Task CRUD + filtered listing + mirrored timeline inserts.
    Updated for schema Rev 0.6.8 (priority_id on tasks;
    old_priority_id/new_priority_id on task_updates).
    """

    def __init__(self, db_or_conn: Union[sqlite3.Connection, Any]):
        self._db_or_conn = db_or_conn

    # -------------------------
    # Connection handling
    # -------------------------
    def _conn(self) -> sqlite3.Connection:
        c = None
        if isinstance(self._db_or_conn, sqlite3.Connection):
            c = self._db_or_conn
        elif hasattr(self._db_or_conn, "conn") and isinstance(self._db_or_conn.conn, sqlite3.Connection):
            c = self._db_or_conn.conn
        elif hasattr(self._db_or_conn, "connect"):
            maybe = self._db_or_conn.connect()
            if isinstance(maybe, sqlite3.Connection):
                c = maybe
        if c is None:
            raise RuntimeError(
                "SQLiteTaskRepository: could not obtain sqlite3.Connection "
                "(expected .conn or .connect() on wrapper, or a raw Connection)."
            )
        return c

    @staticmethod
    def _row_to_task_dict(row: Union[sqlite3.Row, Tuple]) -> Dict[str, Any]:
        if isinstance(row, sqlite3.Row):
            return dict(row)
        return {
            "id": row[0],
            "project_id": row[1],
            "name": row[2],
            "description": row[3],
            "phase_id": row[4],
            "priority_id": row[5],
            "created_at_utc": row[6],
            "updated_at_utc": row[7],
        }

    # -------------------------
    # CRUD
    # -------------------------
    def create_task(
        self,
        *,
        project_id: int,
        name: str,
        description: Optional[str] = None,
        phase_id: int = 1,          # Open
        priority_id: int = 2,       # Medium
        note_on_create: Optional[str] = None,
    ) -> int:
        con = self._conn()
        cur = con.cursor()

        # insert new task
        cur.execute(
            """
            INSERT INTO tasks(project_id, name, description, phase_id, priority_id,
                              created_at_utc, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (project_id, name, description or '', phase_id, priority_id),
        )
        task_id = cur.lastrowid

        # mirror create entry into task_updates
        cur.execute(
            """
            INSERT INTO task_updates(task_id, updated_at_utc, note, reason,
                                     old_phase_id, new_phase_id,
                                     old_priority_id, new_priority_id)
            VALUES (?, datetime('now'), ?, 'create', 1, ?, 2, ?)
            """,
            (task_id, note_on_create, phase_id, priority_id),
        )
        con.commit()
        return task_id

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, project_id, name, description, phase_id, priority_id,
                   created_at_utc, updated_at_utc
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        )
        row = cur.fetchone()
        return self._row_to_task_dict(row) if row else None

    def update_task_fields(
        self,
        task_id: int,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        note: Optional[str] = None,
    ) -> bool:
        con = self._conn()
        cur = con.cursor()

        # get existing priority for update logs
        cur.execute("SELECT priority_id FROM tasks WHERE id = ?", (task_id,))
        r = cur.fetchone()
        if not r:
            return False
        priority_id = r["priority_id"] if isinstance(r, sqlite3.Row) else r[0]

        sets, params = [], []
        if name is not None:
            sets.append("name = ?")
            params.append(name)
        if description is not None:
            sets.append("description = ?")
            params.append(description)

        changed = False
        if sets:
            sets.append("updated_at_utc = datetime('now')")
            sql = f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?"
            params.append(task_id)
            cur.execute(sql, params)
            changed = cur.rowcount > 0

        if note:
            # always include valid phase_id/priority_id values for NOT NULLs
            cur.execute(
                """
                INSERT INTO task_updates(task_id, updated_at_utc, note, reason,
                                         old_phase_id, new_phase_id,
                                         old_priority_id, new_priority_id)
                SELECT ?, datetime('now'), ?, 'update',
                       phase_id, phase_id, priority_id, priority_id
                FROM tasks WHERE id = ?
                """,
                (task_id, note, task_id),
            )
            changed = True

        if changed:
            con.commit()
        return changed

    def change_task_phase(
        self,
        task_id: int,
        new_phase_id: int,
        *,
        reason: Optional[str] = None,
        note: Optional[str] = None,
    ) -> bool:
        con = self._conn()
        cur = con.cursor()
        cur.execute("SELECT phase_id, priority_id FROM tasks WHERE id = ?", (task_id,))
        r = cur.fetchone()
        if not r:
            return False
        old_phase_id = r["phase_id"] if isinstance(r, sqlite3.Row) else r[0]
        priority_id = r["priority_id"] if isinstance(r, sqlite3.Row) else r[1]

        if old_phase_id == new_phase_id:
            if note or reason:
                cur.execute(
                    """
                    INSERT INTO task_updates(task_id, updated_at_utc, note, reason,
                                             old_phase_id, new_phase_id,
                                             old_priority_id, new_priority_id)
                    VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
                    """,
                    (task_id, note, reason or "update",
                     old_phase_id, new_phase_id, priority_id, priority_id),
                )
                con.commit()
            return True

        # perform phase change
        cur.execute("UPDATE tasks SET phase_id = ? WHERE id = ?", (new_phase_id, task_id))

        # mirror timeline entry
        cur.execute(
            """
            INSERT INTO task_updates(task_id, updated_at_utc, note, reason,
                                     old_phase_id, new_phase_id,
                                     old_priority_id, new_priority_id)
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
            """,
            (task_id, note, reason or "phase_change",
             old_phase_id, new_phase_id, priority_id, priority_id),
        )
        con.commit()
        return cur.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        con = self._conn()
        cur = con.cursor()
        cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        con.commit()
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
        con = self._conn()
        cur = con.cursor()
        where, params = ["project_id = ?"], [project_id]
        if phase_id is not None:
            where.append("phase_id = ?")
            params.append(phase_id)
        if search:
            where.append("(name LIKE ? OR COALESCE(description, '') LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like])

        cur.execute(
            f"""
            SELECT id, project_id, name, description, phase_id, priority_id,
                   created_at_utc, updated_at_utc
            FROM tasks
            WHERE {' AND '.join(where)}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        )
        return [self._row_to_task_dict(r) for r in cur.fetchall()]
        
    def set_task_priority(
        self,
        task_id: int,
        new_priority_id: int,
        *,
        reason: str = "priority_change",
        note: str | None = None,
    ) -> bool:
        con = self._conn()
        cur = con.cursor()

        cur.execute("SELECT phase_id, priority_id FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        if not row:
            return False
        phase_id = row[0]
        old_priority_id = row[1]

        if old_priority_id == new_priority_id:
            if note or reason:
                cur.execute(
                    """
                    INSERT INTO task_updates(task_id, updated_at_utc, note, reason,
                                             old_phase_id, new_phase_id,
                                             old_priority_id, new_priority_id)
                    VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
                    """,
                    (task_id, note, reason, phase_id, phase_id, old_priority_id, new_priority_id),
                )
                con.commit()
            return True

        cur.execute("UPDATE tasks SET priority_id = ? WHERE id = ?", (new_priority_id, task_id))
        cur.execute(
            """
            INSERT INTO task_updates(task_id, updated_at_utc, note, reason,
                                     old_phase_id, new_phase_id,
                                     old_priority_id, new_priority_id)
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
            """,
            (task_id, note, reason, phase_id, phase_id, old_priority_id, new_priority_id),
        )
        con.commit()
        return True


    def count_tasks_total(
        self,
        *,
        project_id: int,
        phase_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> int:
        con = self._conn()
        cur = con.cursor()
        where, params = ["project_id = ?"], [project_id]
        if phase_id is not None:
            where.append("phase_id = ?")
            params.append(phase_id)
        if search:
            where.append("(name LIKE ? OR COALESCE(description, '') LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like])
        cur.execute(f"SELECT COUNT(1) FROM tasks WHERE {' AND '.join(where)}", params)
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
        
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Return a single task row as a dict, or None if not found.
        Columns: id, project_id, name, description, phase_id, priority_id, created_at_utc, updated_at_utc
        """
        con = self._conn()
        cur = con.cursor()
        cur.execute("""
            SELECT id, project_id, name, description, phase_id, priority_id, created_at_utc, updated_at_utc
            FROM tasks
            WHERE id = ?
            LIMIT 1
        """, (task_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "project_id": row[1],
            "name": row[2],
            "description": row[3] or "",
            "phase_id": row[4],
            "priority_id": row[5],
            "created_at_utc": row[6],
            "updated_at_utc": row[7],
        }

