# Rev 0.6.7

# trackerZ – logging setup (Rev 0.6.7)
from __future__ import annotations
import logging, os, sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

try:
    # Optional: pipe Qt messages into Python logging if Qt exists
    from PySide6.QtCore import qInstallMessageHandler, QtMsgType
    def _qt_handler(msg_type, context, message):
        lvl = {
            QtMsgType.QtDebugMsg: logging.DEBUG,
            QtMsgType.QtInfoMsg: logging.INFO,
            QtMsgType.QtWarningMsg: logging.WARNING,
            QtMsgType.QtCriticalMsg: logging.ERROR,
            QtMsgType.QtFatalMsg: logging.CRITICAL,
        }.get(msg_type, logging.INFO)
        logging.getLogger("qt").log(lvl, message)
except Exception:
    qInstallMessageHandler = None  # PySide6 not available at import time
    
APP_NAME = "trackerZ"
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", "~/.local/state")).expanduser() / APP_NAME / "logs"
STATE_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = STATE_DIR / "trackerZ.log"  # <-- exported symbol diagnostics_panel expects

def _state_dir(app: str = "trackerZ") -> Path:
    base = os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
    d = Path(base) / app / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d

def setup_logging(app_name: str = "trackerZ") -> Path:
    # Level via env (DEBUG/INFO/WARNING/ERROR), default INFO
    level_name = os.environ.get("TRACKERZ_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    log_dir = _state_dir(app_name)
    logfile = log_dir / "trackerZ.log"

    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(level)

    # File: rotate at 5MB, keep 7 backups
    fh = RotatingFileHandler(logfile, maxBytes=5_000_000, backupCount=7, encoding="utf-8")
    fh.setFormatter(logging.Formatter(fmt, datefmt))
    fh.setLevel(level)
    root.addHandler(fh)

    # Console: inherit level; nice for ./run.sh --debug
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter(fmt, datefmt))
    ch.setLevel(level)
    root.addHandler(ch)

    # Uncaught exceptions → log as ERROR
    def _excepthook(exctype, value, tb):
        logging.getLogger("unhandled").exception("Uncaught exception", exc_info=(exctype, value, tb))
        # keep default behavior
        sys.__excepthook__(exctype, value, tb)
    sys.excepthook = _excepthook

    # Route Qt messages if available (after QApplication is created is also fine)
    if qInstallMessageHandler is not None:
        try:
            qInstallMessageHandler(_qt_handler)
        except Exception:
            pass

    logging.getLogger(__name__).info("Logging initialized at %s; file: %s", level_name, logfile)
    return logfile

