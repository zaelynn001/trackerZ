# src/ui/diagnostics_dock.py
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit, QLabel
from src.utils.logging_setup import init_logging

def _tail(path: Path, max_lines: int = 500) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return "".join(lines[-max_lines:])
    except FileNotFoundError:
        return "(log file not found)"
    except Exception as e:
        return f"(error reading log: {e})"

class DiagnosticsDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Diagnostics", parent)
        self.setObjectName("DiagnosticsDock")
        self.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable)

        self.log_file = init_logging()

        w = QWidget()
        lay = QVBoxLayout(w)
        top = QHBoxLayout()
        self.lbl = QLabel(f"Log: {self.log_file}")
        self.btn_refresh = QPushButton("Refresh")
        self.btn_autorefresh = QPushButton("Auto: On")
        self.btn_autorefresh.setCheckable(True)
        self.btn_autorefresh.setChecked(True)

        top.addWidget(self.lbl, 1)
        top.addWidget(self.btn_refresh)
        top.addWidget(self.btn_autorefresh)

        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)

        lay.addLayout(top)
        lay.addWidget(self.view, 1)
        self.setWidget(w)

        self.timer = QTimer(self)
        self.timer.setInterval(1500)
        self.timer.timeout.connect(self.reload)
        self.timer.start()

        self.btn_refresh.clicked.connect(self.reload)
        self.btn_autorefresh.clicked.connect(self._toggle_auto)

        self.reload()

    def _toggle_auto(self):
        if self.btn_autorefresh.isChecked():
            self.btn_autorefresh.setText("Auto: On")
            self.timer.start()
        else:
            self.btn_autorefresh.setText("Auto: Off")
            self.timer.stop()

    def reload(self):
        text = _tail(Path(self.log_file))
        self.view.setPlainText(text)
        self.view.moveCursor(QTextCursor.End)

