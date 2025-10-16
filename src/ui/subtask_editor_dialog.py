# Rev 0.6.5 — Subtask Editor with Phase, Priority, Note
from __future__ import annotations
from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QComboBox, QLabel
)
from ui.window_mode import lock_dialog_fixed

_PHASE_NAMES = {1: "Open", 2: "In Progress", 3: "In Hiatus", 4: "Resolved", 5: "Closed"}
_PRIORITY_NAMES = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}


class SubtaskEditorDialog(QDialog):
    """
    Values returned (see values()):
      name: str
      description: str
      phase_id: int
      priority_id: int
      note: str
    """

    def __init__(
        self,
        parent=None,
        *,
        name: str = "",
        description: Optional[str] = None,
        phase_id: int = 1,
        priority_id: int = 2,
        title: str = "Subtask"
    ):
        super().__init__(parent)
        self.setWindowTitle(title)

        self._name = QLineEdit(name or "")
        self._desc = QTextEdit()
        if description:
            self._desc.setPlainText(description)

        self._cmb_phase = QComboBox()
        for pid, label in _PHASE_NAMES.items():
            self._cmb_phase.addItem(label, pid)
        i = self._cmb_phase.findData(phase_id or 1)
        if i >= 0:
            self._cmb_phase.setCurrentIndex(i)

        self._cmb_priority = QComboBox()
        for prio, label in _PRIORITY_NAMES.items():
            self._cmb_priority.addItem(label, prio)
        j = self._cmb_priority.findData(priority_id or 2)
        if j >= 0:
            self._cmb_priority.setCurrentIndex(j)

        self._note = QTextEdit()
        self._note.setPlaceholderText("Optional note (will be recorded in the subtask timeline)")

        form = QFormLayout()
        form.addRow("Name:", self._name)
        form.addRow("Description:", self._desc)
        form.addRow(QLabel("<hr/>"))
        form.addRow("Phase:", self._cmb_phase)
        form.addRow("Priority:", self._cmb_priority)
        form.addRow("Note:", self._note)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(btns)
        
        lock_dialog_fixed(self, width_ratio=0.5, height_ratio=0.6)

    def values(self) -> Tuple[str, str, int, int, str]:
        name = self._name.text().strip()
        desc = self._desc.toPlainText().strip()
        phase_id = int(self._cmb_phase.currentData())
        priority_id = int(self._cmb_priority.currentData())
        note = self._note.toPlainText().strip()
        return name, desc, phase_id, priority_id, note
