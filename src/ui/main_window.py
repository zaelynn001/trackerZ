# src/ui/main_window.py
# Rev 0.1.1
from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QMainWindow, QWidget, QStackedWidget, QVBoxLayout, QDockWidget, QPushButton, QHBoxLayout

import logging

try:
    from ui.diagnostics_panel import DiagnosticsPanel
except Exception:
    DiagnosticsPanel = None

from ui.project_picker_view import ProjectPickerView
from ui.project_overview_view import ProjectOverviewView

class MainWindow(QMainWindow):
    projectSelected = Signal(int)  # project_id

    def __init__(self, projects_vm, tasks_vm, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("trackerZ")

        self._stack = QStackedWidget()
        self._picker = ProjectPickerView(projects_vm)
        self._overview = ProjectOverviewView(tasks_vm)
        self._overview.taskEditRequested.connect(self._open_task_editor)
        self._overview.subtaskEditRequested.connect(self._open_subtask_editor)

        # Top bar with Back
        top = QWidget()
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(8, 8, 8, 8)
        self._back = QPushButton("Back")
        self._back.clicked.connect(self._show_picker)
        top_lay.addWidget(self._back)
        top_lay.addStretch()

        center = QWidget()
        center_lay = QVBoxLayout(center)
        center_lay.setContentsMargins(8, 0, 8, 8)
        center_lay.addWidget(self._stack)

        wrapper = QWidget()
        wrap_lay = QVBoxLayout(wrapper)
        wrap_lay.setContentsMargins(0, 0, 0, 0)
        wrap_lay.addWidget(top)
        wrap_lay.addWidget(center)
        self.setCentralWidget(wrapper)

        self._stack.addWidget(self._picker)    # 0
        self._stack.addWidget(self._overview)  # 1
        self._stack.setCurrentWidget(self._picker)

        self._picker.projectChosen.connect(self._on_project_chosen)

        if DiagnosticsPanel:
            dock = QDockWidget("Diagnostics", self)
            dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
            dock.setWidget(DiagnosticsPanel())
            self.addDockWidget(Qt.BottomDockWidgetArea, dock)

    def _on_project_chosen(self, project_id: int):
        self.projectSelected.emit(project_id)
        self._overview.load_for_project(project_id)
        self._stack.setCurrentWidget(self._overview)

    def _show_picker(self):
        self._stack.setCurrentWidget(self._picker)
        
    def _open_task_editor(self, task_id: int):
        # TODO: replace with real editor
        logging.getLogger("trackerZ").info(f"Edit Task requested: {task_id}")

    def _open_subtask_editor(self, subtask_id: int):
        # TODO: replace with real editor
        logging.getLogger("trackerZ").info(f"Edit Subtask requested: {subtask_id}")

