# Rev 0.4.1

# src/main.py  (Rev 0.4.1)
import sys
from PySide6.QtGui import QGuiApplication, QFont
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import QApplication 
from repositories.db import Database
from repositories.sqlite_project_repository import SQLiteProjectRepository
from repositories.sqlite_task_repository import SQLiteTaskRepository
from repositories.sqlite_subtask_repository import SQLiteSubtaskRepository
from repositories.sqlite_phase_repository import SQLitePhaseRepository
from ui.main_window import MainWindow

from src.utils.logging_setup import setup_logging

def _build_repositories(db_path: str):
    db = Database(db_path)
    db.run_migrations()
    return (
        SQLiteProjectRepository(db),
        SQLiteTaskRepository(db),
        SQLiteSubtaskRepository(db),
        SQLitePhaseRepository(db),
    )

def main():
    app = QApplication(sys.argv)
    
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QCoreApplication.setOrganizationName("zaelynn")
    QCoreApplication.setApplicationName("trackerZ")
    
    logfile = setup_logging("trackerZ")
    print(f"[logging] Writing to: {logfile}")  # also lands in run.sh tee
    # --- DI wiring ---
    projects_repo, tasks_repo, subtasks_repo, phases_repo = _build_repositories("data/tracker.db")

    # --- UI ---
    win = MainWindow(
        projects_repo=projects_repo,
        tasks_repo=tasks_repo,
        subtasks_repo=subtasks_repo,
        phases_repo=phases_repo,
        attachments_repo=None,
        expenses_repo=None,
        logfile=logfile,
    )
    win.show()

    # Keep a strong ref just in case someone stores nothing at module level
    app.setProperty("mainWindow", win)
    app.setFont(QFont("Sans Serif", 10))

    # CRUCIAL: start the event loop
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())

