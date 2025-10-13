# Rev 0.5.1 — M5 wiring for Task CRUD + Timeline
from __future__ import annotations


from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
	QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
	QHBoxLayout, QPushButton, QMessageBox
)


from viewmodels.tasks_viewmodel import TasksViewModel
from ui.task_editor_dialog import TaskEditorDialog
from ui.task_timeline_panel import TaskTimelinePanel




class TasksView(QWidget):
	"""Tasks tab view with CRUD + Timeline integration.
	Public API:
	- load_for_project(project_id: int, phase_id: int|None)
	- taskChosen(int): emitted on double-click (unchanged behavior)
	"""
	
	# Emitted when a user activates (double-clicks) a task row (kept for compatibility)
	taskChosen = Signal(int)
	
	def __init__(self, tasks_repo, parent=None):
		super().__init__(parent)
		self._vm = TasksViewModel(tasks_repo)
		self._project_id: int | None = None
		self._phase_id: int | None = None


# --- Controls ------------------------------------------------------
		self._btn_new = QPushButton("New Task")
		self._btn_edit = QPushButton("Edit")
		self._btn_delete = QPushButton("Delete")
		self._btn_history = QPushButton("History")


		self._btn_edit.setEnabled(False)
		self._btn_delete.setEnabled(False)
		self._btn_history.setEnabled(False)


		# Table
		self._table = QTableWidget(0, 3) # id, name, phase
		self._table.setHorizontalHeaderLabels(["ID", "Name", "Phase"])
		self._table.setEditTriggers(QTableWidget.NoEditTriggers)
		self._table.setSelectionBehavior(QTableWidget.SelectRows)
		self._table.setSelectionMode(QTableWidget.SingleSelection)
		self._table.itemDoubleClicked.connect(self._on_item_double_clicked)
		self._table.itemSelectionChanged.connect(self._on_selection_changed)


		hdr = self._table.horizontalHeader()
		hdr.setStretchLastSection(True)
		hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents) # ID snug
		hdr.setSectionResizeMode(1, QHeaderView.Stretch) # Name grows
		hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Phase snug


		vh = self._table.verticalHeader()
		vh.setVisible(False)
		vh.setDefaultSectionSize(22)
		vh.setMinimumSectionSize(18)
		self._table.setWordWrap(False)
		self._table.setAlternatingRowColors(True)
		self._table.setSizeAdjustPolicy(QTableWidget.AdjustToContentsOnFirstShow)

		# Timeline panel (can be shown/hidden by user)
		self._timeline = TaskTimelinePanel(self)
		self._timeline.setVisible(False)


		# Layouts
		top = QHBoxLayout()
		top.addWidget(self._btn_new)
		top.addWidget(self._btn_edit)
		top.addWidget(self._btn_delete)
		top.addWidget(self._btn_history)
		top.addStretch(1)


		lay = QVBoxLayout(self)
		lay.addLayout(top)
		lay.addWidget(self._table)
		lay.addWidget(self._timeline)


		# Wire buttons
		self._btn_new.clicked.connect(self._on_new_clicked)
		self._btn_edit.clicked.connect(self._on_edit_clicked)
		self._btn_delete.clicked.connect(self._on_delete_clicked)
		self._btn_history.clicked.connect(self._on_history_clicked)


		# Connect VM signals
		self._vm.tasksReloaded.connect(self._on_tasks_reloaded)
		self._vm.timelineLoaded.connect(self._on_timeline_loaded)


	# ---------------- Public API ----------------
	def load_for_project(self, project_id: int, phase_id: int | None):
		self._project_id = project_id
		self._phase_id = phase_id
		self._vm.set_filters(project_id, phase_id)
		self._vm.reload()
		
		# ---------------- Internals -----------------
	def _on_tasks_reloaded(self, total: int, rows: list[dict]):
		# Optional: show counts in a status bar
		# w = self.window(); getattr(w, 'statusBar', lambda: None)() ...
		self._render(rows)
		
	def _render(self, rows: list[dict]):
		self._table.setRowCount(len(rows))
		for r, row in enumerate(rows):
			tid = row.get("id") or row.get("task_id")
			name = row.get("name") or row.get("title") or ""
			phase_name = row.get("phase_name") or row.get("phase") or ""
			
			id_item = QTableWidgetItem(str(tid) if tid is not None else "")
			name_item = QTableWidgetItem(name)
			phase_item = QTableWidgetItem(phase_name)
			
			id_item.setData(Qt.UserRole, tid)
			name_item.setData(Qt.UserRole, tid)
			phase_item.setData(Qt.UserRole, tid)
			
			self._table.setItem(r, 0, id_item)
			self._table.setItem(r, 1, name_item)
			self._table.setItem(r, 2, phase_item)
			
			self._table.resizeColumnsToContents()
			self._on_selection_changed()
			
	def _on_item_double_clicked(self, item: QTableWidgetItem):
		if not item:
			return
		tid = item.data(Qt.UserRole)
		if tid is None:
			try:
				tid = int(self._table.item(item.row(), 0).text())
			except Exception:
				return
		self.taskChosen.emit(int(tid))
		
	def _selected_task_id(self) -> int | None:
		items = self._table.selectedItems()
		if not items:
			return None
		# any item in the row has the id in UserRole
		tid = items[0].data(Qt.UserRole)
		if tid is None:
			try:
				tid = int(self._table.item(items[0].row(), 0).text())
			except Exception:
				return None
		return int(tid)
		
	def _on_selection_changed(self):
		has_sel = self._selected_task_id() is not None
		self._btn_edit.setEnabled(has_sel)
		self._btn_delete.setEnabled(has_sel)
		self._btn_history.setEnabled(has_sel)
		
	# --------------- Button handlers ---------------
	
	def _on_new_clicked(self):
		if self._project_id is None:
			return
		dlg = TaskEditorDialog(self)
		if dlg.exec() == dlg.Accepted:
			name, desc = dlg.values()
		if not name:
			QMessageBox.warning(self, "Missing name", "Please provide a task name.")
			return
			# default to phase 1 (Open) unless you expose a chooser
		self._vm.create_task(self._project_id, name, desc, 1)
		
	def _on_edit_clicked(self):
		tid = self._selected_task_id()
		if tid is None:
			return
		# For now, fetch current row values from the table (keeps repo API small)
		row = self._table.currentRow()
		cur_name = self._table.item(row, 1).text() if row >= 0 else ""
		dlg = TaskEditorDialog(self, name=cur_name, description="")
		if dlg.exec() == dlg.Accepted:
			name, desc = dlg.values()
			if not name:
				QMessageBox.warning(self, "Missing name", "Please provide a task name.")
				return
			self._vm.edit_task(tid, name, desc)
			
	def _on_delete_clicked(self):
		tid = self._selected_task_id()
		if tid is None:
			return
		if QMessageBox.question(
			self,
			"Delete Task",
			f"Are you sure you want to delete task #{tid}?",
			QMessageBox.Yes | QMessageBox.No,
		) == QMessageBox.Yes:
			self._vm.delete_task(tid)
			# Hide timeline if it was showing this task
			self._timeline.setVisible(False)
		
	def _on_history_clicked(self):
		tid = self._selected_task_id()
		if tid is None:
			return
		self._vm.load_timeline(tid)
		
	def _on_timeline_loaded(self, task_id: int, updates: list[dict]):
		# Show and populate the timeline panel
		self._timeline.setVisible(True)
		self._timeline.set_updates(updates)
