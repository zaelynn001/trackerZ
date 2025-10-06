# trackerZ application context
# Rev 0.0.1

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .utils.logging_setup import get_logger
from .models.db import DB
from .models.dao import DAO
from .services.phase_service import PhaseService

@dataclass
class AppContext:
    """Central container for shared app resources."""
    db_path: Path
    db: DB
    dao: DAO
    phase_service: PhaseService

    @classmethod
    def create(cls, db_path: Path) -> "AppContext":
        """Initialize DB, DAO, and services."""
        log = get_logger("AppContext")
        db = DB(db_path)
        dao = DAO(db)
        phase = PhaseService(dao)
        log.info("AppContext initialized with DB=%s", db_path)
        return cls(db_path=db_path, db=db, dao=dao, phase_service=phase)

