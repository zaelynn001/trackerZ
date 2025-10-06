# trackerZ logging setup
# Rev 0.0.1

from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from .paths import log_dir

_LOGGER_NAME = "trackerZ"
_DEF_FMT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Initialize rotating file + console logger."""
    logger = logging.getLogger(_LOGGER_NAME)
    if getattr(logger, "_configured", False):
        return logger

    logger.setLevel(level)
    log_path: Path = log_dir() / "trackerZ.log"

    fh = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3)
    fh.setFormatter(logging.Formatter(_DEF_FMT))
    fh.setLevel(level)

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(_DEF_FMT))
    ch.setLevel(level)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger._configured = True  # type: ignore[attr-defined]
    logger.info("Logging initialized at %s", log_path)
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return namespaced child logger."""
    base = logging.getLogger(_LOGGER_NAME)
    return base if name is None else base.getChild(name)

