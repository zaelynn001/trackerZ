# Rev 0.5.1
# trackerZ – ProjectOverviewWindow (Rev 0.5.1)
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel, QHBoxLayout
from viewmodels.project_overview_viewmodel import ProjectOverviewViewModel
from ui.tabs.overview_tab import OverviewTab
from ui.tabs.tasks_tab import TasksTab
from ui.tabs.subtasks_tab import SubtasksTab
from ui.tabs.attachments_tab import AttachmentsTab
from ui.tabs.expenses_tab import ExpensesTab
from ui.tabs.history_tab import HistoryTab

class ProjectOverviewWindow(QMainWindow):
    def __init__(self, project_id:int, projects_repo, tasks_repo, subtasks_repo, phases_repo, attachments_repo=None, expenses_repo=None, parent=None):
        super().__init__(parent)
        self._project_id = project_id
        self._vm = ProjectOverviewViewModel(projects_repo, tasks_repo, subtasks_repo, attachments_repo, expenses_repo)
        
        self.setMinimumSize(900, 560)
        self.resize(1100, 750)
        geo = QSettings().value("overview/geometry", None)
        if geo is not None:
            self.restoreGeometry(geo)

        self._tabs = QTabWidget()
        self._tab_overview = OverviewTab()
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

        hdr = QLabel("")
        hdr.setObjectName("projectHeader")

        root = QWidget()
        lay = QVBoxLayout(root)
        lay.addWidget(hdr)
        lay.addWidget(self._tabs)
        self.setCentralWidget(root)

        self._hdr = hdr
        self.load(self._project_id)

    def load(self, project_id:int):
        self._vm.load(project_id)
        self.setWindowTitle(self._vm.project_name() or f"Project {project_id}")
        self._hdr.setText(f"<h2>{self._vm.project_name()}</h2>")

        counts = self._vm.counts()
        self._tab_overview.set_counts(counts)

        self._tab_tasks.load(project_id, phase_id=None)
        self._tab_subtasks.load(project_id)
        self._tab_history.load(project_id)        # scaffold
        self._tab_attachments.load(project_id)    # scaffold
        self._tab_expenses.load(project_id)       # scaffold
        
    def closeEvent(self, e):
        QSettings().setValue("overview/geometry", self.saveGeometry())
        super().closeEvent(e)

