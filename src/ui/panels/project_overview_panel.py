# Rev 0.6.8 — M6.5 ProjectOverviewPanel (aligned to Rev 0.6.5 tabs)
from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

# Reuse existing tabs from your codebase
from ui.tabs.overview_tab import OverviewTab
from ui.tabs.tasks_tab import TasksTab
from ui.tabs.subtasks_tab import SubtasksTab
from ui.tabs.attachments_tab import AttachmentsTab
from ui.tabs.expenses_tab import ExpensesTab
from ui.tabs.history_tab import HistoryTab

class ProjectOverviewPanel(QWidget):
    """
    Embed your Overview/Tasks/Subtasks/Attachments/Expenses/History tabs
    inside a QWidget so the whole overview can live in the WorkspaceStack.
    """

    def __init__(
        self,
        *,
        project_id: Optional[int] = None,
        projects_repo=None,
        tasks_repo=None,
        subtasks_repo=None,
        phases_repo=None,
        attachments_repo=None,   # present for future use; not required by current tab ctor
        expenses_repo=None,      # present for future use; not required by current tab ctor
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._project_id = project_id
        self._projects_repo = projects_repo
        self._tasks_repo = tasks_repo
        self._subtasks_repo = subtasks_repo
        self._phases_repo = phases_repo

        self._tabs = QTabWidget(self)
        self._tabs.setTabPosition(QTabWidget.North)     # keep tabs visible at top
        self._tabs.setDocumentMode(False)               # classic tabs, easier to see
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._tabs)

        # Constructor signatures from your Rev 0.6.8 tabs:
        OverviewTab(projects_repo, tasks_repo, subtasks_repo, phases_repo, parent=None)
        TasksTab(tasks_repo, phases_repo, parent=None)
        # - SubtasksTab(subtasks_repo, parent=None)
        # - AttachmentsTab(parent=None)
        # - ExpensesTab(parent=None)
        # - HistoryTab(parent=None)

        self._tab_overview = OverviewTab(self._projects_repo, self._tasks_repo, self._subtasks_repo, self._phases_repo, self)
        self._tab_tasks = TasksTab(self._tasks_repo, self._phases_repo, self)
        self._tab_subtasks = SubtasksTab(self._subtasks_repo, self)
        self._tab_attachments = AttachmentsTab(self)
        self._tab_expenses = ExpensesTab(self)
        self._tab_history = HistoryTab(self)

        self._tabs.addTab(self._tab_overview, "Overview")
        self._tabs.addTab(self._tab_tasks, "Tasks")
        self._tabs.addTab(self._tab_subtasks, "Subtasks")
        self._tabs.addTab(self._tab_attachments, "Attachments")
        self._tabs.addTab(self._tab_expenses, "Expenses")
        self._tabs.addTab(self._tab_history, "History")
        
    def select_tab(self, key: str) -> None:
        """Select a tab by semantic key."""
        mapping = {
            "overview":   self._tab_overview,
            "tasks":      self._tab_tasks,
            "subtasks":   self._tab_subtasks,
            "attachments": self._tab_attachments,
            "expenses":    self._tab_expenses,
            "history":     self._tab_history,
        }
        widget = mapping.get(key)
        if widget is None:
            return
        idx = self._tabs.indexOf(widget)
        if idx >= 0:
            self._tabs.setCurrentIndex(idx)

    def load(self, project_id: int) -> None:
        self._project_id = project_id
        self.select_tab("overview")
        # Mirror your ProjectOverviewWindow.load() behavior
        idx = self._tabs.indexOf(self._tab_overview)
        if idx >= 0:
            self._tabs.setCurrentIndex(idx)
        if hasattr(self._tab_overview, "load"):
            self._tab_overview.load(project_id)
        if hasattr(self._tab_tasks, "load"):
            self._tab_tasks.load(project_id)
        if hasattr(self._tab_subtasks, "load"):
            self._tab_subtasks.load(project_id)
        if hasattr(self._tab_attachments, "load"):
            self._tab_attachments.load(project_id)
        if hasattr(self._tab_expenses, "load"):
            self._tab_expenses.load(project_id)
        if hasattr(self._tab_history, "load"):
            self._tab_history.load(project_id)
