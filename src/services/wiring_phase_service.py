# src/services/wiring_phase_service.py
# Convenience wiring for PhaseService <-> SQLitePhaseRepository

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.repositories.sqlite_phase_repository import SQLitePhaseRepository
from src.services.phase_service import PhaseService  # existing service in your repo


def build_phase_service(db_path: Optional[str | Path]) -> PhaseService:
    """
    Returns a PhaseService instance wired to the SQLite repo.
    db_path can be your XDG data path (recommended).
    """
    repo = SQLitePhaseRepository(db_path=db_path)
    return PhaseService(repo)

