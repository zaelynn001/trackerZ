# src/ui/project_editor.py
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QComboBox,
    QDialogButtonBox, QMessageBox, QLabel
)
from PySide6.QtCore import Qt
from src.models.dao import get_project, update_project_metadata, allowed_phase_targets, change_project_phase, get_all_phases

class ProjectEditorDialog(QDialog):
    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Project — #{project_id}")
        self.resize(640, 420)
        self.project_id = project_id

        self.title_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.priority_edit = QLineEdit()

        self.phase_current_label = QLabel("")
        self.phase_combo = QComboBox()
        self.phase_combo.setEditable(False)

        form = QFormLayout()
        form.addRow("Title", self.title_edit)
        form.addRow("Description", self.desc_edit)
        form.addRow("Priority", self.priority_edit)
        form.addRow("Current Phase", self.phase_current_label)
        form.addRow("Change Phase To", self.phase_combo)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, orientation=Qt.Horizontal)
        self.buttons.accepted.connect(self._on_save)
        self.buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(self.buttons)

        self._current_phase_id: Optional[int] = None
        self._load_project()

    def _load_project(self):
        pr = get_project(self.project_id)
        if not pr:
            QMessageBox.critical(self, "Not found", f"Project {self.project_id} was not found.")
            self.reject()
            return

        self.title_edit.setText(pr.get("title", ""))
        self.desc_edit.setPlainText(pr.get("description", "") or "")
        self.priority_edit.setText(pr.get("priority", "") or "")

        self._current_phase_id = pr.get("phase_id") or pr.get("phase")
        # `get_project` returns phase_name; we also need phase_id, get it from all phases:
        all_phases = get_all_phases()
        name_by_id = {p["id"]: p["name"] for p in all_phases}
        id_by_name = {p["name"]: p["id"] for p in all_phases}

        # derive current id/name
        if isinstance(self._current_phase_id, int):
            current_name = name_by_id.get(self._current_phase_id, pr.get("phase_name", ""))
        else:
            current_name = pr.get("phase_name", "")
            self._current_phase_id = id_by_name.get(current_name)

        self.phase_current_label.setText(current_name or "(unknown)")

        # Allowed targets from current
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

        # First save metadata
        try:
            update_project_metadata(self.project_id, title, description, priority)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save metadata:\n{e}")
            return

        # Then apply (optional) phase change
        new_phase_id = self.phase_combo.currentData()
        note = ""  # could wire a note field later
        try:
            # Only try change if different from current
            if self._current_phase_id and new_phase_id and new_phase_id != self._current_phase_id:
                change_project_phase(self.project_id, actor="local-user", new_phase_id=new_phase_id, note=note)
        except Exception as e:
            QMessageBox.critical(self, "Phase change blocked", str(e))
            return

        self.accept()

