# src/ui/project_picker_view.py
# Rev 0.1.1
from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableView, QPushButton, QHBoxLayout
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

class ProjectPickerView(QWidget):
    projectChosen = Signal(int)

    def __init__(self, projects_vm, parent=None):
        super().__init__(parent)
        self._vm = projects_vm

        self._name = QLabel("Select a project")
        self._name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._table = QTableView()
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableView.SingleSelection)
        self._table.doubleClicked.connect(self._emit_selection)

        self._open_btn = QPushButton("Open")
        self._open_btn.clicked.connect(self._emit_selection)

        top = QHBoxLayout()
        top.addWidget(self._name)
        top.addStretch()
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self._table)
        layout.addWidget(self._open_btn, alignment=Qt.AlignRight)

        self._model = QStandardItemModel(0, 2, self)
        self._model.setHorizontalHeaderLabels(["ID", "Name"])
        self._table.setModel(self._model)
        self.refresh()

    def refresh(self):
        rows = self._vm.list_projects()
        self._model.removeRows(0, self._model.rowCount())
        for pid, name in rows:
            id_item = QStandardItem(str(pid))
            name_item = QStandardItem(name or "")
            id_item.setEditable(False)
            name_item.setEditable(False)
            self._model.appendRow([id_item, name_item])
        self._table.resizeColumnsToContents()

    def _emit_selection(self):
        idxs = self._table.selectionModel().selectedRows()
        if not idxs:
            return
        row = idxs[0].row()
        pid = int(self._model.item(row, 0).text())
        self.projectChosen.emit(pid)

