# Rev 0.4.1
# trackerZ – SubtasksTab (Rev 0.4.1)
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget, QTableWidgetItem

class SubtasksTab(QWidget):
    def __init__(self, subtasks_repo, parent=None):
        super().__init__(parent)
        self._repo = subtasks_repo
        self._project_id = None
        self._all_rows = []

        self._task_filter = QComboBox()
        self._task_filter.addItem("All tasks", userData=None)
        self._task_filter.currentIndexChanged.connect(self._apply_filter)

        self._table = QTableWidget(0, 4)  # id, task_id, name, phase
        self._table.setHorizontalHeaderLabels(["ID", "Task", "Name", "Phase"])
        
        hdr = self._table.horizontalHeader()
        hdr.setStretchLastSection(True)
        from PySide6.QtWidgets import QHeaderView
        for col, mode in ((0, QHeaderView.ResizeToContents),
                          (1, QHeaderView.ResizeToContents),
                          (2, QHeaderView.Stretch),
                          (3, QHeaderView.ResizeToContents)):
            hdr.setSectionResizeMode(col, mode)

        vh = self._table.verticalHeader()
        vh.setVisible(False)
        vh.setDefaultSectionSize(22)
        vh.setMinimumSectionSize(18)
        self._table.setWordWrap(False)

        top = QHBoxLayout()
        top.addWidget(QLabel("Task:"))
        top.addWidget(self._task_filter)
        top.addStretch(1)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self._table)

    def load(self, project_id:int):
        self._project_id = project_id
        self._all_rows = self._repo.list_subtasks_for_project(project_id)  # expect list of dicts
        self._populate_task_filter(self._all_rows)
        self._render(self._all_rows)

    def _populate_task_filter(self, rows):
        seen = {}
        self._task_filter.blockSignals(True)
        self._task_filter.clear()
        self._task_filter.addItem("All tasks", userData=None)
        for r in rows:
            tid = r.get("task_id")
            tname = r.get("task_name") or f"Task {tid}"
            if tid not in seen:
                self._task_filter.addItem(tname, userData=tid)
                seen[tid] = True
        self._task_filter.blockSignals(False)

    def _apply_filter(self):
        tid = self._task_filter.currentData()
        rows = self._all_rows if tid is None else [r for r in self._all_rows if r.get("task_id")==tid]
        self._render(rows)

    def _render(self, rows):
        self._table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self._table.setItem(i, 0, QTableWidgetItem(str(r.get("id"))))
            self._table.setItem(i, 1, QTableWidgetItem(str(r.get("task_id"))))
            self._table.setItem(i, 2, QTableWidgetItem(r.get("name") or ""))
            self._table.setItem(i, 3, QTableWidgetItem(r.get("phase_name") or ""))

