# src/ui/project_editor_dialog.py
# Rev 0.6.8 — Match Task/Subtask editor layout; read-only Name/Description; same behavior
from __future__ import annotations
from typing import Optional, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QTextEdit,
    QDialogButtonBox, QLabel, QMessageBox, QLineEdit, QWidget
)
from ui.window_mode import lock_dialog_fixed

_PHASE_NAMES = {1: "Open", 2: "In Progress", 3: "In Hiatus", 4: "Resolved", 5: "Closed"}
_PRIORITY_NAMES = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}


class ProjectEditorDialog(QDialog):
    """
    Matches the visual/UX of Task/Subtask editors:
      Name (read-only), Description (read-only), <hr/>, Phase, Priority, Note, OK/Cancel.

    Behavior is unchanged: this dialog still applies updates via projects_repo in _apply().
    """

    def __init__(self, *, project_id: int, projects_repo, phases_repo=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Project #{project_id}")
        self._project_id = project_id
        self._projects = projects_repo
        self._phases = phases_repo

        # ---- Controls ----
        # Read-only project identity (to match other editors)
        self._name = QLineEdit()
        self._name.setReadOnly(True)

        self._desc = QTextEdit()
        self._desc.setAcceptRichText(False)
        self._desc.setReadOnly(True)

        # Editable fields
        self._cmb_phase = QComboBox()
        self._cmb_priority = QComboBox()
        self._txt_note = QTextEdit()
        self._txt_note.setAcceptRichText(False)
        self._txt_note.setPlaceholderText("Optional note (will be recorded in the project timeline)")

        # Populate combos
        self._populate_phase_items()
        self._populate_priority_items()

        # Load current DB values (fills name/desc + selects combos)
        self._load_current_values()

        # ---- Layout (match Task/Subtask editors) ----
        form = QFormLayout()
        form.addRow("Name:", self._name)
        form.addRow("Description:", self._desc)
        form.addRow(QLabel("<hr/>"))
        form.addRow("Phase:", self._cmb_phase)
        form.addRow("Priority:", self._cmb_priority)
        form.addRow("Note:", self._txt_note)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._apply)
        btns.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(btns)

        lock_dialog_fixed(self, width_ratio=0.5, height_ratio=0.6)

    # ----- data -----
    def _load_current_values(self):
        rec: Optional[Dict] = None
        try:
            rec = self._projects.get_project(self._project_id)
        except Exception:
            rec = None

        if not rec:
            # Graceful fallback
            self._name.setText("(project not found)")
            self._desc.setPlainText("")
            return

        # Read-only identity
        self._name.setText(str(rec.get("name") or ""))
        self._desc.setPlainText(str(rec.get("description") or ""))

        # Preselect combos to current values
        phase_id = int(rec.get("phase_id", 1))
        prio_id = int(rec.get("priority_id", 2))

        i = self._cmb_phase.findData(phase_id)
        if i >= 0:
            self._cmb_phase.setCurrentIndex(i)

        j = self._cmb_priority.findData(prio_id)
        if j >= 0:
            self._cmb_priority.setCurrentIndex(j)

    def _populate_phase_items(self):
        # Prefer dynamic list from phases_repo; fallback to constants
        items: list[tuple[str, int]] = []
        try:
            if self._phases:
                for p in self._phases.list_phases():
                    items.append((p["name"], int(p["id"])))
        except Exception:
            items = []
        if not items:
            items = [(name, pid) for pid, name in _PHASE_NAMES.items()]

        self._cmb_phase.clear()
        for name, pid in items:
            self._cmb_phase.addItem(name, pid)

    def _populate_priority_items(self):
        self._cmb_priority.clear()
        for pid, name in _PRIORITY_NAMES.items():
            self._cmb_priority.addItem(name, pid)

    # ----- actions -----
    def _apply(self):
        # New selections
        new_phase = int(self._cmb_phase.currentData())
        new_prio = int(self._cmb_priority.currentData())
        note = (self._txt_note.toPlainText().strip() or None)

        # Load current to detect actual changes
        rec = self._projects.get_project(self._project_id)
        if not rec:
            QMessageBox.warning(self, "Update failed", "Project not found.")
            return

        old_phase = int(rec.get("phase_id", 1))
        old_prio = int(rec.get("priority_id", 2))

        changed = False

        # Phase change first (so transitions are validated)
        if new_phase != old_phase:
            ok = False
            try:
                ok = self._projects.set_project_phase(
                    self._project_id,
                    new_phase,
                    note=note or "Changed via editor",
                )
            except Exception:
                ok = False
            if not ok:
                QMessageBox.warning(
                    self,
                    "Phase change blocked",
                    "That phase change is not allowed by the configured transitions.",
                )
                return
            changed = True

        # Priority change
        if new_prio != old_prio:
            ok = False
            try:
                ok = self._projects.set_project_priority(
                    self._project_id,
                    new_prio,
                    note=note or "Changed via editor",
                )
            except Exception:
                ok = False
            if not ok:
                QMessageBox.warning(self, "Priority update failed", "Could not update project priority.")
                return
            changed = True

        # Note-only entry (no field changes)
        if not changed and note:
            try:
                self._projects.add_project_note(self._project_id, note=note)
                changed = True
            except Exception:
                pass

        if changed:
            self.accept()
        else:
            self.reject()
