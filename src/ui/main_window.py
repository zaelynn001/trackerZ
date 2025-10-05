# -*- coding: utf-8 -*-
# File: src/ui/main_window.py
# M04: UI shell — project picker → tasks list with filters and Total • Filtered counters.

from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import Qt, Slot, QEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QProgressBar, QMessageBox, QMenuBar, QMenu
)
from PySide6.QtCore import QModelIndex
from PySide6.QtGui import QAction

from src.viewmodels.tasks_viewmodel import TasksViewModel, TaskRow
from src.repositories.sqlite_phase_repository import SQLitePhaseRepository
from src.repositories.sqlite_project_repository import SQLiteProjectRepository
from src.models.db import get_connection
from src.ui.project_overview import ProjectOverviewDialog
from src.ui.diagnostics import DiagnosticsDialog


class MainWindow(QMainWindow):
    def __init__(self, db_path: Optional[str] = None, parent: Optional[QWidget] = None):
        # IMPORTANT: parent must be a QWidget (or None), not a string.
        super().__init__(parent)

        # If app_launcher passes a DB path, expose it to the connection factory.
        if db_path:
            os.environ["TRACKERZ_DB"] = db_path
        self._db_path = db_path

        self.setWindowTitle("trackerZ — M04")
        self.resize(1100, 700)
        
        # --- Menubar ---
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        view_menu = QMenu("&View", self)
        menubar.addMenu(view_menu)
        act_overview = QAction("Project Overview…", self)
        act_overview.triggered.connect(self._openProjectOverview)
        view_menu.addAction(act_overview)

        help_menu = QMenu("&Help", self)
        menubar.addMenu(help_menu)
        act_diag = QAction("Diagnostics…", self)
        act_diag.triggered.connect(self._openDiagnostics)
        help_menu.addAction(act_diag)


        # --- Repos to populate pickers ---
        self._phase_repo = self._make_repo(SQLitePhaseRepository)
        self._project_repo = self._make_repo(SQLiteProjectRepository)

        # --- ViewModel ---
        self.vm = TasksViewModel(self)
        self.vm.countersChanged.connect(self._onCountersChanged)
        self.vm.rowsChanged.connect(self._onRowsChanged)
        self.vm.busyChanged.connect(self._onBusyChanged)

        # --- Top bar: Project, Phase, Search, Counters ---
        top = QWidget(self)
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(6, 6, 6, 6)
        top_layout.setSpacing(10)

        self.projectLabel = QLabel("Project:", top)
        self.projectPicker = QComboBox(top)
        self.projectPicker.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.projectPicker.currentIndexChanged.connect(self._onProjectChanged)
        # Enable double-click on the closed combo box (field area)
        self.projectPicker.installEventFilter(self)

        self.phaseLabel = QLabel("Phase:", top)
        self.phasePicker = QComboBox(top)
        self.phasePicker.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.phasePicker.currentIndexChanged.connect(self._onPhaseChanged)

        self.searchEdit = QLineEdit(top)
        self.searchEdit.setPlaceholderText("Search tasks…")
        self.searchEdit.returnPressed.connect(self._onSearch)
        self.searchEdit.textEdited.connect(self._onSearchLive)

        self.countersLabel = QLabel("Total: 0 • Filtered: 0", top)
        self.countersLabel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.busyBar = QProgressBar(top)
        self.busyBar.setRange(0, 0)
        self.busyBar.setVisible(False)
        self.busyBar.setFixedWidth(120)

        top_layout.addWidget(self.projectLabel)
        top_layout.addWidget(self.projectPicker)
        top_layout.addSpacing(12)
        top_layout.addWidget(self.phaseLabel)
        top_layout.addWidget(self.phasePicker)
        top_layout.addSpacing(12)
        top_layout.addWidget(self.searchEdit, 1)
        top_layout.addSpacing(12)
        top_layout.addWidget(self.countersLabel, 0, Qt.AlignRight)
        top_layout.addWidget(self.busyBar)

        # --- Table ---
        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Phase", "Created", "Updated"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSortingEnabled(False)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # --- Central layout ---
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(6)
        root_layout.addWidget(top)
        root_layout.addWidget(self.table, 1)
        self.setCentralWidget(root)

        # Populate pickers & kick first load
        self._populateProjects()
        self._populatePhases()
        self._triggerInitialLoad()
        
        # Enable: double-click a project in the combo’s popup to open overview
        try:
            view = self.projectPicker.view()  # QListView backing the QComboBox popup
            if view is not None:
                view.doubleClicked.connect(self._onProjectDoubleClicked)
        except Exception:
            # Non-fatal: some styles may not expose a view until first show
            pass

        
    # ---------- Helpers ----------
    def _make_repo(self, repo_cls):
        """
        Some repos in your tree accept (conn_factory=...), others accept (db_path=...),
        and a few are no-arg. Try all three safely.
        """
        # 1) Try conn_factory
        try:
            return repo_cls(conn_factory=get_connection)  # type: ignore[arg-type]
        except TypeError:
            pass
        except ValueError:
            # e.g., SQLitePhaseRepository explicitly raises ValueError for bad args
            pass

        # 2) Try db_path (if provided)
        if getattr(self, "_db_path", None):
            try:
                return repo_cls(db_path=self._db_path)  # type: ignore[arg-type]
            except TypeError:
                pass
            except ValueError:
                pass

        # 3) Fall back to no-arg constructor
        return repo_cls()


    # ---------- Populate pickers ----------

    def _populateProjects(self) -> None:
        self.projectPicker.blockSignals(True)
        self.projectPicker.clear()
        self.projectPicker.addItem("— Select Project —", userData=None)
        for proj in self._project_repo.list_all_projects():
            self.projectPicker.addItem(proj["title"], userData=proj["id"])
        self.projectPicker.blockSignals(False)

    def _populatePhases(self) -> None:
        self.phasePicker.blockSignals(True)
        self.phasePicker.clear()
        self.phasePicker.addItem("All phases", userData=None)
        for ph in self._phase_repo.list_all_phases():
            self.phasePicker.addItem(ph["name"], userData=ph["id"])
        self.phasePicker.blockSignals(False)

    # ---------- Event handlers ----------

    @Slot()
    def _triggerInitialLoad(self) -> None:
        if self.projectPicker.count() > 1:
            self.projectPicker.setCurrentIndex(1)
        else:
            self.vm.refresh()
            

    # ---------- Double-click handlers ----------
    def eventFilter(self, obj, event):
        if obj is self.projectPicker and event.type() == QEvent.MouseButtonDblClick:
            self._openProjectOverview()
            return True
        return super().eventFilter(obj, event)

    @Slot()
    def _onProjectListDoubleClicked(self, index):
        # Sync selection to the item double-clicked in the popup list
        try:
            row = index.row()
            if 0 <= row < self.projectPicker.count():
                self.projectPicker.setCurrentIndex(row)
        except Exception:
            pass
        self._openProjectOverview()

    def _openProjectOverview(self) -> None:
        project_id = self.projectPicker.currentData()
        if project_id is None:
            QMessageBox.information(self, "Project Overview", "Please select a project first.")
            return
        dlg = ProjectOverviewDialog(int(project_id), parent=self)
        dlg.exec()
        # If the overview can change tasks, refresh afterwards
        self.vm.refresh()

    def _openDiagnostics(self) -> None:
        try:
            # PROJECT_ROOT discovery: up two parents from this file
            from pathlib import Path
            project_root = Path(__file__).resolve().parents[2]
            dlg = DiagnosticsDialog(project_root, parent=self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Diagnostics", f"Failed to open diagnostics: {e}")

    @Slot(int)
    def _onProjectChanged(self, index: int) -> None:
        project_id = self.projectPicker.currentData()
        if project_id is None:
            self.vm.setProject(None)  # type: ignore[arg-type]
            return
        self.vm.setProject(int(project_id))

    @Slot(int)
    def _onPhaseChanged(self, index: int) -> None:
        phase_id = self.phasePicker.currentData()
        if phase_id is None:
            self.vm.setPhaseFilter(None)
        else:
            self.vm.setPhaseFilter(int(phase_id))

    @Slot()
    def _onSearch(self) -> None:
        self.vm.setSearch(self.searchEdit.text())

    @Slot(str)
    def _onSearchLive(self, _text: str) -> None:
        self.vm.setSearch(self.searchEdit.text())

    # ---------- VM signal handlers ----------

    @Slot(int, int)
    def _onCountersChanged(self, total: int, filtered: int) -> None:
        self.countersLabel.setText(f"Total: {total} • Filtered: {filtered}")

    @Slot(list)
    def _onRowsChanged(self, rows: list[TaskRow]) -> None:
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(str(row.id)))
            self.table.setItem(r, 1, QTableWidgetItem(row.title))
            self.table.setItem(r, 2, QTableWidgetItem(row.phase))
            self.table.setItem(r, 3, QTableWidgetItem(row.created_at or ""))
            self.table.setItem(r, 4, QTableWidgetItem(row.updated_at or ""))

    @Slot(bool)
    def _onBusyChanged(self, busy: bool) -> None:
        self.busyBar.setVisible(busy)

