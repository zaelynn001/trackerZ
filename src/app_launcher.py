# Rev 0.1.0

from __future__ import annotations
import sys, os
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    db_path = os.environ.get("TRACKERZ_DB", "data/tracker.db")
    app = QApplication(sys.argv)
    win = MainWindow(db_path)
    win.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())

