# Rev 0.6.5 — Project Update Editor
from __future__ import annotations
from typing import Optional, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QTextEdit,
    QDialogButtonBox, QLabel, QMessageBox
)
from ui.window_mode import lock_dialog_fixed

_PHASE_NAMES = {1: "Open", 2: "In Progress", 3: "In Hiatus", 4: "Resolved", 5: "Closed"}
_PRIORITY_NAMES = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}


class ProjectEditorDialog(QDialog):
    def __init__(self, *, project_id: int, projects_repo, phases_repo=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Project #{project_id}")
        self._project_id = project_id
        self._projects = projects_repo
        self._phases = phases_repo

        self._cmb_phase = QComboBox()
        self._cmb_priority = QComboBox()
        self._txt_note = QTextEdit()
        self._lbl_current = QLabel("-")

        self._populate_phase_items()
        self._populate_priority_items()
        self._load_current_values()

        form = QFormLayout()
        form.addRow("Current:", self._lbl_current)
        form.addRow("Phase:", self._cmb_phase)
        form.addRow("Priority:", self._cmb_priority)
        form.addRow("Note (optional):", self._txt_note)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._apply)
        btns.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(btns)
        lock_dialog_fixed(self, width_ratio=0.5, height_ratio=0.6)

    # ----- data -----
    def _load_current_values(self):
        rec: Optional[Dict] = self._projects.get_project(self._project_id)
        if not rec:
            self._lbl_current.setText("Project not found")
            return
        phase_id = int(rec.get("phase_id", 1))
        prio_id = int(rec.get("priority_id", 2))
        self._lbl_current.setText(f"Phase: {_PHASE_NAMES.get(phase_id, phase_id)} | "
                                  f"Priority: {_PRIORITY_NAMES.get(prio_id, prio_id)}")

        i = self._cmb_phase.findData(phase_id)
        if i >= 0:
            self._cmb_phase.setCurrentIndex(i)
        j = self._cmb_priority.findData(prio_id)
        if j >= 0:
            self._cmb_priority.setCurrentIndex(j)

    def _populate_phase_items(self):
        # prefer phases_repo list, fallback to constants
        items = []
        try:
            if self._phases:
                for p in self._phases.list_phases():
                    items.append((p["name"], int(p["id"])))
        except Exception:
            pass
        if not items:
            items = [(name, pid) for pid, name in _PHASE_NAMES.items()]
        for name, pid in items:
            self._cmb_phase.addItem(name, pid)

    def _populate_priority_items(self):
        for pid, name in _PRIORITY_NAMES.items():
            self._cmb_priority.addItem(name, pid)

    # ----- actions -----
    def _apply(self):
        new_phase = int(self._cmb_phase.currentData())
        new_prio = int(self._cmb_priority.currentData())
        note = self._txt_note.toPlainText().strip() or None

        # get current to detect changes
        rec = self._projects.get_project(self._project_id)
        if not rec:
            QMessageBox.warning(self, "Update failed", "Project not found.")
            return
        old_phase = int(rec.get("phase_id", 1))
        old_prio = int(rec.get("priority_id", 2))

        changed = False

        # phase change first (validates via phase_transitions)
        if new_phase != old_phase:
            ok = False
            try:
                ok = self._projects.set_project_phase(self._project_id, new_phase, note=note or "Changed via editor")
            except Exception:
                ok = False
            if not ok:
                QMessageBox.warning(self, "Phase change blocked",
                                    "That phase change is not allowed by the configured transitions.")
                return
            changed = True

        # priority change
        if new_prio != old_prio:
            ok = False
            try:
                ok = self._projects.set_project_priority(self._project_id, new_prio, note=note or "Changed via editor")
            except Exception:
                ok = False
            if not ok:
                QMessageBox.warning(self, "Priority update failed", "Could not update project priority.")
                return
            changed = True

        if not changed and note:
            # Log a note-only update (fills all NOT NULL fields)
            try:
                self._projects.add_project_note(self._project_id, note=note)
                changed = True
            except Exception:
                pass

        if changed:
            self.accept()
        else:
            # nothing changed
            self.reject()
