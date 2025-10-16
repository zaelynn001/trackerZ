# Rev 0.6.5

"""Pytest fixtures for trackerZ (Rev 0.6.5)"""
from __future__ import annotations
import sqlite3
import pytest
from pathlib import Path
from src.repositories.db import Database




@pytest.fixture()
def db_conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    db = Database(path=str(db_path))
    try:
        db.run_migrations()
        yield db.conn
    finally:
        db.close()
