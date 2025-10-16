# Rev 0.6.5

"""Diagnostics panel dock (Rev 0.6.5)"""
from __future__ import annotations
from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QPushButton, QTextEdit
from PySide6.QtCore import Qt
from utils.logging_setup import LOG_FILE




class DiagnosticsPanel(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Diagnostics", parent)
        container = QWidget(self)
        layout = QVBoxLayout(container)


        self.text = QTextEdit(container)
        self.text.setReadOnly(True)


        self.btn_reload = QPushButton("Reload log", container)
        self.btn_reload.clicked.connect(self.reload)


        layout.addWidget(self.btn_reload)
        layout.addWidget(self.text)
        container.setLayout(layout)
        self.setWidget(container)
        self.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)


        self.reload()


    def reload(self):
        try:
            contents = LOG_FILE.read_text(encoding="utf-8") if LOG_FILE.exists() else "(no log yet)"
        except Exception as e:
            contents = f"Failed to read log: {e}"
        self.text.setPlainText(contents)
