# Rev 0.6.5
# trackerZ – ProjectOverviewWindow
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel
)

from viewmodels.project_overview_viewmodel import ProjectOverviewViewModel
from ui.tabs.overview_tab import OverviewTab
from ui.tabs.tasks_tab import TasksTab
from ui.tabs.subtasks_tab import SubtasksTab
from ui.tabs.attachments_tab import AttachmentsTab
from ui.tabs.expenses_tab import ExpensesTab
from ui.tabs.history_tab import HistoryTab
from ui.window_mode import lock_maximized

class ProjectOverviewWindow(QMainWindow):
    def __init__(
        self,
        project_id: int,
        projects_repo,
        tasks_repo,
        subtasks_repo,
        phases_repo,
        attachments_repo=None,
        expenses_repo=None,
        parent=None,
    ):
        super().__init__(parent)
        self._project_id = project_id
        self._projects_repo = projects_repo
        self._tasks_repo = tasks_repo
        self._subtasks_repo = subtasks_repo
        self._phases_repo = phases_repo

        # VM provides id/name/description + counts via 'loaded' dict
        self._vm = ProjectOverviewViewModel(projects_repo, tasks_repo, subtasks_repo)

        self.setMinimumSize(900, 560)
        self.resize(1100, 750)
        geo = QSettings().value("overview/geometry", None)
        if geo is not None:
            self.restoreGeometry(geo)

        # Tabs
        self._tabs = QTabWidget(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        self.setLayout(layout)
        self._tab_overview = OverviewTab(self._projects_repo, self._tasks_repo, self._subtasks_repo, self._phases_repo, self)
        self._tab_tasks = TasksTab(tasks_repo, phases_repo)
        self._tab_subtasks = SubtasksTab(subtasks_repo)
        self._tab_attachments = AttachmentsTab()
        self._tab_expenses = ExpensesTab()
        self._tab_history = HistoryTab()

        self._tabs.addTab(self._tab_overview, "Overview")
        self._tabs.addTab(self._tab_tasks, "Tasks")
        self._tabs.addTab(self._tab_subtasks, "Subtasks")
        self._tabs.addTab(self._tab_attachments, "Attachments")
        self._tabs.addTab(self._tab_expenses, "Expenses")
        self._tabs.addTab(self._tab_history, "History")

        # Keep a minimal header (blank) to preserve layout spacing if your stylesheet expects it.
        self._hdr = QLabel("")  # intentionally left empty; Overview tab owns content
        self._hdr.setObjectName("projectHeader")

        root = QWidget()
        lay = QVBoxLayout(root)
        lay.addWidget(self._hdr)
        lay.addWidget(self._tabs)
        self.setCentralWidget(root)
        
        lock_maximized(self, lock_resize=True) 

        # Wire VM
        self._vm.loaded.connect(self._on_loaded)

        # Initial load
        self.load(self._project_id)

    # ---------------- Public API ----------------
    def load(self, project_id: int):
        # VM will emit 'loaded' with the info dict; tabs get loaded below.
        self._vm.load(project_id)
        
        self._project_id = project_id
        self._tab_overview.load(project_id)

        # Load tab contents (lists)
        self._tab_tasks.load(project_id, phase_id=None)
        self._tab_subtasks.load(project_id)
        self._tab_history.load(project_id)        # scaffold
        self._tab_attachments.load(project_id)    # scaffold
        self._tab_expenses.load(project_id)       # scaffold

    # ---------------- Slots ----------------
    def _on_loaded(self, info: dict):
        """
        info schema from VM:
        {
            "id": int,
            "name": str,
            "description": str|None,
            "tasks_total": int,
            "subtasks_total": int,
            # attachments_total?, expenses_total? (future)
        }
        """
        # Window title only; Overview tab renders the details
        if info:
            pid = info.get("id")
            name = info.get("name") or ""
            self.setWindowTitle(f"{name} — Project {pid}")
        else:
            self.setWindowTitle("Project")

        # Send everything to Overview tab
        if hasattr(self._tab_overview, "set_info"):
            self._tab_overview.set_info(info or {"id": "—", "name": "Unknown Project", "description": ""})

        if hasattr(self._tab_overview, "set_counts"):
            self._tab_overview.set_counts({
                "tasks_total": int(info.get("tasks_total", 0)) if info else 0,
                "subtasks_total": int(info.get("subtasks_total", 0)) if info else 0,
                # attachments_total / expenses_total can be added later
            })

    # ---------------- Qt Overrides ----------------
    def closeEvent(self, e):
        QSettings().setValue("overview/geometry", self.saveGeometry())
        super().closeEvent(e)
