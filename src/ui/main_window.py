# Rev 0.6.5
# trackerZ — Main Window with Phase + Priority columns
# Columns: ID | Name | Description | Phase | Priority | Created (UTC) | Updated (UTC) | Total Tasks

from __future__ import annotations
import typing as _t

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDockWidget
)

from ui.project_overview_window import ProjectOverviewWindow
from ui.window_mode import lock_maximized


class MainWindow(QMainWindow):
    def __init__(
        self,
        *,
        projects_repo,
        tasks_repo,
        subtasks_repo,
        phases_repo,
        attachments_repo=None,
        expenses_repo=None,
        logfile: str | None = None,
        parent=None,
        **_ignored,
    ):
        super().__init__(parent)
        self._projects_repo = projects_repo
        self._tasks_repo = tasks_repo
        self._subtasks_repo = subtasks_repo
        self._phases_repo = phases_repo
        self._attachments_repo = attachments_repo
        self._expenses_repo = expenses_repo
        self._logfile = logfile

        self._phase_map: dict[int, str] = {}
        self._ensure_phase_map()

        self.setWindowTitle("trackerZ — Projects")
        self.resize(1100, 720)

        # ---- central ----
        central = QWidget(self)
        v = QVBoxLayout(central)

        top_bar = QHBoxLayout()
        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.clicked.connect(self._reload_projects)
        top_bar.addWidget(self._btn_refresh)
        top_bar.addStretch(1)
        v.addLayout(top_bar)

        # ID | Name | Description | Phase | Priority | Created | Updated | Total
        self._tbl = QTableWidget(0, 8, self)
        self._tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self._tbl.setSelectionMode(QTableWidget.SingleSelection)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.setSortingEnabled(True)
        self._tbl.verticalHeader().setVisible(False)

        self._tbl.setHorizontalHeaderLabels([
            "ID", "Name", "Description", "Phase", "Priority", "Created (UTC)", "Updated (UTC)", "Total Tasks"
        ])
        h = self._tbl.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        h.setSectionResizeMode(1, QHeaderView.Stretch)            # Name
        h.setSectionResizeMode(2, QHeaderView.Stretch)            # Description
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)   # Phase
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)   # Priority
        h.setSectionResizeMode(5, QHeaderView.ResizeToContents)   # Created
        h.setSectionResizeMode(6, QHeaderView.ResizeToContents)   # Updated
        h.setSectionResizeMode(7, QHeaderView.ResizeToContents)   # Total Tasks

        self._tbl.doubleClicked.connect(self._open_selected_project)
        v.addWidget(self._tbl)
        self.setCentralWidget(central)
        lock_maximized(self, lock_resize=True) 

        # ---- optional diagnostics dock ----
        try:
            from ui.diagnostics_panel import DiagnosticsPanel
            dock = QDockWidget("Diagnostics", self)
            dock.setObjectName("DiagnosticsDock")
            dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
            panel = DiagnosticsPanel(self)
            dock.setWidget(panel)
            self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        except Exception:
            pass

        # initial load
        self._reload_projects()

    # -------------------- data loading --------------------

    def _reload_projects(self):
        rows = self._fetch_projects_table_rows()
        self._tbl.setRowCount(0)
        self._tbl.setSortingEnabled(False)
        for r in rows:
            self._append_project_row(r)
        self._tbl.setSortingEnabled(True)

    def _fetch_projects_table_rows(self) -> list[dict]:
        """
        Returns rows with:
          id, name, description, phase_id, priority_id,
          created_at_utc, updated_at_utc (latest from project*_updates),
          tasks_total
        """
        conn = self._conn_for(self._projects_repo) or self._conn_for(self._tasks_repo)
        if not conn:
            return []

        cur = conn.cursor()

        # Detect updates table: project_updates OR projects_updates
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'project%update%';")
        found = cur.fetchone()
        updates_table = found[0] if found else None

        if updates_table:
            sql = f"""
                SELECT
                    p.id,
                    p.name,
                    COALESCE(p.description, '') AS description,
                    p.phase_id,
                    p.priority_id,
                    p.created_at_utc,
                    (SELECT MAX(u.updated_at_utc) FROM {updates_table} u WHERE u.project_id = p.id) AS updated_at_utc,
                    (SELECT COUNT(1) FROM tasks t WHERE t.project_id = p.id) AS tasks_total
                FROM projects p
                ORDER BY p.id ASC
            """
        else:
            sql = """
                SELECT
                    p.id,
                    p.name,
                    COALESCE(p.description, '') AS description,
                    p.phase_id,
                    p.priority_id,
                    p.created_at_utc,
                    NULL AS updated_at_utc,
                    (SELECT COUNT(1) FROM tasks t WHERE t.project_id = p.id) AS tasks_total
                FROM projects p
                ORDER BY p.id ASC
            """

        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        return [{cols[i]: row[i] for i in range(len(cols))} for row in cur.fetchall()]

    def _append_project_row(self, rec: dict):
        row = self._tbl.rowCount()
        self._tbl.insertRow(row)

        pid = rec.get("id")

        # ID
        item_id = QTableWidgetItem(str(pid if pid is not None else ""))
        item_id.setData(Qt.UserRole, pid)
        item_id.setFlags(item_id.flags() ^ Qt.ItemIsEditable)
        self._tbl.setItem(row, 0, item_id)

        # Name
        name = rec.get("name") or ""
        item_name = QTableWidgetItem(name)
        item_name.setFlags(item_name.flags() ^ Qt.ItemIsEditable)
        self._tbl.setItem(row, 1, item_name)

        # Description
        desc = rec.get("description") or ""
        item_desc = QTableWidgetItem(desc)
        item_desc.setFlags(item_desc.flags() ^ Qt.ItemIsEditable)
        self._tbl.setItem(row, 2, item_desc)

        # Phase (name only; fallback to ID if unknown)
        phase_id = rec.get("phase_id")
        phase_label = self._phase_label(phase_id)
        item_phase = QTableWidgetItem(phase_label)
        item_phase.setFlags(item_phase.flags() ^ Qt.ItemIsEditable)
        item_phase.setData(Qt.UserRole, int(phase_id) if phase_id is not None else -1)
        self._tbl.setItem(row, 3, item_phase)

        # Priority (name only)
        prio_id = rec.get("priority_id")
        prio_label = self._priority_label(prio_id)
        item_prio = QTableWidgetItem(prio_label)
        item_prio.setFlags(item_prio.flags() ^ Qt.ItemIsEditable)
        item_prio.setData(Qt.UserRole, int(prio_id) if prio_id is not None else -1)
        self._tbl.setItem(row, 4, item_prio)

        # Created (UTC)
        created_raw = rec.get("created_at_utc")
        item_created = QTableWidgetItem(self._fmt_ts(created_raw))
        item_created.setFlags(item_created.flags() ^ Qt.ItemIsEditable)
        item_created.setData(Qt.UserRole, created_raw or "")
        self._tbl.setItem(row, 5, item_created)

        # Updated (UTC)
        updated_raw = rec.get("updated_at_utc")
        item_updated = QTableWidgetItem(self._fmt_ts(updated_raw))
        item_updated.setFlags(item_updated.flags() ^ Qt.ItemIsEditable)
        item_updated.setData(Qt.UserRole, updated_raw or "")
        self._tbl.setItem(row, 6, item_updated)

        # Total Tasks
        total = int(rec.get("tasks_total", 0) or 0)
        item_total = QTableWidgetItem(str(total))
        item_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item_total.setFlags(item_total.flags() ^ Qt.ItemIsEditable)
        item_total.setData(Qt.UserRole, total)
        self._tbl.setItem(row, 7, item_total)

    # -------------------- actions --------------------

    def _open_selected_project(self):
        idxs = self._tbl.selectionModel().selectedRows()
        if not idxs:
            return
        row = idxs[0].row()
        pid_item = self._tbl.item(row, 0)
        if not pid_item:
            return
        project_id = int(pid_item.data(Qt.UserRole) or pid_item.text())
        self._open_project_overview(project_id)

    def _open_project_overview(self, project_id: int):
        win = ProjectOverviewWindow(
            project_id,
            self._projects_repo,
            self._tasks_repo,
            self._subtasks_repo,
            self._phases_repo,
            attachments_repo=self._attachments_repo,
            expenses_repo=self._expenses_repo,
            parent=self,
        )
        win.show()

    # -------------------- utils --------------------

    def _ensure_phase_map(self) -> None:
        """phase_id → name mapping via phases_repo.list_phases(), with safe fallback."""
        self._phase_map.clear()
        try:
            for p in self._phases_repo.list_phases():
                self._phase_map[int(p["id"])] = p["name"]
        except Exception:
            # Fallback to canonical set
            self._phase_map.update({1: "Open", 2: "In Progress", 3: "In Hiatus", 4: "Resolved", 5: "Closed"})

    def _phase_label(self, phase_id: _t.Optional[int]) -> str:
        if phase_id is None:
            return "—"
        return self._phase_map.get(int(phase_id), str(phase_id))

    @staticmethod
    def _priority_label(pid: _t.Optional[int]) -> str:
        names = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}
        return names.get(pid, "—")

    @staticmethod
    def _fmt_ts(ts: _t.Optional[str]) -> str:
        """Return human-readable UTC like 'Oct 14 2025 19:41 UTC' or '—'."""
        if not ts:
            return "—"
        import datetime
        try:
            if ts.endswith("Z"):
                ts = ts[:-1]
            dt = datetime.datetime.fromisoformat(ts)
            return dt.strftime("%b %d %Y %H:%M UTC")
        except Exception:
            return ts

    def _conn_for(self, repo):
        # Align with your repositories’ connection patterns
        if hasattr(repo, "_conn"):
            try:
                return repo._conn()
            except Exception:
                pass
        if hasattr(repo, "conn"):
            c = getattr(repo, "conn")
            if c:
                return c
        if hasattr(repo, "_db"):
            inner = getattr(repo, "_db")
            if hasattr(inner, "conn"):
                return getattr(inner, "conn")
        if hasattr(repo, "_db_or_conn"):
            inner = getattr(repo, "_db_or_conn")
            if hasattr(inner, "conn"):
                return getattr(inner, "conn")
        return None
