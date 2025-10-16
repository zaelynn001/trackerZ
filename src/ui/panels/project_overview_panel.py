# Rev 0.0.1

# ============================================
# File: src/ui/panels/project_overview_panel.py
# ============================================
from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget


# Reuse your existing tabs directly
from ui.tabs.overview_tab import OverviewTab
from ui.tabs.tasks_tab import TasksTab
from ui.tabs.subtasks_tab import SubtasksTab
from ui.tabs.attachments_tab import AttachmentsTab
from ui.tabs.expenses_tab import ExpensesTab
from ui.tabs.history_tab import HistoryTab


class ProjectOverviewPanel(QWidget):
	"""Embed your existing Overview/Tasks/Subtasks/... tabs in a QWidget
	so they can live inside the stacked workspace instead of a separate window."""
	def __init__(
		self,
		*,
		project_id: Optional[int] = None,
		projects_repo=None,
		tasks_repo=None,
		subtasks_repo=None,
		phases_repo=None,
		attachments_repo=None,
		expenses_repo=None,
		parent: Optional[QWidget] = None,
	) -> None:
		super().__init__(parent)
		self._project_id = project_id
		self._repos = dict(
			projects=projects_repo, tasks=tasks_repo, subtasks=subtasks_repo, phases=phases_repo,
			attachments=attachments_repo, expenses=expenses_repo
		)
		self._tabs = QTabWidget(self)
		lay = QVBoxLayout(self)
		lay.setContentsMargins(0,0,0,0)
		lay.addWidget(self._tabs)


		# Instantiate tabs using the same constructor style as your ProjectOverviewWindow
		self._tab_overview = OverviewTab(projects_repo, tasks_repo, subtasks_repo, phases_repo, self)
		self._tab_tasks = TasksTab(tasks_repo, phases_repo, self)
		self._tab_subtasks = SubtasksTab(subtasks_repo, phases_repo, self)
		self._tab_attachments = AttachmentsTab(attachments_repo, self)
		self._tab_expenses = ExpensesTab(expenses_repo, self)
		self._tab_history = HistoryTab(self)


		self._tabs.addTab(self._tab_overview, "Overview")
		self._tabs.addTab(self._tab_tasks, "Tasks")
		self._tabs.addTab(self._tab_subtasks, "Subtasks")
		self._tabs.addTab(self._tab_attachments, "Attachments")
		self._tabs.addTab(self._tab_expenses, "Expenses")
		self._tabs.addTab(self._tab_history, "History")
		
	def load(self, project_id: int) -> None:
		self._project_id = project_id
		# Call each tab's load, mirroring ProjectOverviewWindow.load
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
