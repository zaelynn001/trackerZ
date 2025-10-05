# -*- coding: utf-8 -*-
# M04: Task repository used by TasksViewModel.
# - Robust to different constructors (conn_factory | db_path | no-arg)
# - Works with either legacy timestamps (created_at/updated_at) or *_utc
# - Returns dict rows
# - Provides count_tasks_total() and list_tasks_filtered()

from __future__ import annotations

from typing import Optional, List, Dict, Any, Callable
from src.models.db import get_connection


class SQLiteTaskRepository:
    def __init__(self, db_path: str | None = None, conn_factory: Callable | None = None):
        self._db_path = db_path
        # accept either name to be compatible with other repos in your tree
        self._conn_factory = conn_factory or getattr(self, "conn_factory", None)

    # ---------- connection + helpers ----------

    def _conn(self):
        """Open a connection using an injected factory if present, else global get_connection()."""
        if self._conn_factory:
            return self._conn_factory()
        return get_connection()

    @staticmethod
    def _dict_factory(cursor, row):
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    def _scalar_from_row(self, row: Any) -> int:
        """
        Return the first column's value as int regardless of row_factory.
        - If row is a mapping (dict), take first value.
        - If row is a sequence/tuple, take index 0.
        """
        if row is None:
            return 0
        if hasattr(row, "values"):
            try:
                value = next(iter(row.values()))
                return int(value or 0)
            except StopIteration:
                return 0
        return int(row[0] if row else 0)

    def _task_cols(self) -> set[str]:
        # Be robust to any row_factory: temporarily disable it to get tuples.
        with self._conn() as conn:
            prev = getattr(conn, "row_factory", None)
            try:
                conn.row_factory = None  # PRAGMA returns tuples: (cid, name, type, ... )
                cur = conn.execute("PRAGMA table_info(tasks);")
                rows = cur.fetchall()
                return {row[1] for row in rows}  # column names
            finally:
                # restore whatever row_factory the connection had
                if prev is not None:
                    conn.row_factory = prev

    # ---------- public API ----------

    def count_tasks_total(self, project_id: Optional[int]) -> int:
        sql = "SELECT COUNT(*) AS cnt FROM tasks"
        params: list[Any] = []
        if project_id is not None:
            sql += " WHERE project_id = ?"
            params.append(project_id)
        with self._conn() as conn:
            cur = conn.execute(sql, params)
            row = cur.fetchone()
            return self._scalar_from_row(row)

    def list_tasks_filtered(
        self,
        project_id: Optional[int],
        phase_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Returns list of dict rows:
          id, project_id, title, phase_id, phase_name, created_at, updated_at
        Adapts to schemas that may have only *_utc or only legacy timestamp columns.
        """
        cols = self._task_cols()
        created_src = "created_at_utc" if "created_at_utc" in cols else ("created_at" if "created_at" in cols else None)
        updated_src = "updated_at_utc" if "updated_at_utc" in cols else ("updated_at" if "updated_at" in cols else None)

        where = []
        params: list[Any] = []
        if project_id is not None:
            where.append("t.project_id = ?")
            params.append(project_id)
        if phase_id is not None:
            where.append("t.phase_id = ?")
            params.append(phase_id)
        if search:
            where.append("LOWER(t.title) LIKE LOWER(?)")
            params.append(f"%{search}%")
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        created_sel = f"t.{created_src} AS created_at" if created_src else "NULL AS created_at"
        updated_sel = f"t.{updated_src} AS updated_at" if updated_src else "NULL AS updated_at"

        order_by = f"ORDER BY t.{updated_src} DESC, t.id DESC" if updated_src else "ORDER BY t.id DESC"

        sql = f"""
            SELECT
                t.id,
                t.project_id,
                t.title,
                t.phase_id,
                p.name AS phase_name,
                {created_sel},
                {updated_sel}
            FROM tasks t
            JOIN phases p ON p.id = t.phase_id
            {where_sql}
            {order_by}
            LIMIT ? OFFSET ?;
        """.strip()

        params.extend([limit, offset])

        with self._conn() as conn:
            conn.row_factory = self._dict_factory
            cur = conn.execute(sql, params)
            return cur.fetchall()

