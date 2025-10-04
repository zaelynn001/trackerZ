# src/ui/task_editor.py
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QComboBox,
    QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt
from src.models.dao import get_task, update_project_metadata, change_task_phase, allowed_phase_targets, get_all_phases
from src.models.db import tx
import logging

class TaskEditorDialog(QDialog):
    def __init__(self, task_id: int, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.setWindowTitle(f"Edit Task — #{task_id}")
        self.resize(600, 420)

        self.title_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.priority_edit = QLineEdit()
        self.phase_combo = QComboBox()

        form = QFormLayout()
        form.addRow("Title", self.title_edit)
        form.addRow("Description", self.desc_edit)
        form.addRow("Priority", self.priority_edit)
        form.addRow("Change Phase To", self.phase_combo)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, orientation=Qt.Horizontal)
        self.buttons.accepted.connect(self._on_save)
        self.buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(self.buttons)

        self._current_phase_id: Optional[int] = None
        self._load()

    def _load(self):
        t = get_task(self.task_id)
        if not t:
            QMessageBox.critical(self, "Not found", f"Task {self.task_id} not found.")
            self.reject()
            return
        self.title_edit.setText(t.get("title",""))
        self.desc_edit.setPlainText(t.get("description","") or "")
        self.priority_edit.setText(t.get("priority","") or "")
        self._current_phase_id = t.get("phase_id")

        # phase options
        self.phase_combo.clear()
        self.phase_combo.addItem("— No change —", self._current_phase_id)
        if self._current_phase_id:
            for row in allowed_phase_targets(self._current_phase_id):
                self.phase_combo.addItem(row["name"], row["id"])

    def _on_save(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Required", "Title is required.")
            return
        description = self.desc_edit.toPlainText().strip()
        priority = (self.priority_edit.text().strip() or None)

        # Save metadata
        with tx() as conn:
            row = conn.execute("SELECT 1 FROM tasks WHERE id = ?", (self.task_id,)).fetchone()
            if not row:
                QMessageBox.critical(self, "Error", "Task not found.")
                return
            conn.execute("""
                UPDATE tasks
                   SET title = ?, description = ?, priority = ?, updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
                 WHERE id = ?
            """, (title, description, priority, self.task_id))
        logging.info("Task %s metadata updated (title=%r, priority=%r)", self.task_id, title, priority)

        # Optional phase change
        new_phase_id = self.phase_combo.currentData()
        try:
            if self._current_phase_id and new_phase_id and new_phase_id != self._current_phase_id:
                change_task_phase(self.task_id, actor="local-user", new_phase_id=new_phase_id, note="")
        except Exception as e:
            QMessageBox.critical(self, "Phase change blocked", str(e))
            return

        self.accept()

