# src/ui/tasks_view.py  Rev 0.1.1
from __future__ import annotations
from PySide6.QtCore import Qt, Signal, Slot, QModelIndex
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QTableView
from PySide6.QtGui import QStandardItemModel, QStandardItem

PHASE_LABEL = "Phase"

class TasksView(QWidget):
    backRequested = Signal()
    taskEditRequested = Signal(int)  # emits selected task_id

    def __init__(self, tasks_vm, parent=None):
        super().__init__(parent)
        self._vm = tasks_vm
        self._project_id = None

        header = QHBoxLayout()
        self._back = QPushButton("Back")
        self._back.clicked.connect(self.backRequested.emit)
        self._phase_label = QLabel(PHASE_LABEL + ":")
        self._phase_combo = QComboBox()
        self._phase_combo.currentIndexChanged.connect(self._apply_filter)
        header.addWidget(self._back); header.addStretch(); header.addWidget(self._phase_label); header.addWidget(self._phase_combo)

        ##counters = QHBoxLayout()
        ##self._total = QLabel("Total: 0")
        ##self._filtered = QLabel("Filtered: 0")
        ##counters.addWidget(self._total); counters.addWidget(self._filtered); counters.addStretch()

        self._tasks_table = QTableView()
        self._tasks_table.setSelectionBehavior(QTableView.SelectRows)
        self._tasks_table.setSelectionMode(QTableView.SingleSelection)

        self._model = QStandardItemModel(0, 4, self)
        self._model.setHorizontalHeaderLabels(["ID", "Title", "Phase", "Updated"])
        self._tasks_table.setModel(self._model)

        self._tasks_table.doubleClicked.connect(self._on_row_activated)
        self._tasks_table.activated.connect(self._on_row_activated)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        ##layout.addLayout(counters)
        layout.addWidget(self._tasks_table)

    def load_for_project(self, project_id: int):
        self._project_id = project_id
        phases = self._vm.list_phases()
        self._phase_combo.blockSignals(True)
        self._phase_combo.clear()
        self._phase_combo.addItem("All", userData=None)
        for pid, name in phases:
            self._phase_combo.addItem(name, userData=pid)
        self._phase_combo.blockSignals(False)
        self._reload()

    def _apply_filter(self):
        self._reload()

    def _reload(self):
        if self._project_id is None:
            return
        phase_id = self._phase_combo.currentData()
        rows = self._vm.list_tasks(self._project_id, phase_id)
        self._model.removeRows(0, self._model.rowCount())
        for tid, title, phase_name, updated_at in rows:
            items = [QStandardItem(str(tid)),
                     QStandardItem(title or ""),
                     QStandardItem(phase_name or ""),
                     QStandardItem(updated_at or "")]
            for it in items:
                it.setEditable(False)
            self._model.appendRow(items)
        self._tasks_table.resizeColumnsToContents()
        

    @Slot(QModelIndex)
    def _on_row_activated(self, index: QModelIndex):
        if not index.isValid():
            return
        row = index.row()
        tid = self._get_task_id_for_row(row)
        if tid is not None:
            self.taskEditRequested.emit(int(tid))

    def _get_task_id_for_row(self, row: int) -> int | None:
        try:
            idx = self._model.index(row, 0)  # ID column
            return int(self._model.data(idx))
        except Exception:
            return None

