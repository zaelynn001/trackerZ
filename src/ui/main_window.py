from __future__ import annotations
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QScrollArea, QFrame
)
from src.repositories.sqlite_task_repository import SqliteTaskRepository
from src.viewmodels.tasks_viewmodel import TasksViewModel

class MainWindow(QMainWindow):
    def __init__(self, db_path: str):
        super().__init__()
        self.setWindowTitle("trackerZ — Tasks")
        self.resize(980, 700)

        # Repo + VM
        self.repo = SqliteTaskRepository(db_path)
        self.pool = QThreadPool.globalInstance()
        self.vm = TasksViewModel(self.repo, self.pool)

        # UI
        root = QWidget()
        root_layout = QVBoxLayout(root)

        # Top bar: Project picker + search + counters
        top = QHBoxLayout()
        self.cboProject = QComboBox()
        self.txtSearch = QLineEdit()
        self.txtSearch.setPlaceholderText("Search title/description/task #")
        self.lblCounters = QLabel("Total: 0 • Filtered: 0")
        top.addWidget(QLabel("Project:"))
        top.addWidget(self.cboProject, 1)
        top.addSpacing(12)
        top.addWidget(QLabel("Search:"))
        top.addWidget(self.txtSearch, 2)
        top.addStretch(1)
        top.addWidget(self.lblCounters)
        root_layout.addLayout(top)

        # Phase filter chips
        self.phaseBar = QHBoxLayout()
        self.phaseBar.addWidget(QLabel("Phase:"))
        self.btnAll = QPushButton("All")
        self.btnAll.setCheckable(True); self.btnAll.setChecked(True)
        self.phaseBar.addWidget(self.btnAll)
        self.phaseButtons: list[QPushButton] = []
        phaseWrap = QHBoxLayout()
        root_layout.addLayout(self.phaseBar)

        # Tasks table
        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(["#", "Title", "Phase", "Priority", "Created (UTC)", "Updated (UTC)"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSelectionBehavior(self.tbl.SelectRows)
        self.tbl.setEditTriggers(self.tbl.NoEditTriggers)
        root_layout.addWidget(self.tbl, 1)

        self.setCentralWidget(root)

        # Wire signals
        self.vm.projectsChanged.connect(self._on_projects)
        self.vm.phasesChanged.connect(self._on_phases)
        self.vm.tasksChanged.connect(self._on_tasks)

        self.cboProject.currentIndexChanged.connect(self._on_project_changed)
        self.txtSearch.textChanged.connect(self.vm.set_search)
        self.btnAll.clicked.connect(lambda: self._select_phase(None))

        # Bootstrap
        self.vm.bootstrap()

    # ----- Slots -----
    def _on_projects(self, projects: list[dict]):
        self.cboProject.blockSignals(True)
        self.cboProject.clear()
        for p in projects:
            self.cboProject.addItem(f"{p['project_number']} — {p['title']}", p["id"])
        self.cboProject.blockSignals(False)

    def _on_phases(self, phases: list[str]):
        # build phase chip buttons
        # clear old (except "All")
        for b in self.phaseButtons:
            b.setParent(None)
        self.phaseButtons.clear()
        for name in phases:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, n=name: self._select_phase(n if checked else None))
            self.phaseBar.addWidget(btn)
            self.phaseButtons.append(btn)

    def _on_tasks(self, tasks: list[dict], total_count: int):
        self.tbl.setRowCount(len(tasks))
        for row, t in enumerate(tasks):
            self.tbl.setItem(row, 0, QTableWidgetItem(t["task_number"]))
            self.tbl.setItem(row, 1, QTableWidgetItem(t["title"] or ""))
            self.tbl.setItem(row, 2, QTableWidgetItem(t["phase"]))
            self.tbl.setItem(row, 3, QTableWidgetItem(t["priority"] or ""))
            self.tbl.setItem(row, 4, QTableWidgetItem(t["created_at_utc"]))
            self.tbl.setItem(row, 5, QTableWidgetItem(t["updated_at_utc"]))
        self.lblCounters.setText(f"Total: {total_count} • Filtered: {len(tasks)}")

    def _on_project_changed(self, index: int):
        pid = self.cboProject.itemData(index)
        if pid is not None:
            self.btnAll.setChecked(True)
            for b in self.phaseButtons: b.setChecked(False)
            self.vm.set_project(pid)

    def _select_phase(self, phase: str | None):
        # toggle chips: exclusive behavior with "All"
        if phase is None:
            self.btnAll.setChecked(True)
            for b in self.phaseButtons: b.setChecked(False)
        else:
            self.btnAll.setChecked(False)
            for b in self.phaseButtons:
                b.setChecked(b.text() == phase)
        self.vm.set_phase(phase)

