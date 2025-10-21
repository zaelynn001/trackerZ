# Rev 0.6.8
# trackerZ – TasksTab (Rev 0.6.8)
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from ui.tasks_view import TasksView

class TasksTab(QWidget):
    def __init__(self, tasks_repo, phases_repo, parent=None):
        super().__init__(parent)
        self._repo = tasks_repo
        self._phases = phases_repo
        self._project_id = None

        self._filter = QComboBox()
        self._filter.addItem("All phases", userData=None)
        for p in self._phases.list_phases():
            self._filter.addItem(p["name"], userData=p["id"])

        self._view = TasksView(tasks_repo)
        self._filter.currentIndexChanged.connect(self._on_phase_changed)

        top = QHBoxLayout()
        top.addWidget(QLabel("Phase:"))
        top.addWidget(self._filter)
        top.addStretch(1)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self._view)

    def load(self, project_id:int, phase_id=None):
        self._project_id = project_id
        if phase_id is not None:
            idx = max(0, self._filter.findData(phase_id))
            self._filter.setCurrentIndex(idx)
        self._reload()

    def _on_phase_changed(self, _=None):
        self._reload()

    def _reload(self):
        phase_id = self._filter.currentData()
        self._view.load_for_project(self._project_id, phase_id)



