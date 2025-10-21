# Rev 0.6.8
from __future__ import annotations
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union


class SQLiteSubtaskRepository:
    """
    Subtask CRUD + filtered listing.
    Now aligned with schema Rev 0.6.8 (priority_id, old/new_priority_id).
    Every subtask change mirrors a timeline entry into subtask_updates,
    and also mirrors a lightweight entry to the parent task's task_updates.
    """

    def __init__(self, db_or_conn: Union[sqlite3.Connection, Any]):
        self._db_or_conn = db_or_conn

    # --------------- connection helpers ---------------
    def _conn(self) -> sqlite3.Connection:
        if isinstance(self._db_or_conn, sqlite3.Connection):
            return self._db_or_conn
        if hasattr(self._db_or_conn, "conn") and isinstance(self._db_or_conn.conn, sqlite3.Connection):
            return self._db_or_conn.conn
        if hasattr(self._db_or_conn, "connect"):
            maybe = self._db_or_conn.connect()
            if isinstance(maybe, sqlite3.Connection):
                return maybe
        raise RuntimeError("SQLiteSubtaskRepository: unable to obtain sqlite3.Connection (.conn/.connect() expected).")

    @staticmethod
    def _row_to_dict(row: Union[sqlite3.Row, Tuple]) -> Dict[str, Any]:
        if isinstance(row, sqlite3.Row):
            return dict(row)
        return {
            "id": row[0],
            "task_id": row[1],
            "name": row[2],
            "description": row[3],
            "phase_id": row[4],
            "priority_id": row[5],
            "created_at_utc": row[6],
            "updated_at_utc": row[7],
        }

    # --------------- CRUD ---------------
    def create_subtask(
        self,
        *,
        task_id: int,
        name: str,
        description: Optional[str] = None,
        phase_id: int = 1,  # Open
        priority_id: int = 2,  # Medium
        note_on_create: Optional[str] = None,
    ) -> int:
        con = self._conn()
        cur = con.cursor()

        # insert subtask
        cur.execute(
            """
            INSERT INTO subtasks(task_id, name, description, phase_id, priority_id, created_at_utc, updated_at_utc)
            VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (task_id, name, description or '', phase_id, priority_id),
        )
        sub_id = cur.lastrowid

        # Mirror into subtask_updates
        cur.execute(
            """
            INSERT INTO subtask_updates(subtask_id, updated_at_utc, note, reason,
                                        old_phase_id, new_phase_id,
                                        old_priority_id, new_priority_id)
            VALUES (?, datetime('now'), ?, 'create', 1, ?, ?, ?)
            """,
            (sub_id, note_on_create, phase_id, priority_id, priority_id),
        )

        # Mirror lightweight note into parent task's timeline
        cur.execute(
            """
            INSERT INTO task_updates(task_id, updated_at_utc, note, reason,
                                     old_phase_id, new_phase_id,
                                     old_priority_id, new_priority_id)
            VALUES (?, datetime('now'), ?, 'subtask_create', 1, ?, 2, ?)
            """,
            (task_id, f"[subtask #{sub_id}] {note_on_create or 'created'}", phase_id, priority_id),
        )

        con.commit()
        return sub_id

    def get_subtask(self, subtask_id: int) -> Optional[Dict[str, Any]]:
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, task_id, name, description, phase_id, priority_id, created_at_utc, updated_at_utc
            FROM subtasks
            WHERE id = ?
            """,
            (subtask_id,),
        )
        row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def update_subtask_fields(
        self,
        subtask_id: int,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        note: Optional[str] = None,
    ) -> bool:
        con = self._conn()
        cur = con.cursor()

        # Need parent task_id + current priority_id
        cur.execute("SELECT task_id, priority_id FROM subtasks WHERE id = ?", (subtask_id,))
        r = cur.fetchone()
        if not r:
            return False
        task_id = r["task_id"] if isinstance(r, sqlite3.Row) else r[0]
        priority_id = r["priority_id"] if isinstance(r, sqlite3.Row) else r[1]

        sets: List[str] = []
        params: List[Any] = []

        if name is not None:
            sets.append("name = ?")
            params.append(name)
        if description is not None:
            sets.append("description = ?")
            params.append(description)

        changed = False
        if sets:
            sets.append("updated_at_utc = datetime('now')")
            sql = f"UPDATE subtasks SET {', '.join(sets)} WHERE id = ?"
            params.append(subtask_id)
            cur.execute(sql, params)
            changed = cur.rowcount > 0

        if note:
            # subtask_updates log
            cur.execute(
                """
                INSERT INTO subtask_updates(subtask_id, updated_at_utc, note, reason,
                                            old_phase_id, new_phase_id,
                                            old_priority_id, new_priority_id)
                SELECT ?, datetime('now'), ?, 'update',
                       phase_id, phase_id, priority_id, priority_id
                FROM subtasks WHERE id = ?
                """,
                (subtask_id, note, subtask_id),
            )
            # mirror to parent task
            cur.execute(
                """
                INSERT INTO task_updates(task_id, updated_at_utc, note, reason,
                                         old_phase_id, new_phase_id,
                                         old_priority_id, new_priority_id)
                SELECT ?, datetime('now'), ?, 'subtask_update',
                       s.phase_id, s.phase_id, s.priority_id, s.priority_id
                FROM subtasks s WHERE s.id = ?
                """,
                (task_id, f"[subtask #{subtask_id}] {note}", subtask_id),
            )
            changed = True

        if changed:
            con.commit()
        return changed

    def change_subtask_phase(
        self,
        subtask_id: int,
        new_phase_id: int,
        *,
        reason: Optional[str] = None,
        note: Optional[str] = None,
    ) -> bool:
        con = self._conn()
        cur = con.cursor()

        cur.execute("SELECT task_id, phase_id, priority_id FROM subtasks WHERE id = ?", (subtask_id,))
        r = cur.fetchone()
        if not r:
            return False
        task_id = r["task_id"] if isinstance(r, sqlite3.Row) else r[0]
        old_phase_id = r["phase_id"] if isinstance(r, sqlite3.Row) else r[1]
        priority_id = r["priority_id"] if isinstance(r, sqlite3.Row) else r[2]

        if old_phase_id == new_phase_id:
            if note or reason:
                cur.execute(
                    """
                    INSERT INTO subtask_updates(subtask_id, updated_at_utc, note, reason,
                                                old_phase_id, new_phase_id,
                                                old_priority_id, new_priority_id)
                    VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
                    """,
                    (subtask_id, note, reason or "update",
                     old_phase_id, new_phase_id,
                     priority_id, priority_id),
                )
                cur.execute(
                    """
                    INSERT INTO task_updates(task_id, updated_at_utc, note, reason,
                                             old_phase_id, new_phase_id,
                                             old_priority_id, new_priority_id)
                    VALUES (?, datetime('now'), ?, 'subtask_update',
                            ?, ?, ?, ?)
                    """,
                    (task_id, f"[subtask #{subtask_id}] {note or (reason or 'no-op')}",
                     old_phase_id, new_phase_id, priority_id, priority_id),
                )
                con.commit()
            return True

        # perform phase change
        cur.execute("UPDATE subtasks SET phase_id = ? WHERE id = ?", (new_phase_id, subtask_id))

        # subtask_updates entry
        cur.execute(
            """
            INSERT INTO subtask_updates(subtask_id, updated_at_utc, note, reason,
                                        old_phase_id, new_phase_id,
                                        old_priority_id, new_priority_id)
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
            """,
            (subtask_id, note, reason or "phase_change",
             old_phase_id, new_phase_id,
             priority_id, priority_id),
        )

        # mirror to parent task timeline
        cur.execute(
            """
            INSERT INTO task_updates(task_id, updated_at_utc, note, reason,
                                     old_phase_id, new_phase_id,
                                     old_priority_id, new_priority_id)
            VALUES (?, datetime('now'), ?, 'subtask_phase_change',
                    ?, ?, ?, ?)
            """,
            (task_id, f"[subtask #{subtask_id}] {note or ''}".strip(),
             old_phase_id, new_phase_id,
             priority_id, priority_id),
        )

        con.commit()
        return cur.rowcount > 0

    def delete_subtask(self, subtask_id: int) -> bool:
        con = self._conn()
        cur = con.cursor()
        cur.execute("SELECT task_id, priority_id FROM subtasks WHERE id = ?", (subtask_id,))
        r = cur.fetchone()
        task_id = (r["task_id"] if isinstance(r, sqlite3.Row) else r[0]) if r else None
        priority_id = (r["priority_id"] if isinstance(r, sqlite3.Row) else r[1]) if r else 2

        cur.execute("DELETE FROM subtasks WHERE id = ?", (subtask_id,))
        ok = cur.rowcount > 0

        if ok and task_id is not None:
            cur.execute(
                """
                INSERT INTO task_updates(task_id, updated_at_utc, note, reason,
                                         old_phase_id, new_phase_id,
                                         old_priority_id, new_priority_id)
                VALUES (?, datetime('now'), ?, 'subtask_delete',
                        1, 1, ?, ?)
                """,
                (task_id, f"[subtask #{subtask_id}] deleted", priority_id, priority_id),
            )
        if ok:
            con.commit()
        return ok

    # --------------- lists/counts ---------------
    def list_subtasks_filtered(
        self,
        *,
        task_id: int,
        phase_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
        order_by: str = "updated_at_utc DESC",
    ) -> List[Dict[str, Any]]:
        con = self._conn()
        cur = con.cursor()
        where = ["task_id = ?"]
        params: List[Any] = [task_id]
        if phase_id is not None:
            where.append("phase_id = ?")
            params.append(phase_id)
        if search:
            where.append("(name LIKE ? OR COALESCE(description, '') LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like])
        cur.execute(
            f"""
            SELECT id, task_id, name, description, phase_id, priority_id, created_at_utc, updated_at_utc
            FROM subtasks
            WHERE {' AND '.join(where)}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        )
        return [self._row_to_dict(r) for r in cur.fetchall()]

    def list_subtasks_for_project(
        self,
        project_id: int,
        *,
        phase_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
        order_by: str = "s.updated_at_utc DESC",
    ) -> List[Dict[str, Any]]:
        con = self._conn()
        cur = con.cursor()
        where = ["t.project_id = ?"]
        params: List[Any] = [project_id]
        if phase_id is not None:
            where.append("s.phase_id = ?")
            params.append(phase_id)
        if search:
            where.append("(s.name LIKE ? OR COALESCE(s.description, '') LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like])
        cur.execute(
            f"""
            SELECT s.id, s.task_id, s.name, s.description, s.phase_id, s.priority_id,
                   s.created_at_utc, s.updated_at_utc
            FROM subtasks s
            JOIN tasks t ON t.id = s.task_id
            WHERE {' AND '.join(where)}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        )
        return [self._row_to_dict(r) for r in cur.fetchall()]
    
    def set_subtask_priority(
        self,
        subtask_id: int,
        new_priority_id: int,
        *,
        reason: str = "priority_change",
        note: str | None = None,
    ) -> bool:
        con = self._conn()
        cur = con.cursor()

        cur.execute("SELECT task_id, phase_id, priority_id FROM subtasks WHERE id = ?", (subtask_id,))
        row = cur.fetchone()
        if not row:
            return False
        task_id = row[0]
        phase_id = row[1]
        old_priority_id = row[2]

        if old_priority_id == new_priority_id:
            if note or reason:
                # log subtask note
                cur.execute(
                    """
                    INSERT INTO subtask_updates(subtask_id, updated_at_utc, note, reason,
                                                old_phase_id, new_phase_id,
                                                old_priority_id, new_priority_id)
                    VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
                    """,
                    (subtask_id, note, reason, phase_id, phase_id, old_priority_id, new_priority_id),
                )
                # mirror to parent task timeline
                cur.execute(
                    """
                    INSERT INTO task_updates(task_id, updated_at_utc, note, reason,
                                             old_phase_id, new_phase_id,
                                             old_priority_id, new_priority_id)
                    VALUES (?, datetime('now'), ?, 'subtask_update', ?, ?, ?, ?)
                    """,
                    (task_id, f"[subtask #{subtask_id}] {note or reason}",
                     phase_id, phase_id, old_priority_id, new_priority_id),
                )
                con.commit()
            return True

        # perform change
        cur.execute("UPDATE subtasks SET priority_id = ? WHERE id = ?", (new_priority_id, subtask_id))

        # subtask history
        cur.execute(
            """
            INSERT INTO subtask_updates(subtask_id, updated_at_utc, note, reason,
                                        old_phase_id, new_phase_id,
                                        old_priority_id, new_priority_id)
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?)
            """,
            (subtask_id, note, reason, phase_id, phase_id, old_priority_id, new_priority_id),
        )

        # mirror note to parent task
        cur.execute(
            """
            INSERT INTO task_updates(task_id, updated_at_utc, note, reason,
                                     old_phase_id, new_phase_id,
                                     old_priority_id, new_priority_id)
            VALUES (?, datetime('now'), ?, 'subtask_priority_change', ?, ?, ?, ?)
            """,
            (task_id, f"[subtask #{subtask_id}] {note or (reason or 'priority_change')}",
             phase_id, phase_id, old_priority_id, new_priority_id),
        )

        con.commit()
        return True


    def count_subtasks_total(self, *, task_id: int, phase_id: Optional[int] = None, search: Optional[str] = None) -> int:
        con = self._conn()
        cur = con.cursor()
        where = ["task_id = ?"]
        params: List[Any] = [task_id]
        if phase_id is not None:
            where.append("phase_id = ?")
            params.append(phase_id)
        if search:
            where.append("(name LIKE ? OR COALESCE(description, '') LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like])
        cur.execute(f"SELECT COUNT(1) FROM subtasks WHERE {' AND '.join(where)}", params)
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    def count_subtasks_total_by_project(self, *, project_id: int) -> int:
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            """
            SELECT COUNT(1)
            FROM subtasks s
            JOIN tasks t ON t.id = s.task_id
            WHERE t.project_id = ?
            """,
            (project_id,),
        )
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
