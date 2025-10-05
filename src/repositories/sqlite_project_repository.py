# -*- coding: utf-8 -*-
# Minimal project repo for pickers in M04

from __future__ import annotations
from typing import List, Dict, Any
from src.models.db import get_connection


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class SQLiteProjectRepository:
    def list_all_projects(self) -> List[Dict[str, Any]]:
        """
        Returns:
          [ { "id": int, "title": str }, ... ]
        """
        sql = """
            SELECT id, title
            FROM projects
            ORDER BY title COLLATE NOCASE ASC, id ASC;
        """
        with get_connection() as conn:
            conn.row_factory = _dict_factory
            cur = conn.execute(sql)
            return cur.fetchall()

