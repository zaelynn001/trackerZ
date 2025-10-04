# src/main.py
import sys, logging
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QMessageBox, QMenuBar, QMenu, QMessageBox
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from src.utils.config import load_settings, save_settings
from src.models.dao import list_projects_flat
from src.ui.project_overview import ProjectOverviewDialog
from src.ui.diagnostics import DiagnosticsDialog
from src.ui.diagnostics_dock import DiagnosticsDock

PROJECT_ROOT = Path(__file__).resolve().parents[1]

class ProjectTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table = QTableWidget(self)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Project #", "Title", "Description", "Phase", "Priority", "Created (UTC)", "Updated (UTC)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self._open_overview)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("trackerZ — Projects"))
        layout.addWidget(self.table)

        self._rows = []

    def load(self):
        try:
            rows = list_projects_flat()
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Database not found", str(e))
            return
        except Exception as e:
            logging.exception("Failed to load projects")
            QMessageBox.critical(self, "Error", f"Could not load projects: {e}")
            return

        self._rows = rows
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(str(row.get("id", ""))))
            self.table.setItem(r, 1, QTableWidgetItem(row.get("project_number", "")))
            self.table.setItem(r, 2, QTableWidgetItem(row.get("title", "")))
            self.table.setItem(r, 3, QTableWidgetItem(row.get("description", "")))
            self.table.setItem(r, 4, QTableWidgetItem(row.get("phase", "")))
            self.table.setItem(r, 5, QTableWidgetItem(row.get("priority", "")))
            self.table.setItem(r, 6, QTableWidgetItem(row.get("created_at_utc", "")))
            self.table.setItem(r, 7, QTableWidgetItem(row.get("updated_at_utc", "")))

    def _open_overview(self):
        idx = self.table.currentRow()
        if idx < 0 or idx >= len(self._rows):
            return
        project_id = self._rows[idx]["id"]
        dlg = ProjectOverviewDialog(project_id, parent=self)
        dlg.exec()
        self.load()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("trackerZ — Project Tracker (Project → Task → Subtask)")
        # Settings
        self._settings = load_settings()
        w = self._settings["main_window"]["width"]
        h = self._settings["main_window"]["height"]
        self.resize(w, h)
        
        # Menu bar with Diagnostics
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        help_menu = QMenu("&Help", self)
        menubar.addMenu(help_menu)

        act_diag = QAction("Diagnostics…", self)
        act_diag.triggered.connect(self._open_diagnostics)
        help_menu.addAction(act_diag)
        act_about = QAction("About", self)
        act_about.triggered.connect(self._about)
        help_menu.addAction(act_about)

        # View menu for toggling dock
        view_menu = QMenu("&View", self)
        menubar.addMenu(view_menu)
        self.act_toggle_dock = QAction("Diagnostics Panel", self, checkable=True)
        view_menu.addAction(self.act_toggle_dock)
        self.act_toggle_dock.triggered.connect(self._toggle_dock)

        self.table = ProjectTable()
        self.setCentralWidget(self.table)
        
        # Diagnostics dock
        self.dock = DiagnosticsDock(self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock)
        dock_visible = bool(self._settings["ui"].get("diagnostics_dock_visible", True))
        self.dock.setVisible(dock_visible)
        self.act_toggle_dock.setChecked(dock_visible)
    def showEvent(self, event):
        super().showEvent(event)
        self.table.load()

    def _open_diagnostics(self):
        dlg = DiagnosticsDialog(PROJECT_ROOT, parent=self)
        dlg.exec()
        
    def _toggle_dock(self):
        vis = not self.dock.isVisible()
        self.dock.setVisible(vis)
        self.act_toggle_dock.setChecked(vis)

    def _about(self):
        QMessageBox.information(self, "About trackerZ",
            "trackerZ — Native project tracker for Ubuntu\n"
            "Hierarchy: Project → Task → Subtask\n"
            "© 2025 — Internal tool")

    def closeEvent(self, event):
        # Save simple settings
        self._settings["main_window"]["is_maximized"] = self.isMaximized()
        if not self.isMaximized():
            self._settings["main_window"]["width"] = self.width()
            self._settings["main_window"]["height"] = self.height()
        self._settings["ui"]["diagnostics_dock_visible"] = self.dock.isVisible()
        try:
            save_settings(self._settings)
        finally:
            super().closeEvent(event)

def main():
    # Initialize logging first
    init_logging()

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())

