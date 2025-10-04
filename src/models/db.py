# src/models/db.py
import os
import sqlite3
from contextlib import contextmanager

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

def _default_db_path() -> str:
    return os.path.join(PROJECT_ROOT, "data", "tracker.db")

# Allow tests or tools to point to a different DB file:
DB_PATH = os.environ.get("TRACKERZ_DB", _default_db_path())

def set_db_path(path: str):
    global DB_PATH
    DB_PATH = path

def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def get_connection():
    # Ensure DB exists
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Did you run schema.sql and seed.sql?")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def tx():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

