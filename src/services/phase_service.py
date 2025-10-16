# Rev 0.6.7

"""Phase rules service (Rev 0.6.7)
Provide allow/deny checks for phase changes.
"""
from __future__ import annotations
import sqlite3
from typing import Iterable, Set




class PhaseService:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn


    def is_allowed(self, from_id: int, to_id: int) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM phase_transitions WHERE from_phase_id=? AND to_phase_id=?",
            (from_id, to_id),
        ).fetchone()
        return row is not None


    def allowed_transitions(self, from_id: int) -> Set[int]:
        rows = self._conn.execute(
            "SELECT to_phase_id FROM phase_transitions WHERE from_phase_id=? ORDER BY to_phase_id",
            (from_id,),
        ).fetchall()
        return {r[0] for r in rows}
