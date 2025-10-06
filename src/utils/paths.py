# Rev 0.0.2

from __future__ import annotations
import os
from pathlib import Path

APP_ID = "trackerZ"

def state_dir() -> Path:
    """Return XDG-compliant state directory, e.g. ~/.local/state/trackerZ"""
    base = Path(os.getenv("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    p = base / APP_ID
    p.mkdir(parents=True, exist_ok=True)
    return p

def log_dir() -> Path:
    """Return trackerZ log directory under state dir"""
    p = state_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p

def data_dir() -> Path:
    """Return current repo data directory (for db + migrations)"""
    return Path.cwd() / "data"

