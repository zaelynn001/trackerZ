# trackerZ main window
# Rev 0.0.1

from __future__ import annotations
from PySide6.QtWidgets import QMainWindow, QWidget, QLabel, QDockWidget
from PySide6.QtCore import Qt
from .diagnostics_panel import DiagnosticsPanel

class MainWindow(QMainWindow):
    """App shell with a detachable diagnostics dock."""
    def __init__(self, app_ctx, parent=None):
        super().__init__(parent)
        self._ctx = app_ctx

        self.setWindowTitle("trackerZ")
        self.resize(1000, 700)

        # Center placeholder
        center = QWidget(self)
        self.setCentralWidget(center)
        lbl = QLabel("trackerZ — A01→M03 baseline", center)
        lbl.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(lbl)

        # Diagnostics dock
        self.dock = QDockWidget("Diagnostics", self)
        self.dock.setObjectName("DiagnosticsDock")
        self.dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.RightDockWidgetArea)
        self.dock.setWidget(DiagnosticsPanel(self))
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock)

