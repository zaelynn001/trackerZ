# Rev 0.6.5 — CRUD + phase/priority labels + task filter shows all tasks by name
from __future__ import annotations
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QMessageBox, QDialog
)

from ui.subtask_editor_dialog import SubtaskEditorDialog


class SubtasksTab(QWidget):
    _PHASE_NAMES = {1: "Open", 2: "In Progress", 3: "In Hiatus", 4: "Resolved", 5: "Closed"}

    def __init__(self, subtasks_repo, parent=None):
        super().__init__(parent)
        self._repo = subtasks_repo
        self._project_id: Optional[int] = None
        self._all_rows: List[dict] = []
        self._tasks_by_id: dict[int, str] = {}  # task_id -> task_name

        # Top controls
        self._task_filter = QComboBox()
        self._task_filter.addItem("All tasks", userData=None)
        self._task_filter.currentIndexChanged.connect(self._apply_filter)

        self._btn_new = QPushButton("New Subtask")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        for b in (self._btn_edit, self._btn_delete):
            b.setEnabled(False)

        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)

        # Table: ID | Task | Name | Phase | Priority
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["ID", "Task", "Name", "Phase", "Priority"])
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

        hdr = self._table.horizontalHeader()
        for col, mode in (
            (0, QHeaderView.ResizeToContents),
            (1, QHeaderView.ResizeToContents),
            (2, QHeaderView.Stretch),
            (3, QHeaderView.ResizeToContents),
            (4, QHeaderView.ResizeToContents),
        ):
            hdr.setSectionResizeMode(col, mode)

        vh = self._table.verticalHeader()
        vh.setVisible(False)
        vh.setDefaultSectionSize(22)
        vh.setMinimumSectionSize(18)
        self._table.setWordWrap(False)
        self._table.setAlternatingRowColors(True)

        # Layout
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Task:"))
        row1.addWidget(self._task_filter)
        row1.addStretch(1)

        row2 = QHBoxLayout()
        row2.addWidget(self._btn_new)
        row2.addWidget(self._btn_edit)
        row2.addWidget(self._btn_delete)
        row2.addStretch(1)

        root = QVBoxLayout(self)
        root.addLayout(row1)
        root.addLayout(row2)
        root.addWidget(self._table)

    # ---------- Public API ----------
    def load(self, project_id: int):
        self._project_id = project_id
        self._all_rows = self._repo.list_subtasks_for_project(project_id)
        self._load_task_names_for_project(project_id)  # fill id->name cache
        self._populate_task_filter(self._all_rows)
        self._render(self._all_rows)

    # ---------- Helpers ----------
    def _populate_task_filter(self, rows: List[dict]):
        """Populate the task filter with *all* project tasks, not just those seen in rows."""
        prev_tid = self._task_filter.currentData()

        self._task_filter.blockSignals(True)
        self._task_filter.clear()
        self._task_filter.addItem("All tasks", userData=None)

        # Use the id->name cache (includes tasks with zero subtasks)
        for tid, tname in sorted(self._tasks_by_id.items(), key=lambda kv: kv[0]):
            label = tname or f"Task {tid}"
            self._task_filter.addItem(label, userData=tid)

        if prev_tid is not None:
            idx = self._task_filter.findData(prev_tid)
            if idx >= 0:
                self._task_filter.setCurrentIndex(idx)

        self._task_filter.blockSignals(False)

    def _apply_filter(self):
        tid = self._task_filter.currentData()
        rows = self._all_rows if tid is None else [r for r in self._all_rows if r.get("task_id") == tid]
        self._render(rows)

    @staticmethod
    def _priority_label(priority_id: Optional[int]) -> str:
        names = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}
        return names.get(priority_id, "—")

    @staticmethod
    def _phase_label(phase_id: Optional[int]) -> str:
        if phase_id is None:
            return "—"
        return SubtasksTab._PHASE_NAMES.get(int(phase_id), str(phase_id))

    def _render(self, rows: List[dict]):
        self._table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            sid = r.get("id")
            tid = r.get("task_id")
            name = r.get("name") or ""
            phase = self._phase_label(r.get("phase_id"))
            prio = self._priority_label(r.get("priority_id"))

            it_id = QTableWidgetItem(str(sid))
            it_id.setData(Qt.UserRole, sid)
            it_task = QTableWidgetItem(str(tid))
            it_name = QTableWidgetItem(name)
            it_phase = QTableWidgetItem(phase)
            it_prio = QTableWidgetItem(prio)

            for it in (it_id, it_task, it_name, it_phase, it_prio):
                it.setFlags(it.flags() ^ Qt.ItemIsEditable)

            self._table.setItem(i, 0, it_id)
            self._table.setItem(i, 1, it_task)
            self._table.setItem(i, 2, it_name)
            self._table.setItem(i, 3, it_phase)
            self._table.setItem(i, 4, it_prio)

        self._on_selection_changed()

    def _selected_subtask_id(self) -> Optional[int]:
        items = self._table.selectedItems()
        if not items:
            return None
        try:
            return int(items[0].data(Qt.UserRole) or self._table.item(items[0].row(), 0).text())
        except Exception:
            return None

    def _current_filter_task_id(self) -> Optional[int]:
        return self._task_filter.currentData()

    def _on_selection_changed(self):
        has = self._selected_subtask_id() is not None
        self._btn_edit.setEnabled(has)
        self._btn_delete.setEnabled(has)

    # ---------- Actions ----------
    def _on_new(self):
        task_id = self._current_filter_task_id()
        if task_id is None:
            QMessageBox.information(self, "Choose task", "Select a specific Task from the filter to add a subtask.")
            return
        dlg = SubtaskEditorDialog(self, title="New Subtask", phase_id=1, priority_id=2)
        if dlg.exec() != int(QDialog.DialogCode.Accepted):
            return
        name, desc, phase_id, priority_id, note = dlg.values()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please provide a subtask name.")
            return

        self._repo.create_subtask(
            task_id=task_id, name=name, description=desc,
            phase_id=phase_id, priority_id=priority_id,
            note_on_create=note or "Created via UI"
        )
        self._reload()

    def _on_edit(self):
        sid = self._selected_subtask_id()
        if sid is None:
            return
        rec = self._repo.get_subtask(sid)
        if not rec:
            return

        dlg = SubtaskEditorDialog(
            self,
            name=rec.get("name") or "",
            description=rec.get("description") or "",
            phase_id=int(rec.get("phase_id", 1)),
            priority_id=int(rec.get("priority_id", 2)),
            title="Edit Subtask",
        )
        if dlg.exec() != int(QDialog.DialogCode.Accepted):
            return
        name, desc, phase_id, priority_id, note = dlg.values()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please provide a subtask name.")
            return

        self._repo.update_subtask_fields(sid, name=name, description=desc, note=note or "Edited via UI")
        self._repo.change_subtask_phase(sid, phase_id, reason="update", note=note or None)
        self._repo.set_subtask_priority(sid, priority_id, note=note or None)
        self._reload()


    def _on_delete(self):
        sid = self._selected_subtask_id()
        if sid is None:
            return
        if QMessageBox.question(self, "Delete Subtask", f"Delete subtask #{sid}?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self._repo.delete_subtask(sid)
        self._reload()

    def _reload(self):
        if self._project_id is None:
            return
        self._all_rows = self._repo.list_subtasks_for_project(self._project_id)
        self._apply_filter()

    # ---------- DB access helpers ----------
    def _conn_for(self, repo):
        # Grab a sqlite3.Connection from various repo shapes
        if hasattr(repo, "_conn"):
            try:
                return repo._conn()
            except Exception:
                pass
        if hasattr(repo, "conn"):
            c = getattr(repo, "conn")
            if c:
                return c
        if hasattr(repo, "_db_or_conn"):
            inner = getattr(repo, "_db_or_conn")
            if hasattr(inner, "conn"):
                return inner.conn
        if hasattr(repo, "_db"):
            inner = getattr(repo, "_db")
            if hasattr(inner, "conn"):
                return inner.conn
        return None

    def _load_task_names_for_project(self, project_id: int):
        """Fill self._tasks_by_id with id->name for tasks in the project."""
        self._tasks_by_id.clear()
        conn = self._conn_for(self._repo)
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM tasks WHERE project_id = ? ORDER BY id", (project_id,))
        for tid, name in cur.fetchall():
            self._tasks_by_id[int(tid)] = name or f"Task {tid}"
