# src/ui/tasks_view.py
# Rev 0.6.8 — M6.5 bottom-center History panel (schema Rev 1.1.0)
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSettings, QModelIndex
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QHBoxLayout, QPushButton, QMessageBox, QDialog, QSplitter
)

from viewmodels.tasks_viewmodel import TasksViewModel
from ui.task_editor_dialog import TaskEditorDialog
from ui.panels.history_panel import HistoryPanel


class TasksView(QWidget):
    taskChosen = Signal(int)

    def __init__(self, tasks_repo, parent=None):
        super().__init__(parent)
        self._vm = TasksViewModel(tasks_repo)
        self._project_id: int | None = None
        self._phase_id: int | None = None

        # ---------- Controls ----------
        self._btn_new = QPushButton("New Task")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        self._btn_history = QPushButton("History")
        self._btn_history.setCheckable(True)
        self._btn_history.setChecked(True)  # panel visible by default

        self._btn_edit.setEnabled(False)
        self._btn_delete.setEnabled(False)
        self._btn_history.setEnabled(False)

        # ---------- Table: ID | Name | Phase | Priority ----------
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

        # ---------- History panel (bottom-center) ----------
        # Expect HistoryPanel to expose: set_updates(list[dict])
        self._history = HistoryPanel(self)
        self._history.setObjectName("HistoryPanel")

        # ---------- Top bar ----------
        top_bar = QHBoxLayout()
        top_bar.addWidget(self._btn_new)
        top_bar.addWidget(self._btn_edit)
        top_bar.addWidget(self._btn_delete)
        top_bar.addWidget(self._btn_history)
        top_bar.addStretch(1)

        # ---------- Top holder (bar + table) ----------
        top_holder = QWidget(self)
        _top_layout = QVBoxLayout(top_holder)
        _top_layout.setContentsMargins(0, 0, 0, 0)
        _top_layout.addLayout(top_bar)
        _top_layout.addWidget(self._table, 1)

        # ---------- Vertical splitter ----------
        self._split = QSplitter(Qt.Vertical, self)
        self._split.addWidget(top_holder)
        self._split.addWidget(self._history)
        self._split.setStretchFactor(0, 3)  # table prefers more space
        self._split.setStretchFactor(1, 2)

        # Root layout
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._split, 1)

        # ---------- Wire buttons ----------
        self._btn_new.clicked.connect(self._on_new_clicked)
        self._btn_edit.clicked.connect(self._on_edit_clicked)
        self._btn_delete.clicked.connect(self._on_delete_clicked)
        self._btn_history.toggled.connect(self._toggle_history)
        # Optional: clicking the text when already checked forces a reload
        self._btn_history.clicked.connect(self._maybe_reload_history)

        # ---------- VM signals ----------
        self._vm.tasksReloaded.connect(self._on_tasks_reloaded)
        self._vm.timelineLoaded.connect(self._on_timeline_loaded)

    # ---------- Public API ----------
    def load_for_project(self, project_id: int, phase_id: int | None):
        self._project_id = project_id
        self._phase_id = phase_id
        self._vm.set_filters(project_id, phase_id)
        self._vm.reload()

    # ---------- Lifecycle (persist splitter sizes) ----------
    def showEvent(self, ev):
        super().showEvent(ev)
        s = QSettings("trackerZ", "ui")
        sizes = s.value("tasks_split_sizes")
        if sizes:
            try:
                self._split.setSizes([int(x) for x in sizes])
            except Exception:
                pass
        else:
            # sensible default: 70% table, 30% history
            self._split.setSizes([700, 300])

    def closeEvent(self, ev):
        s = QSettings("trackerZ", "ui")
        s.setValue("tasks_split_sizes", self._split.sizes())
        super().closeEvent(ev)

    # ---------- Internals ----------
    def _on_tasks_reloaded(self, total: int, rows: list[dict]):
        self._render(rows)
        # If panel is visible and a row is selected, refresh timeline
        if self._btn_history.isChecked():
            tid = self._selected_task_id()
            if tid is not None:
                self._vm.load_timeline(tid)

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

        # Auto-refresh history when visible
        if has_sel and self._btn_history.isChecked():
            tid = self._selected_task_id()
            if tid is not None:
                self._vm.load_timeline(tid)

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

        # --- Load authoritative record from DB via ViewModel ---
        rec = self._vm.get_task_details(tid) if hasattr(self._vm, "get_task_details") else None
        if not rec:
            # fallback to current table values if repo call not yet added
            row = self._table.currentRow()
            cur_name = self._table.item(row, 1).text() if row >= 0 else ""
            phase_label = self._table.item(row, 2).text() if row >= 0 else "Open"
            prio_label = self._table.item(row, 3).text() if row >= 0 else "Medium"
            phase_id_map = {1: "Open", 2: "In Progress", 3: "In Hiatus", 4: "Resolved", 5: "Closed"}
            prio_id_map = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}
            phase_name_to_id = {v: k for k, v in phase_id_map.items()}
            prio_name_to_id = {v: k for k, v in prio_id_map.items()}
            cur_phase_id = phase_name_to_id.get(phase_label, 1)
            cur_prio_id = prio_name_to_id.get(prio_label, 2)
            cur_desc = ""
        else:
            cur_name = rec.get("name") or ""
            cur_desc = rec.get("description") or ""
            cur_phase_id = int(rec.get("phase_id") or 1)
            cur_prio_id = int(rec.get("priority_id") or 2)

        # --- Open the editor dialog ---
        from ui.task_editor_dialog import TaskEditorDialog
        dlg = TaskEditorDialog(
            self,
            title="Edit Task",
            name=cur_name,
            description=cur_desc,     # real description; read-only in edit mode
            phase_id=cur_phase_id,
            priority_id=cur_prio_id,
            mode="edit",
        )

        if dlg.exec() != int(QDialog.DialogCode.Accepted):
            return

        # --- Extract new values ---
        name, desc, phase_id, priority_id, note = dlg.values()

        if not name:
            QMessageBox.warning(self, "Missing name", "Please provide a task name.")
            return

        # --- Apply only what actually changed ---
        try:
            # Only change phase if different
            if int(phase_id) != int(cur_phase_id):
                self._vm.change_task_phase(
                    task_id=tid,
                    new_phase_id=int(phase_id),
                    reason="phase_change",
                    note=note or None,
                )

            # Only change priority if different
            if int(priority_id) != int(cur_prio_id):
                self._vm.set_task_priority(
                    task_id=tid,
                    new_priority_id=int(priority_id),
                    note=note or None,
                )

            # If neither phase nor priority changed but a note exists, log it as a note
            if note and int(phase_id) == int(cur_phase_id) and int(priority_id) == int(cur_prio_id):
                try:
                    self._vm.update_task_fields(task_id=tid, note=note)
                except Exception:
                    pass

        except Exception as e:
            QMessageBox.warning(self, "Update failed", f"An error occurred:\n{e}")


    def _on_delete_clicked(self):
        tid = self._selected_task_id()
        if tid is None:
            return
        if QMessageBox.question(
            self, "Delete Task", f"Are you sure you want to delete task #{tid}?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self._vm.delete_task(tid)
            # Clear history panel
            self._history.set_updates([])

    def _toggle_history(self, on: bool):
        self._history.setVisible(on)
        if not on:
            # collapse bottom pane
            self._split.setSizes([1_000, 0])
        else:
            # restore a sensible height
            sizes = self._split.sizes()
            if sizes[1] == 0:
                self._split.setSizes([700, 300])
            # load if we have a selection
            tid = self._selected_task_id()
            if tid is not None:
                self._vm.load_timeline(tid)

    def _maybe_reload_history(self):
        # If already visible and a task is selected, refresh the data
        if self._btn_history.isChecked():
            tid = self._selected_task_id()
            if tid is not None:
                self._vm.load_timeline(tid)

    def _on_history_clicked(self):
        # Kept for compatibility if other code triggers it; delegate to reload
        self._maybe_reload_history()

    def _on_timeline_loaded(self, task_id: int, updates: list[dict]):
        # Render into the bottom-center history panel
        self._history.set_updates(updates)
