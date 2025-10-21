# Rev 0.7.0 — Bottom-center History panel + coalesced timeline for Subtasks
from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QMessageBox, QDialog, QSplitter
)

from ui.subtask_editor_dialog import SubtaskEditorDialog
from ui.panels.history_panel import HistoryPanel
from repositories.sqlite_subtask_updates_repository import SQLiteSubtaskUpdatesRepository


class SubtasksTab(QWidget):
    _PHASE_NAMES = {1: "Open", 2: "In Progress", 3: "In Hiatus", 4: "Resolved", 5: "Closed"}
    _PRIORITY_NAMES = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}

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

        # --- Build "top holder" (controls + table)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Task:"))
        row1.addWidget(self._task_filter, 1)
        row1.addSpacing(12)
        row1.addWidget(self._btn_new)
        row1.addWidget(self._btn_edit)
        row1.addWidget(self._btn_delete)

        top_holder = QWidget(self)
        _top_layout = QVBoxLayout(top_holder)
        _top_layout.setContentsMargins(0, 0, 0, 0)
        _top_layout.addLayout(row1)
        _top_layout.addWidget(self._table, 1)

        # --- History panel (bottom-center)
        self._history = HistoryPanel(self)
        self._history.setObjectName("HistoryPanel")

        # --- Vertical splitter
        self._split = QSplitter(Qt.Vertical, self)
        self._split.addWidget(top_holder)
        self._split.addWidget(self._history)
        self._split.setStretchFactor(0, 3)  # table gets more space by default
        self._split.setStretchFactor(1, 2)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._split, 1)

        # Updates repo cache
        self._updates_repo: Optional[SQLiteSubtaskUpdatesRepository] = None

    # ---------- lifecycle (persist splitter sizes) ----------
    def showEvent(self, ev):
        super().showEvent(ev)
        s = QSettings("trackerZ", "ui")
        sizes = s.value("subtasks_split_sizes")
        if sizes:
            try:
                self._split.setSizes([int(x) for x in sizes])
            except Exception:
                pass
        else:
            self._split.setSizes([700, 300])

    def closeEvent(self, ev):
        s = QSettings("trackerZ", "ui")
        s.setValue("subtasks_split_sizes", self._split.sizes())
        super().closeEvent(ev)

    # ---------- public API ----------
    def load(self, project_id: int):
        self._project_id = project_id
        # Fetch tasks & subtasks
        self._refresh_task_names_cache(project_id)
        self._all_rows = self._repo.list_subtasks_for_project(project_id)
        self._populate_task_filter()
        self._apply_filter()
        # Clear history panel until a row is selected
        self._history.set_updates([])

    # ---------- filter & render ----------
    def _populate_task_filter(self):
        prev_tid = self._task_filter.currentData()

        self._task_filter.blockSignals(True)
        self._task_filter.clear()
        self._task_filter.addItem("All tasks", userData=None)

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
        return SubtasksTab._PRIORITY_NAMES.get(priority_id, "—")

    @staticmethod
    def _phase_label(phase_id: Optional[int]) -> str:
        if phase_id is None:
            return "—"
        return SubtasksTab._PHASE_NAMES.get(int(phase_id), str(phase_id))

    def _render(self, rows: List[dict]):
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            sid = row.get("id") or row.get("subtask_id")
            task_id = row.get("task_id")
            tname = self._tasks_by_id.get(task_id, f"Task {task_id}")
            name = row.get("name") or ""
            phase_name = row.get("phase_name") or self._phase_label(row.get("phase_id"))
            priority_id = row.get("priority_id")

            id_item = QTableWidgetItem(str(sid) if sid is not None else "")
            task_item = QTableWidgetItem(tname)
            name_item = QTableWidgetItem(name)
            phase_item = QTableWidgetItem(phase_name)
            prio_item = QTableWidgetItem(self._priority_label(priority_id))

            for it in (id_item, task_item, name_item, phase_item, prio_item):
                it.setData(Qt.UserRole, sid)

            self._table.setItem(r, 0, id_item)
            self._table.setItem(r, 1, task_item)
            self._table.setItem(r, 2, name_item)
            self._table.setItem(r, 3, phase_item)
            self._table.setItem(r, 4, prio_item)

        self._table.resizeColumnsToContents()
        self._on_selection_changed()

    # ---------- selection & history ----------
    def _selected_subtask_id(self) -> Optional[int]:
        items = self._table.selectedItems()
        if not items:
            return None
        sid = items[0].data(Qt.UserRole)
        try:
            return int(sid) if sid is not None else None
        except Exception:
            return None

    def _on_selection_changed(self):
        has_sel = self._selected_subtask_id() is not None
        self._btn_edit.setEnabled(has_sel)
        self._btn_delete.setEnabled(has_sel)

        if has_sel:
            self._load_timeline_for_selected()
        else:
            self._history.set_updates([])

    def _load_timeline_for_selected(self):
        sid = self._selected_subtask_id()
        if sid is None:
            self._history.set_updates([])
            return

        repo = self._get_updates_repo()
        updates = repo.list_updates_for_subtask(sid, order_desc=True)

        # Coalesce near-simultaneous updates (<= 2 seconds) and drop non-changes
        updates = self._coalesce_updates(updates, window_secs=2)
        updates = self._normalize_changes(updates)
        updates = self._decorate_updates(updates)

        self._history.set_updates(updates)

    def _get_updates_repo(self) -> SQLiteSubtaskUpdatesRepository:
        if self._updates_repo is None:
            # Reach into the repo to grab a sqlite3.Connection (consistent with other repos)
            try:
                conn = self._repo._conn()  # uses the repo's internal helper
            except Exception:
                # Fallback: try common attributes
                conn = getattr(self._repo, "conn", None) or getattr(self._repo, "_db_or_conn", None)
            self._updates_repo = SQLiteSubtaskUpdatesRepository(conn)
        return self._updates_repo

    # ---------- coalescing & decoration (mirror Tasks VM) ----------
    @staticmethod
    def _parse_ts(s: str | None) -> datetime | None:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", "")) if "T" in s else datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None

    @staticmethod
    def _merge_reason(flags: set[str], phase_changed: bool, prio_changed: bool) -> str:
        if phase_changed and prio_changed:
            return "update"
        if phase_changed:
            return "phase_change"
        if prio_changed:
            return "priority_change"
        if "create" in flags:
            return "create"
        if "note" in flags:
            return "note"
        return "update"

    def _coalesce_updates(self, updates: List[Dict[str, Any]], window_secs: int = 2) -> List[Dict[str, Any]]:
        if not updates:
            return []
        items = list(updates)  # newest-first
        out: List[Dict[str, Any]] = []
        cur: List[Dict[str, Any]] = []

        def flush(group: List[Dict[str, Any]]):
            if not group:
                return
            reasons = {(u.get("reason") or "update").lower() for u in group}
            merged = dict(group[0])  # newest
            merged["updated_at_utc"] = group[0].get("updated_at_utc")

            # notes (unique, newest-first)
            notes = [(u.get("note") or "").strip() for u in group if (u.get("note") or "").strip()]
            if notes:
                seen, uniq = set(), []
                for n in notes:
                    if n in seen:
                        continue
                    seen.add(n)
                    uniq.append(n)
                merged["note"] = "\n".join(uniq)

            # phase merge: earliest old -> latest new
            olds = [u.get("old_phase_id") for u in group if u.get("old_phase_id") is not None]
            news = [u.get("new_phase_id") for u in group if u.get("new_phase_id") is not None]
            merged["old_phase_id"] = olds[-1] if olds else None
            merged["new_phase_id"] = news[0] if news else None

            # priority merge: earliest old -> latest new
            p_olds = [u.get("old_priority_id") for u in group if u.get("old_priority_id") is not None]
            p_news = [u.get("new_priority_id") for u in group if u.get("new_priority_id") is not None]
            merged["old_priority_id"] = p_olds[-1] if p_olds else None
            merged["new_priority_id"] = p_news[0] if p_news else None

            phase_changed = merged["old_phase_id"] is not None and merged["new_phase_id"] is not None and int(merged["old_phase_id"]) != int(merged["new_phase_id"])
            prio_changed = merged["old_priority_id"] is not None and merged["new_priority_id"] is not None and int(merged["old_priority_id"]) != int(merged["new_priority_id"])

            merged["reason"] = SubtasksTab._merge_reason(reasons, phase_changed, prio_changed)
            out.append(merged)

        prev = self._parse_ts(items[0].get("updated_at_utc"))
        cur.append(items[0])
        for u in items[1:]:
            ts = self._parse_ts(u.get("updated_at_utc"))
            same_bucket = (prev and ts and abs((prev - ts).total_seconds()) <= window_secs) or (u.get("updated_at_utc") == cur[0].get("updated_at_utc"))
            if same_bucket:
                cur.append(u)
            else:
                flush(cur)
                cur = [u]
                prev = ts
        flush(cur)
        return out

    def _normalize_changes(self, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for u in updates:
            w = dict(u)
            # Phase change only if real
            op, np = w.get("old_phase_id"), w.get("new_phase_id")
            if not (op is not None and np is not None and str(op) != str(np)):
                w["old_phase_id"] = None
                w["new_phase_id"] = None
            # Priority change only if real
            opr, npr = w.get("old_priority_id"), w.get("new_priority_id")
            if not (opr is not None and npr is not None and str(opr) != str(npr)):
                w["old_priority_id"] = None
                w["new_priority_id"] = None
            out.append(w)
        return out

    def _decorate_updates(self, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for u in updates:
            u = dict(u)
            # Add *_name lookups when IDs exist
            if u.get("old_phase_id") is not None:
                u["old_phase_name"] = self._PHASE_NAMES.get(int(u["old_phase_id"]), str(u["old_phase_id"]))
            if u.get("new_phase_id") is not None:
                u["new_phase_name"] = self._PHASE_NAMES.get(int(u["new_phase_id"]), str(u["new_phase_id"]))
            if u.get("old_priority_id") is not None:
                u["old_priority_name"] = self._PRIORITY_NAMES.get(int(u["old_priority_id"]), str(u["old_priority_id"]))
            if u.get("new_priority_id") is not None:
                u["new_priority_name"] = self._PRIORITY_NAMES.get(int(u["new_priority_id"]), str(u["new_priority_id"]))
            u["updated_local"] = u.get("updated_at_utc")
            out.append(u)
        return out

    # ---------- repo helpers ----------
    def _refresh_task_names_cache(self, project_id: int):
        # Use the subtask repo's API to get a mapping of tasks for this project, including tasks without subtasks.
        try:
            self._tasks_by_id = self._repo.list_tasks_for_project(project_id)  # {id: name}
        except Exception:
            self._tasks_by_id = {}
            # Fallback: scan rows for tasks present
            for r in self._all_rows:
                tid = r.get("task_id")
                if tid is not None and tid not in self._tasks_by_id:
                    self._tasks_by_id[tid] = f"Task {tid}"

    # ---------- CRUD ----------
    def _on_new(self):
        if self._project_id is None:
            return
        tid = self._task_filter.currentData()
        if tid is None:
            QMessageBox.information(self, "Pick a task", "Choose a task from the drop-down before adding a subtask.")
            return

        dlg = SubtaskEditorDialog(
            self,
            title="New Subtask",
            name="",
            description="",
            phase_id=1,
            priority_id=2,
        )
        if dlg.exec() != int(QDialog.DialogCode.Accepted):
            return

        name, desc, phase_id, priority_id, note = dlg.values()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please provide a subtask name.")
            return

        self._repo.create_subtask(
            task_id=tid,
            name=name,
            description=desc,
            phase_id=phase_id,
            priority_id=priority_id,
            note_on_create=note or "Created via UI",
        )
        # reload current filter
        self._all_rows = self._repo.list_subtasks_for_project(self._project_id)
        self._apply_filter()

    def _on_edit(self):
        sid = self._selected_subtask_id()
        if sid is None:
            return

        rec = self._repo.get_subtask(sid)
        if not rec:
            QMessageBox.warning(self, "Not found", f"Could not load subtask #{sid}.")
            return

        dlg = SubtaskEditorDialog(
            self,
            title="Edit Subtask",
            name=rec.get("name") or "",
            description=rec.get("description") or "",
            phase_id=int(rec.get("phase_id", 1)),
            priority_id=int(rec.get("priority_id", 2)),
            mode="edit",
        )
        if dlg.exec() != int(QDialog.DialogCode.Accepted):
            return

        name, desc, phase_id, priority_id, note = dlg.values()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please provide a subtask name.")
            return

        # Apply only what changed
        changed = False
        if int(phase_id) != int(rec.get("phase_id", 1)):
            self._repo.change_subtask_phase(sid, int(phase_id), reason="phase_change", note=note or None)
            changed = True
        if int(priority_id) != int(rec.get("priority_id", 2)):
            self._repo.set_subtask_priority(sid, int(priority_id), note=note or None)
            changed = True
        if note and not changed:
            # record a note without other changes
            try:
                self._repo.update_subtask_fields(sid, note=note)
            except Exception:
                pass

        # Reload rows and refresh timeline for selected subtask
        self._all_rows = self._repo.list_subtasks_for_project(self._project_id)
        self._apply_filter()
        self._load_timeline_for_selected()

    def _on_delete(self):
        sid = self._selected_subtask_id()
        if sid is None:
            return
        if QMessageBox.question(self, "Delete Subtask", f"Are you sure you want to delete subtask #{sid}?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self._repo.delete_subtask(sid)
            self._all_rows = self._repo.list_subtasks_for_project(self._project_id)
            self._apply_filter()
            self._history.set_updates([])
