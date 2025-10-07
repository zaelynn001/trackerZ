# trackerZ DB adapter
# Rev 0.1.1

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from ..utils.logging_setup import get_logger

@dataclass
class DB:
    """Lightweight SQLite wrapper with sane pragmas."""
    path: Path

    def __post_init__(self):
        self._log = get_logger("DB")
        self.conn = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self._log.info("SQLite open %s", self.path)

    # Thin delegation helpers
    def cursor(self):
        return self.conn.cursor()

    def execute(self, *a, **k):
        return self.conn.execute(*a, **k)

    def executemany(self, *a, **k):
        return self.conn.executemany(*a, **k)

    def commit(self):
        return self.conn.commit()

