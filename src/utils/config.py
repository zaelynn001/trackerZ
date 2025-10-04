# src/utils/config.py
import json
from pathlib import Path
from typing import Any, Dict
from .paths import config_dir

SETTINGS_FILE = config_dir() / "settings.json"

_DEFAULTS: Dict[str, Any] = {
    "main_window": {
        "width": 1100,
        "height": 600,
        "is_maximized": False,
    },
    "ui": {
        "diagnostics_dock_visible": True
    }
}

def load_settings() -> Dict[str, Any]:
    if SETTINGS_FILE.exists():
        try:
            return {**_DEFAULTS, **json.loads(SETTINGS_FILE.read_text())}
        except Exception:
            return _DEFAULTS.copy()
    return _DEFAULTS.copy()

def save_settings(data: Dict[str, Any]) -> None:
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))

