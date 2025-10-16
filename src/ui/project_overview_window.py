# Rev 0.6.5
# Rev 0.7.0 — Overview: proper maximize, no geometry persistence, no setLayout on QMainWindow
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel

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

        # ViewModel
        self._vm = ProjectOverviewViewModel(projects_repo, tasks_repo, subtasks_repo)

        # ---- Central widget (QMainWindow must use a central widget; do NOT call setLayout on self) ----
        self._tabs = QTabWidget(self)
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

        self._hdr = QLabel("")              # reserved header (keeps spacing if your stylesheet expects it)
        self._hdr.setObjectName("projectHeader")

        root = QWidget(self)
        lay = QVBoxLayout(root)
        lay.addWidget(self._hdr)
        lay.addWidget(self._tabs)
        self.setCentralWidget(root)

        # Defer maximize so it wins over any initial sizing or WM geometry
        QTimer.singleShot(0, lambda: lock_maximized(self, lock_resize=True))

        # Wire VM
        self._vm.loaded.connect(self._on_loaded)

        # Initial load
        self.load(self._project_id)

    # ---------------- Public API ----------------
    def load(self, project_id: int):
        self._project_id = project_id
        self._vm.load(project_id)

        self._tab_overview.load(project_id)
        self._tab_tasks.load(project_id, phase_id=None)
        self._tab_subtasks.load(project_id)
        self._tab_history.load(project_id)        # scaffold
        self._tab_attachments.load(project_id)    # scaffold
        self._tab_expenses.load(project_id)       # scaffold

    # ---------------- Slots ----------------
    def _on_loaded(self, info: dict):
        # Window title only; Overview tab renders the details
        if info:
            pid = info.get("id")
            name = info.get("name") or ""
            self.setWindowTitle(f"{name} — Project {pid}")
        else:
            self.setWindowTitle("Project")

        if hasattr(self._tab_overview, "set_info"):
            self._tab_overview.set_info(info or {"id": "—", "name": "Unknown Project", "description": ""})

        if hasattr(self._tab_overview, "set_counts"):
            self._tab_overview.set_counts({
                "tasks_total": int(info.get("tasks_total", 0)) if info else 0,
                "subtasks_total": int(info.get("subtasks_total", 0)) if info else 0,
            })

    # ---------------- Qt Overrides ----------------
    # No geometry persistence; maximize lock controls size.
    # Keep save/restore for splitters/headers elsewhere if you use them.


    # ---------------- Qt Overrides ----------------
    def closeEvent(self, e):
        QSettings().setValue("overview/geometry", self.saveGeometry())
        super().closeEvent(e)
