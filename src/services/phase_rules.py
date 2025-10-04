# src/services/phase_rules.py
from typing import Optional
from src.models.db import tx

def is_allowed_phase_change(old_phase_id: int, new_phase_id: int) -> bool:
    """Return True if a transition old→new exists in phase_transitions."""
    with tx() as conn:
        row = conn.execute(
            "SELECT 1 FROM phase_transitions WHERE from_phase_id = ? AND to_phase_id = ?",
            (old_phase_id, new_phase_id),
        ).fetchone()
        return bool(row)

def current_phase_id_for(table: str, pk_name: str, pk_value: int) -> Optional[int]:
    """Fetch current phase_id for a row in `table` with primary key `pk_name`."""
    with tx() as conn:
        row = conn.execute(
            f"SELECT phase_id FROM {table} WHERE {pk_name} = ?", (pk_value,)
        ).fetchone()
        return row["phase_id"] if row else None

