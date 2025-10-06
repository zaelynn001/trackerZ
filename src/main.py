# trackerZ application entry point
# Rev 0.1.0

from __future__ import annotations
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from .utils.logging_setup import setup_logging, get_logger
from .ui.main_window import MainWindow
from .app_context import AppContext
from .utils.paths import data_dir

def main() -> int:
    """Initialize logging, context, and main window."""
    setup_logging()
    log = get_logger("main")

    db_path = Path(data_dir()) / "tracker.db"
    if not db_path.exists():
        log.error("Database missing at %s — verify migrations and data path.", db_path)

    ctx = AppContext.create(db_path)

    app = QApplication(sys.argv)
    win = MainWindow(ctx)
    win.show()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())

