# Rev 0.6.5

"""Paths and XDG helpers (Rev 0.6.5)
- Uses XDG Base Directory spec
- Logs/state/config remain under XDG dirs
- **DB now lives in project repo at** ./data/trackerZ.db (as requested)
"""
from __future__ import annotations
import os
from pathlib import Path


APP_NAME = "trackerZ"


XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
XDG_STATE_HOME = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


# XDG locations (still used for logs/config)
DATA_DIR = XDG_DATA_HOME / APP_NAME
STATE_DIR = XDG_STATE_HOME / APP_NAME
LOGS_DIR = STATE_DIR / "logs"
CONFIG_DIR = XDG_CONFIG_HOME / APP_NAME


# Project-relative locations
RUNTIME_ROOT = Path(__file__).resolve().parents[2]
PROJECT_DATA_DIR = (RUNTIME_ROOT / "data").resolve()
MIGRATIONS_DIR = (PROJECT_DATA_DIR / "migrations").resolve()


# DB is now stored in the repo's data/ folder
DB_PATH = PROJECT_DATA_DIR / "trackerZ.db"




def ensure_dirs() -> None:
    # Ensure both XDG dirs (for logs/config) and project data dir (for DB)
    for p in (DATA_DIR, STATE_DIR, LOGS_DIR, CONFIG_DIR, PROJECT_DATA_DIR):
        p.mkdir(parents=True, exist_ok=True)


