# src/utils/logging_setup.py
import logging
import logging.handlers
from pathlib import Path
from .paths import logs_dir

def init_logging(app_name: str = "trackerZ") -> Path:
    logs_path = logs_dir()
    log_file = logs_path / f"{app_name}.log"

    root = logging.getLogger()
    if root.handlers:
        return log_file  # already initialized

    root.setLevel(logging.INFO)

    # Console handler (INFO+)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))

    # Rotating file handler (keep a few small logs)
    fh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=512_000, backupCount=5, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [%(process)d:%(threadName)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z"
    ))

    root.addHandler(ch)
    root.addHandler(fh)

    logging.getLogger(__name__).info("Logging initialized at %s", log_file)
    return log_file

