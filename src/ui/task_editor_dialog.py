# src/ui/task_editor_dialog.py
# Rev 0.6.8 — Match SubtaskEditorDialog layout exactly; read-only Name/Desc on edit
from __future__ import annotations
from typing import Optional, Tuple

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QComboBox, QLabel, QWidget
)
from PySide6.QtCore import Qt
from ui.window_mode import lock_dialog_fixed

_PHASE_NAMES = {1: "Open", 2: "In Progress", 3: "In Hiatus", 4: "Resolved", 5: "Closed"}
_PRIORITY_NAMES = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}


class TaskEditorDialog(QDialog):
    """
    Values returned (see values()):
      name: str
      description: str
      phase_id: int
      priority_id: int
      note: str

    UI matches SubtaskEditorDialog (QFormLayout + horizontal rule + lock_dialog_fixed).
    Name/Description are read-only in edit mode.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        title: str = "Task",
        name: Optional[str] = None,
        description: Optional[str] = None,
        phase_id: int = 1,
        priority_id: int = 2,
        note: Optional[str] = None,
        mode: Optional[str] = None,  # "create" | "edit" | None (auto)
    ):
        super().__init__(parent)
        self.setWindowTitle(title)

        # Determine edit mode (read-only Name/Desc)
        self._is_edit = (mode and mode.lower() == "edit") or ("edit" in (title or "").lower())

        # --- fields
        self._name = QLineEdit((name or "").strip())
        self._name.setReadOnly(self._is_edit)

        self._desc = QTextEdit()
        self._desc.setAcceptRichText(False)
        self._desc.setPlainText((description or "").strip())
        self._desc.setReadOnly(self._is_edit)

        self._cmb_phase = QComboBox()
        for pid, label in _PHASE_NAMES.items():
            self._cmb_phase.addItem(label, pid)
        ix = self._cmb_phase.findData(phase_id or 1)
        if ix >= 0:
            self._cmb_phase.setCurrentIndex(ix)

        self._cmb_priority = QComboBox()
        for prio, label in _PRIORITY_NAMES.items():
            self._cmb_priority.addItem(label, prio)
        jx = self._cmb_priority.findData(priority_id or 2)
        if jx >= 0:
            self._cmb_priority.setCurrentIndex(jx)

        self._note = QTextEdit(note or "")
        self._note.setAcceptRichText(False)
        self._note.setPlaceholderText("Optional note (will be recorded in the task timeline)")

        # --- layout (mirror subtask editor)
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

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(btns)

        # Match your dialog sizing behavior
        lock_dialog_fixed(self, width_ratio=0.5, height_ratio=0.6)

        # Focus: first editable control
        (self._cmb_phase if self._is_edit else self._name).setFocus(Qt.OtherFocusReason)

    def values(self) -> Tuple[str, str, int, int, str]:
        name = self._name.text().strip()
        desc = self._desc.toPlainText().strip()
        phase_id = int(self._cmb_phase.currentData())
        priority_id = int(self._cmb_priority.currentData())
        note = self._note.toPlainText().strip()
        return name, desc, phase_id, priority_id, note
