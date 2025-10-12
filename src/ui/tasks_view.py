# Rev 0.4.1

# trackerZ – TasksView (Rev 0.4.1)
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView

from viewmodels.tasks_viewmodel import TasksViewModel

class TasksView(QWidget):
    # Emitted when a user activates (double-clicks) a task row
    taskChosen = Signal(int)

    def __init__(self, tasks_repo, parent=None):
        super().__init__(parent)
        self._vm = TasksViewModel(tasks_repo)
        self._project_id = None
        self._phase_id = None

        self._table = QTableWidget(0, 3)  # id, name, phase
        self._table.setHorizontalHeaderLabels(["ID", "Name", "Phase"])
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        hdr = self._table.horizontalHeader()
        hdr.setStretchLastSection(True)                       # let last column fill
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID snug
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)           # Name grows
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Phase snug

        vh = self._table.verticalHeader()
        vh.setVisible(False)
        vh.setDefaultSectionSize(22)       # tidy row height
        vh.setMinimumSectionSize(18)
        self._table.setWordWrap(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSizeAdjustPolicy(
            QTableWidget.AdjustToContentsOnFirstShow
        )

        lay = QVBoxLayout(self)
        lay.addWidget(self._table)

    def load_for_project(self, project_id: int, phase_id: int | None):
        """Public entry point used by TasksTab."""
        self._project_id = project_id
        self._phase_id = phase_id
        self._reload()

    # --- internals ---------------------------------------------------------

    def _reload(self):
        if self._project_id is None:
            return
        total, rows = self._vm.list_tasks(project_id=self._project_id, phase_id=self._phase_id)
        # You can propagate 'total vs filtered' to a status bar if you want:
        # self.window().statusBar().showMessage(f"Showing {len(rows)} of {total} tasks")

        self._render(rows)

    def _render(self, rows: list[dict]):
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            tid = row.get("id") or row.get("task_id")
            name = row.get("name") or row.get("title") or ""
            phase_name = row.get("phase_name") or row.get("phase") or ""

            id_item = QTableWidgetItem(str(tid) if tid is not None else "")
            name_item = QTableWidgetItem(name)
            phase_item = QTableWidgetItem(phase_name)

            # Store the task id in UserRole for reliable retrieval
            id_item.setData(Qt.UserRole, tid)
            name_item.setData(Qt.UserRole, tid)
            phase_item.setData(Qt.UserRole, tid)

            self._table.setItem(r, 0, id_item)
            self._table.setItem(r, 1, name_item)
            self._table.setItem(r, 2, phase_item)

        self._table.resizeColumnsToContents()

    def _on_item_double_clicked(self, item: QTableWidgetItem):
        if not item:
            return
        tid = item.data(Qt.UserRole)
        if tid is None:
            # Fallback: try to parse from column 0 text
            try:
                tid = int(self._table.item(item.row(), 0).text())
            except Exception:
                return
        self.taskChosen.emit(int(tid))

