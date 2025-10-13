# Rev 0.5.1
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem


class TaskTimelinePanel(QWidget):
	"""Simple table view for task_updates; to be embedded/docked.
	Call set_updates(list[dict]) to refresh.
	"""
	def __init__(self, parent=None):
		super().__init__(parent)
		self._table = QTableWidget(0, 5)
		self._table.setHorizontalHeaderLabels(["When (UTC)", "Reason", "Note", "Old Phase", "New Phase"])
		lay = QVBoxLayout(self)
		lay.addWidget(self._table)


	def set_updates(self, updates):
		self._table.setRowCount(len(updates))
		for r, u in enumerate(updates):
			self._table.setItem(r, 0, QTableWidgetItem(str(u.get("created_at", ""))))
			self._table.setItem(r, 1, QTableWidgetItem(str(u.get("reason", ""))))
			self._table.setItem(r, 2, QTableWidgetItem(str(u.get("note", ""))))
			self._table.setItem(r, 3, QTableWidgetItem(str(u.get("old_phase_id", ""))))
			self._table.setItem(r, 4, QTableWidgetItem(str(u.get("new_phase_id", ""))))
		self._table.resizeColumnsToContents()
