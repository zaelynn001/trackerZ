# trackerZ diagnostics panel
# Rev 0.1.0

from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton
import logging

class DiagnosticsPanel(QWidget):
    """Simple log viewer with manual refresh."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DiagnosticsPanel")

        layout = QVBoxLayout(self)
        self.text = QTextEdit(self)
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QTextEdit.NoWrap)

        self.btn_refresh = QPushButton("Tail Log", self)
        self.btn_refresh.clicked.connect(self.refresh)

        layout.addWidget(self.text)
        layout.addWidget(self.btn_refresh)

        self.refresh()

    def refresh(self):
        """Reload trackerZ log content into the panel."""
        logger = logging.getLogger("trackerZ")
        for h in logger.handlers:
            if hasattr(h, "baseFilename"):
                path = getattr(h, "baseFilename")
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        self.text.setPlainText(f.read())
                except Exception as e:
                    self.text.setPlainText(f"<error reading log>\\n{e}")
                break

