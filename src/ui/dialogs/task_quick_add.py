# Rev 0.1.1

# src/ui/dialogs/task_quick_add.py  
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QTextEdit, QDialogButtonBox

class TaskQuickAdd(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Task")
        self.name = QLineEdit(self);  self.name.setPlaceholderText("Task name")
        self.note = QTextEdit(self);  self.note.setPlaceholderText("Note (optional)")
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(self.name); lay.addWidget(self.note); lay.addWidget(btns)

    def values(self) -> tuple[str, str | None]:
        n = self.name.text().strip()
        return n, (self.note.toPlainText().strip() or None)

