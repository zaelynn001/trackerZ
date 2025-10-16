# Rev 0.6.7 — add Priority column (schema Rev 1.1.0)
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QHBoxLayout, QPushButton, QMessageBox, QDialog
)

from viewmodels.tasks_viewmodel import TasksViewModel
from ui.task_editor_dialog import TaskEditorDialog
from ui.task_timeline_panel import TaskTimelinePanel


class TasksView(QWidget):
    taskChosen = Signal(int)

    def __init__(self, tasks_repo, parent=None):
        super().__init__(parent)
        self._vm = TasksViewModel(tasks_repo)
        self._project_id: int | None = None
        self._phase_id: int | None = None

        # Controls
        self._btn_new = QPushButton("New Task")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        self._btn_history = QPushButton("History")

        self._btn_edit.setEnabled(False)
        self._btn_delete.setEnabled(False)
        self._btn_history.setEnabled(False)

        # Table: ID | Name | Phase | Priority
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["ID", "Name", "Phase", "Priority"])
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

        hdr = self._table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)            # Name
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)   # Phase
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)   # Priority

        vh = self._table.verticalHeader()
        vh.setVisible(False)
        vh.setDefaultSectionSize(22)
        vh.setMinimumSectionSize(18)
        self._table.setWordWrap(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSizeAdjustPolicy(QTableWidget.AdjustToContentsOnFirstShow)

        # Timeline panel
        self._timeline = TaskTimelinePanel(self)
        self._timeline.setVisible(False)

        # Layout
        top = QHBoxLayout()
        top.addWidget(self._btn_new)
        top.addWidget(self._btn_edit)
        top.addWidget(self._btn_delete)
        top.addWidget(self._btn_history)
        top.addStretch(1)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self._table)
        lay.addWidget(self._timeline)

        # Wire buttons
        self._btn_new.clicked.connect(self._on_new_clicked)
        self._btn_edit.clicked.connect(self._on_edit_clicked)
        self._btn_delete.clicked.connect(self._on_delete_clicked)
        self._btn_history.clicked.connect(self._on_history_clicked)

        # VM signals
        self._vm.tasksReloaded.connect(self._on_tasks_reloaded)
        self._vm.timelineLoaded.connect(self._on_timeline_loaded)

    # ---------- Public API ----------
    def load_for_project(self, project_id: int, phase_id: int | None):
        self._project_id = project_id
        self._phase_id = phase_id
        self._vm.set_filters(project_id, phase_id)
        self._vm.reload()

    # ---------- Internals ----------
    def _on_tasks_reloaded(self, total: int, rows: list[dict]):
        self._render(rows)
    _PHASE_NAMES = {1: "Open", 2: "In Progress", 3: "In Hiatus", 4: "Resolved", 5: "Closed"}

    @staticmethod
    def _phase_label(phase_id: int | None) -> str:
        if phase_id is None:
            return "—"
        return TasksView._PHASE_NAMES.get(int(phase_id), str(phase_id))


    @staticmethod
    def _priority_label(priority_id: int | None) -> str:
        # Stable mapping: 1 Low, 2 Medium, 3 High, 4 Critical
        names = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}
        return names.get(priority_id, "—")

    def _render(self, rows: list[dict]):
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            tid = row.get("id") or row.get("task_id")
            name = row.get("name") or row.get("title") or ""
            phase_name = row.get("phase_name") or self._phase_label(row.get("phase_id"))
            priority_id = row.get("priority_id")

            id_item = QTableWidgetItem(str(tid) if tid is not None else "")
            name_item = QTableWidgetItem(name)
            phase_item = QTableWidgetItem(phase_name)
            prio_item = QTableWidgetItem(self._priority_label(priority_id))

            for it in (id_item, name_item, phase_item, prio_item):
                it.setData(Qt.UserRole, tid)

            self._table.setItem(r, 0, id_item)
            self._table.setItem(r, 1, name_item)
            self._table.setItem(r, 2, phase_item)
            self._table.setItem(r, 3, prio_item)

        self._table.resizeColumnsToContents()
        self._on_selection_changed()

    def _on_item_double_clicked(self, item: QTableWidgetItem):
        if not item:
            return
        tid = item.data(Qt.UserRole)
        if tid is None:
            try:
                tid = int(self._table.item(item.row(), 0).text())
            except Exception:
                return
        self.taskChosen.emit(int(tid))

    def _selected_task_id(self) -> int | None:
        items = self._table.selectedItems()
        if not items:
            return None
        tid = items[0].data(Qt.UserRole)
        if tid is None:
            try:
                tid = int(self._table.item(items[0].row(), 0).text())
            except Exception:
                return None
        return int(tid)

    def _on_selection_changed(self):
        has_sel = self._selected_task_id() is not None
        self._btn_edit.setEnabled(has_sel)
        self._btn_delete.setEnabled(has_sel)
        self._btn_history.setEnabled(has_sel)

    # ----- Buttons -----
    def _on_new_clicked(self):
        if self._project_id is None:
            return
        dlg = TaskEditorDialog(self, title="New Task", phase_id=1, priority_id=2)
        if dlg.exec() != int(QDialog.DialogCode.Accepted):
            return
        name, desc, phase_id, priority_id, note = dlg.values()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please provide a task name.")
            return

        self._vm.create_task(
            project_id=self._project_id,
            name=name,
            description=desc,
            phase_id=phase_id,
            priority_id=priority_id,
            note_on_create=note or "Created via UI",
        )

    def _on_edit_clicked(self):
        tid = self._selected_task_id()
        if tid is None:
            return
        row = self._table.currentRow()
        cur_name = self._table.item(row, 1).text() if row >= 0 else ""
        dlg = TaskEditorDialog(self, name=cur_name, description="", title="Edit Task")
        if dlg.exec() != int(QDialog.DialogCode.Accepted):
            return

        name, desc, phase_id, priority_id, note = dlg.values()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please provide a task name.")
            return

        # Update fields (logs note if provided)
        self._vm.update_task_fields(task_id=tid, name=name, description=desc, note=note or "Edited via UI")

        # Apply phase change
        try:
            self._vm.change_task_phase(task_id=tid, new_phase_id=phase_id, reason="update", note=note or None)
        except Exception:
            pass

        # Apply priority change (no-op if unchanged)
        try:
            self._vm.set_task_priority(task_id=tid, new_priority_id=priority_id, note=note or None)
        except Exception:
            pass



    def _on_delete_clicked(self):
        tid = self._selected_task_id()
        if tid is None:
            return
        from PySide6.QtWidgets import QMessageBox
        if QMessageBox.question(self, "Delete Task", f"Are you sure you want to delete task #{tid}?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self._vm.delete_task(tid)
            self._timeline.setVisible(False)

    def _on_history_clicked(self):
        tid = self._selected_task_id()
        if tid is None:
            return
        self._vm.load_timeline(tid)

    def _on_timeline_loaded(self, task_id: int, updates: list[dict]):
        self._timeline.setVisible(True)
        self._timeline.set_updates(updates)
