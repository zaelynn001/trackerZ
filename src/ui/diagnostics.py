# src/ui/diagnostics.py
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices, QClipboard, QTextCursor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout, QLabel, QPushButton,
    QHBoxLayout, QPlainTextEdit, QMessageBox, QFileDialog, QApplication
)

from src.utils.logging_setup import init_logging
from src.utils.paths import logs_dir
from src.models.db import DB_PATH

def _tail_lines(path: Path, max_lines: int = 400) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return "".join(lines[-max_lines:])
    except FileNotFoundError:
        return "(log file not found)"
    except Exception as e:
        return f"(error reading log: {e})"

class DiagnosticsDialog(QDialog):
    def __init__(self, project_root: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("trackerZ — Diagnostics")
        self.resize(860, 560)
        self.project_root = project_root

        # Ensure logging so we know the file path
        self.log_file = init_logging()

        self.tabs = QTabWidget(self)
        self.tab_env = QWidget()
        self.tab_logs = QWidget()
        self.tabs.addTab(self.tab_env, "Environment")
        self.tabs.addTab(self.tab_logs, "Logs")

        root = QVBoxLayout(self)
        root.addWidget(self.tabs)

        self._build_env_tab()
        self._build_logs_tab()
        self._load_env()
        self._load_logs()

    # ── Environment tab ───────────────────────────────────────
    def _build_env_tab(self):
        self.lbl_python = QLabel()
        self.lbl_qt = QLabel()
        self.lbl_platform = QLabel()
        self.lbl_repo = QLabel()
        self.lbl_db = QLabel()
        self.lbl_logs = QLabel()

        form = QFormLayout(self.tab_env)
        form.addRow("Python", self.lbl_python)
        form.addRow("Qt", self.lbl_qt)
        form.addRow("Platform", self.lbl_platform)
        form.addRow("Project Root", self.lbl_repo)
        form.addRow("Database Path", self.lbl_db)
        form.addRow("Log File", self.lbl_logs)

        # Buttons
        btns = QHBoxLayout()
        self.btn_open_logs = QPushButton("Open Logs Folder")
        self.btn_open_logs.clicked.connect(self._open_logs_folder)
        self.btn_open_db = QPushButton("Open DB Folder")
        self.btn_open_db.clicked.connect(self._open_db_folder)
        btns.addWidget(self.btn_open_logs)
        btns.addWidget(self.btn_open_db)
        form.addRow(btns)

    def _load_env(self):
        try:
            import PySide6
            from PySide6 import QtCore
            qt_ver = QtCore.qVersion()
        except Exception:
            qt_ver = "(unknown)"

        self.lbl_python.setText(f"{platform.python_version()} — {sys.executable}")
        self.lbl_qt.setText(qt_ver)
        self.lbl_platform.setText(f"{platform.system()} {platform.release()} ({platform.machine()})")
        self.lbl_repo.setText(str(self.project_root))
        self.lbl_db.setText(str(DB_PATH))
        self.lbl_logs.setText(str(self.log_file))

    def _open_logs_folder(self):
        folder = logs_dir()
        QDesktopServices.openUrl(folder.as_uri())

    def _open_db_folder(self):
        dbp = Path(DB_PATH)
        QDesktopServices.openUrl(dbp.parent.as_uri())

    # ── Logs tab ──────────────────────────────────────────────
    def _build_logs_tab(self):
        lay = QVBoxLayout(self.tab_logs)
        self.log_view = QPlainTextEdit(self.tab_logs)
        self.log_view.setReadOnly(True)

        btns = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._load_logs)
        self.btn_copy = QPushButton("Copy All")
        self.btn_copy.clicked.connect(self._copy_logs)
        self.btn_open_file = QPushButton("Open Log File")
        self.btn_open_file.clicked.connect(self._open_log_file)

        btns.addWidget(self.btn_refresh)
        btns.addWidget(self.btn_copy)
        btns.addWidget(self.btn_open_file)

        lay.addLayout(btns)
        lay.addWidget(self.log_view, 1)

    def _load_logs(self):
        text = _tail_lines(Path(self.log_file))
        self.log_view.setPlainText(text)
        self.log_view.moveCursor(QTextCursor.End)

    def _copy_logs(self):
        text = self.log_view.toPlainText()
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Log contents copied to clipboard.")

    def _open_log_file(self):
        lf = Path(self.log_file)
        if lf.exists():
            QDesktopServices.openUrl(lf.as_uri())
        else:
            QMessageBox.warning(self, "Missing", "Log file not found.")

