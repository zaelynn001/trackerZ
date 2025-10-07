# src/main.py
# Rev 0.1.1
from __future__ import annotations

import os
import sys
import sqlite3
from pathlib import Path
from datetime import timezone

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

# --- Logging (use project logger if available) ---
try:
    # Prefer repo’s logging helper if present
    from utils.logging_setup import setup_logging  # type: ignore
except Exception:
    setup_logging = None  # fallback below

import logging

def _init_logging():
    if setup_logging:
        setup_logging()
        return
    # Fallback: ~/.local/state/trackerZ/logs/trackerZ.log
    state_dir = Path.home() / ".local" / "state" / "trackerZ" / "logs"
    state_dir.mkdir(parents=True, exist_ok=True)
    log_path = state_dir / "trackerZ.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)],
    )
    logging.getLogger(__name__).info("Logging initialized at %s", log_path)

# --- DB helpers ---
def _default_db_path() -> Path:
    # Env override → project data/tracker.db → XDG data dir
    env = os.getenv("TRACKERZ_DB")
    if env:
        return Path(env)
    repo_db = Path(__file__).resolve().parent.parent / "data" / "tracker.db"
    if repo_db.exists():
        return repo_db
    xdg = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    data_dir = xdg / "trackerZ"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "tracker.db"

def _open_sqlite(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA foreign_keys=ON;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA busy_timeout=5000;")
    conn.commit()
    logging.getLogger(__name__).info("SQLite opened at %s (WAL ON)", db_path)
    return conn

# --- Repositories (import concrete classes) ---
def _build_repositories(conn):
    from repositories.sqlite_projects_repository import SQLiteProjectsRepository
    from repositories.sqlite_task_repository import SQLiteTaskRepository
    from repositories.sqlite_phase_repository import SQLitePhaseRepository
    from repositories.sqlite_subtask_repository import SQLiteSubtaskRepository
    return (
        SQLiteProjectsRepository(conn),
        SQLiteTaskRepository(conn),
        SQLitePhaseRepository(conn),
        SQLiteSubtaskRepository(conn),
    )

# --- ViewModels and UI ---
def _build_viewmodels(projects_repo, tasks_repo, phases_repo, subtasks_repo):
    from viewmodels.projects_viewmodel import ProjectsViewModel
    from viewmodels.tasks_viewmodel import TasksViewModel
    return ProjectsViewModel(projects_repo), TasksViewModel(tasks_repo, phases_repo, subtasks_repo)


def _build_main_window(projects_vm, tasks_vm):
    from ui.main_window import MainWindow
    win = MainWindow(projects_vm=projects_vm, tasks_vm=tasks_vm)
    return win

# --- Qt app bootstrap ---
def main() -> int:
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["TZ"] = "UTC"  # app uses UTC timestamps
    _init_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("trackerZ")
    app.setOrganizationName("trackerZ")
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    db_path = _default_db_path()
    conn = _open_sqlite(db_path)

    try:
        projects_repo, tasks_repo, phases_repo, subtasks_repo = _build_repositories(conn)
    except Exception as e:
        logging.getLogger(__name__).exception("Repository wiring failed")
        raise

    projects_vm, tasks_vm = _build_viewmodels(projects_repo, tasks_repo, phases_repo, subtasks_repo)
    win = _build_main_window(projects_vm, tasks_vm)
    win.resize(1100, 720)
    win.show()

    code = app.exec()
    try:
        conn.close()
    finally:
        return code

if __name__ == "__main__":
    sys.exit(main())

