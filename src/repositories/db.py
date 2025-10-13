# Rev 0.5.1

"""SQLite connection & migration runner (Rev 0.5.1)
- WAL mode, foreign_keys=ON
- Applies SQL files in data/migrations in lexical order
- Tracks applied files in schema_migrations(filename TEXT PRIMARY KEY, applied_at UTC)
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Iterable


from src.utils.paths import DB_PATH, MIGRATIONS_DIR, ensure_dirs




class Database:
    def __init__(self, path: Path | str = DB_PATH) -> None:
        ensure_dirs()
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self.conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )


    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass


    def applied(self) -> set[str]:
        rows = self.conn.execute("SELECT filename FROM schema_migrations").fetchall()
        return {r[0] for r in rows}


    def apply_sql(self, sql: str) -> None:
        self.conn.executescript(sql)


    def run_migrations(self, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
        applied = self.applied()
        to_apply = [p for p in sorted(migrations_dir.glob("*.sql")) if p.name not in applied]
        for p in to_apply:
            sql = p.read_text(encoding="utf-8")
            self.apply_sql(sql)
            self.conn.execute(
                "INSERT INTO schema_migrations(filename, applied_at) VALUES(?, ?)",
                (p.name, datetime.now(timezone.utc).isoformat()),
            )
        return [p.name for p in to_apply]


    # Convenience cursor
    def cursor(self) -> sqlite3.Cursor:
        return self.conn.cursor()
