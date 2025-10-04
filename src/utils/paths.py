# src/utils/paths.py
import os
from pathlib import Path

APP_NAME = "trackerZ"

def _home() -> Path:
    return Path.home()

def xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", _home() / ".local" / "share"))

def xdg_state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", _home() / ".local" / "state"))

def xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", _home() / ".config"))

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def logs_dir() -> Path:
    return ensure_dir(xdg_state_home() / APP_NAME / "logs")

def config_dir() -> Path:
    return ensure_dir(xdg_config_home() / APP_NAME)

def db_path(project_root: Path) -> Path:
    # dev DB path (later we can switch to XDG data if you want)
    return project_root / "data" / "tracker.db"

