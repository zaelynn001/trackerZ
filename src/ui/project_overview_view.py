# src/ui/project_overview_view.py  Rev 0.1.1
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from ui.tasks_view import TasksView
from ui.subtasks_view import SubtasksView

class ProjectOverviewView(QWidget):
    taskEditRequested = Signal(int)     # task_id
    subtaskEditRequested = Signal(int)  # subtask_id
    def __init__(self, tasks_vm, parent=None):
        super().__init__(parent)
        self._tabs = QTabWidget(self)

        self.overview_tab  = QWidget()              # existing
        self.tasks_tab     = TasksView(tasks_vm)    # updated TasksView
        self.subtasks_tab  = SubtasksView(tasks_vm) # move here
        self.attach_tab    = QWidget()
        self.expenses_tab  = QWidget()
        self.history_tab   = QWidget()

        self._tabs.addTab(self.overview_tab, "Overview")
        self._tabs.addTab(self.tasks_tab,    "Tasks")
        self._tabs.addTab(self.subtasks_tab, "Subtasks")
        self._tabs.addTab(self.attach_tab,   "Attachments")
        self._tabs.addTab(self.expenses_tab, "Expenses")
        self._tabs.addTab(self.history_tab,  "History")

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)

        # react to task selection
        self.tasks_tab.taskEditRequested.connect(self.taskEditRequested.emit)
        self.subtasks_tab.subtaskEditRequested.connect(self.subtaskEditRequested.emit)

    def load_for_project(self, project_id: int):
        self._current_project_id = project_id
        self.tasks_tab.load_for_project(project_id)
        self.subtasks_tab.load_for_project(project_id) 


