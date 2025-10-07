# src/ui/subtasks_view.py
# Rev 0.1.1
from __future__ import annotations
from PySide6.QtCore import Qt, Signal, Slot, QModelIndex
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableView
from PySide6.QtGui import QStandardItemModel, QStandardItem

class SubtasksView(QWidget):
    subtaskEditRequested = Signal(int) 
    def __init__(self, tasks_vm, parent=None):
        super().__init__(parent)
        self._vm = tasks_vm
        self._task_id = None

        hdr = QHBoxLayout()
        self._title = QLabel("Subtasks")
        self._phase_lbl = QLabel("Phase:")
        self._phase_combo = QComboBox()
        self._phase_combo.currentIndexChanged.connect(self._reload)
        hdr.addWidget(self._title); hdr.addStretch(); hdr.addWidget(self._phase_lbl); hdr.addWidget(self._phase_combo)

        ##ctr = QHBoxLayout()
       ## self._total = QLabel("Total: 0")
       ## self._filtered = QLabel("Filtered: 0")
       ## ctr.addWidget(self._total); ctr.addWidget(self._filtered); ctr.addStretch()

        self._table = QTableView()
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableView.SingleSelection)
        self._table.doubleClicked.connect(self._on_row_activated)
        self._table.activated.connect(self._on_row_activated)
        lay = QVBoxLayout(self)
        lay.addLayout(hdr)
        ##lay.addLayout(ctr)
        lay.addWidget(self._table)

        self._model = QStandardItemModel(0, 4, self)
        self._model.setHorizontalHeaderLabels(["ID", "Title", "Phase", "Updated"])
        self._table.setModel(self._model)
    def load_for_project(self, project_id: int, phase_id: int | None = None):
        self._project_id = project_id
        self._task_id = None  # clear any task filter
        self._reload(phase_id)
    def set_task(self, task_id: int | None):
        self._task_id = task_id
        self._title.setText(f"Subtasks for Task {task_id}")
        phases = self._vm.list_phases()
        self._phase_combo.blockSignals(True)
        self._phase_combo.clear()
        self._phase_combo.addItem("All", userData=None)
        for pid, name in phases:
            self._phase_combo.addItem(name, userData=pid)
        self._phase_combo.blockSignals(False)
        self._reload()
        
    @Slot(QModelIndex)
    def _on_row_activated(self, index: QModelIndex):
        if not index.isValid():
            return
        row = index.row()
        sid = self._get_subtask_id_for_row(row)
        if sid is not None and hasattr(self, "subtaskEditRequested"):
            self.subtaskEditRequested.emit(int(sid))
            
    def _get_subtask_id_for_row(self, row: int) -> int | None:
        """
        Returns subtask_id from the model.
        Assumes column 0 holds ID or it is stored under UserRole.
        """
        try:
            idx = self._model.index(row, 0)
            val = self._model.data(idx)
            if val is not None:
                return int(val)
        except Exception:
            pass
        try:
            idx = self._model.index(row, 0)
            val = self._model.data(idx, Qt.UserRole)
            if val is not None:
                return int(val)
        except Exception:
            pass
        return None    

    def _reload(self, phase_id: int | None = None):
        if self._project_id is None:
            return
        # expect VM to accept project_id plus optional task_id and phase_id
        rows = self._vm.list_subtasks(project_id=self._project_id, phase_id=phase_id)
        self._model.removeRows(0, self._model.rowCount())
        for sid, name, phase_name, updated_at_utc in rows:
            items=[QStandardItem(str(sid)), QStandardItem(name or ""), QStandardItem(phase_name or ""), QStandardItem(updated_at_utc                                                                      or "")]
            for it in items: it.setEditable(False)
            self._model.appendRow(items)
        self._table.resizeColumnsToContents()

