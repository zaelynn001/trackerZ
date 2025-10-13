# Rev 0.5.1
from __future__ import annotations
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QTextEdit, QDialogButtonBox


class TaskEditorDialog(QDialog):
	"""Minimal editor for creating/editing a task.
	Integrate with TasksViewModel externally.
	"""
	def __init__(self, parent=None, *, name: str = "", description: str = ""):
		super().__init__(parent)
		self.setWindowTitle("Task Editor")
		self._name = QLineEdit(name)
		self._desc = QTextEdit()
		self._desc.setPlainText(description)
		btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		btns.accepted.connect(self.accept)
		btns.rejected.connect(self.reject)
		lay = QVBoxLayout(self)
		lay.addWidget(self._name)
		lay.addWidget(self._desc)
		lay.addWidget(btns)
	

	def values(self) -> tuple[str, str]:
		return self._name.text().strip(), self._desc.toPlainText().strip()
