# Rev 0.6.7 — show Project Phase & Priority (schema Rev 1.1.0)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QFormLayout,
    QGroupBox, QGridLayout, QSizePolicy, QHBoxLayout
)

class OverviewTab(QWidget):
    def __init__(self, projects_repo, tasks_repo, subtasks_repo, phases_repo=None, parent=None):
        super().__init__(parent)
        self._projects = projects_repo
        self._tasks = tasks_repo
        self._subtasks = subtasks_repo
        self._phases = phases_repo
        self._project_id = None
        self._phase_ids = {}
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self._lbl_id = QLabel("-")
        self._lbl_name = QLabel("-")
        self._lbl_desc = QLabel("-")
        self._lbl_created = QLabel("-")
        self._lbl_updated = QLabel("-")
        self._lbl_phase = QLabel("-")
        self._lbl_priority = QLabel("-")
        self._lbl_desc.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Project ID:", self._lbl_id)
        form.addRow("Name:", self._lbl_name)
        form.addRow("Description:", self._lbl_desc)
        form.addRow("Created (UTC):", self._lbl_created)
        form.addRow("Updated (UTC):", self._lbl_updated)
        form.addRow("Phase:", self._lbl_phase)
        form.addRow("Priority:", self._lbl_priority)

        box_summary = QGroupBox("Project Summary")
        box_summary.setLayout(form)
        root.addWidget(box_summary)

        # Aggregates (unchanged)
        self._lbl_tasks_total = QLabel("0")
        self._lbl_tasks_open = QLabel("0")
        self._lbl_tasks_inprog = QLabel("0")
        self._lbl_tasks_hiatus = QLabel("0")
        self._lbl_tasks_resolved = QLabel("0")
        self._lbl_tasks_closed = QLabel("0")
        self._lbl_subtasks_total = QLabel("0")

        grid = QGridLayout()
        r = 0
        grid.addWidget(QLabel("<b>Tasks</b>"), r, 0, 1, 2); r += 1
        for label, widget in [
            ("Total:", self._lbl_tasks_total),
            ("Open:", self._lbl_tasks_open),
            ("In Progress:", self._lbl_tasks_inprog),
            ("In Hiatus:", self._lbl_tasks_hiatus),
            ("Resolved:", self._lbl_tasks_resolved),
            ("Closed:", self._lbl_tasks_closed),
        ]:
            grid.addWidget(QLabel(label), r, 0)
            grid.addWidget(widget, r, 1)
            r += 1
        grid.addWidget(QLabel("<b>Subtasks</b>"), r, 0, 1, 2); r += 1
        grid.addWidget(QLabel("Total:"), r, 0)
        grid.addWidget(self._lbl_subtasks_total, r, 1)

        box_aggs = QGroupBox("Aggregates")
        box_aggs.setLayout(grid)
        root.addWidget(box_aggs)
        
        btn_edit = QPushButton("Edit Project…")
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(btn_edit)
        root.addLayout(btn_row)
        btn_edit.clicked.connect(self._open_project_editor)

        btn = QPushButton("Refresh")
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn.clicked.connect(self._refresh_clicked)
        root.addWidget(btn, alignment=Qt.AlignRight)
        root.addStretch(1)

    # ---------- Public API ----------
    def load(self, project_id: int):
        self._project_id = project_id
        self._ensure_phase_ids()
        self._load_project_fields()
        self._load_aggregates()

    @staticmethod
    def _fmt_ts(ts: str | None) -> str:
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

    def _refresh_clicked(self):
        if self._project_id is not None:
            self._load_project_fields()
            self._load_aggregates()

    # ---------- Data loading ----------
    def _get_project_row(self, project_id: int):
        conn = self._conn_for(self._projects) or self._conn_for(self._tasks)
        if not conn:
            return None
        cur = conn.cursor()
        # include phase_id, priority_id
        cur.execute(
            "SELECT id, name, description, created_at_utc, phase_id, priority_id FROM projects WHERE id = ?",
            (project_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))

    def _get_project_updated_utc(self, project_id: int) -> str:
        conn = self._conn_for(self._projects) or self._conn_for(self._tasks)
        if not conn:
            return ""
        cur = conn.cursor()
        table_name = None
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'project%update%';")
        found = cur.fetchone()
        if found:
            table_name = found[0]
        if not table_name:
            return ""
        try:
            cur.execute(f"SELECT MAX(updated_at_utc) FROM {table_name} WHERE project_id = ?", (project_id,))
            row = cur.fetchone()
            if not row or not row[0]:
                cur.execute(f"SELECT MAX(created_at_utc) FROM {table_name} WHERE project_id = ?", (project_id,))
                row = cur.fetchone()
            return row[0] if row and row[0] else ""
        except Exception:
            return ""

    @staticmethod
    def _priority_label(pid: int | None) -> str:
        names = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}
        return names.get(pid, "—")

    def _load_project_fields(self):
        p = self._get_project_row(self._project_id)
        if not p:
            for lbl in (self._lbl_id, self._lbl_name, self._lbl_desc, self._lbl_created, self._lbl_updated, self._lbl_phase, self._lbl_priority):
                lbl.setText("-")
            return
        self._lbl_id.setText(str(p.get("id", "")))
        self._lbl_name.setText(p.get("name", "") or "")
        self._lbl_desc.setText(p.get("description", "") or "")
        self._lbl_created.setText(self._fmt_ts(p.get("created_at_utc")))
        self._lbl_updated.setText(self._fmt_ts(self._get_project_updated_utc(self._project_id)))

        # New: show phase/priority
        phase_id = p.get("phase_id")
        self._lbl_phase.setText(self._fmt_phase(phase_id))
        self._lbl_priority.setText(self._priority_label(p.get("priority_id")))

    # ---------- Aggregates (unchanged) ----------
    def _load_aggregates(self):
        pid = self._project_id
        try:
            total_tasks = self._tasks.count_tasks_total(project_id=pid)
        except TypeError:
            total_tasks = 0
        self._lbl_tasks_total.setText(str(total_tasks))

        conn = self._conn_for(self._tasks) or self._conn_for(self._projects)
        if conn:
            cur = conn.cursor()
            def qcount(phase):
                cur.execute("SELECT COUNT(*) FROM tasks WHERE project_id=? AND phase_id=?", (pid, phase))
                r = cur.fetchone()
                return int(r[0]) if r else 0
            self._lbl_tasks_open.setText(str(qcount(1)))
            self._lbl_tasks_inprog.setText(str(qcount(2)))
            self._lbl_tasks_hiatus.setText(str(qcount(3)))
            self._lbl_tasks_resolved.setText(str(qcount(4)))
            self._lbl_tasks_closed.setText(str(qcount(5)))

        total_subs = 0
        if hasattr(self._subtasks, "count_subtasks_total_by_project"):
            try:
                total_subs = self._subtasks.count_subtasks_total_by_project(project_id=pid)
            except Exception:
                total_subs = 0
        elif conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*)
                FROM subtasks s
                JOIN tasks t ON t.id = s.task_id
                WHERE t.project_id = ?
                """,
                (pid,),
            )
            r = cur.fetchone()
            total_subs = int(r[0]) if r else 0

        self._lbl_subtasks_total.setText(str(total_subs))

    # ---------- Phase mapping ----------
    def _ensure_phase_ids(self):
        if self._phase_ids:
            return
        self._phase_ids.update({
            "Open": 1,
            "In Progress": 2,
            "In Hiatus": 3,
            "Resolved": 4,
            "Closed": 5,
        })

    def _fmt_phase(self, pid: int | None) -> str:
        if pid is None:
            return "—"
        # Names are stable; mirror reverse map from _phase_ids
        rev = {v: k for k, v in self._phase_ids.items()} if self._phase_ids else {
            1: "Open", 2: "In Progress", 3: "In Hiatus", 4: "Resolved", 5: "Closed"
        }
        return rev.get(pid, "—")

    # ---------- Connection helper ----------
    def _conn_for(self, repo):
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
        
    def _open_project_editor(self):
        if self._project_id is None:
            return
        try:
            from ui.project_editor_dialog import ProjectEditorDialog
        except Exception:
            return
        dlg = ProjectEditorDialog(project_id=self._project_id, projects_repo=self._projects, phases_repo=self._phases, parent=self)
        if dlg.exec():
            # refresh details after changes
            self._load_project_fields()
            self._load_aggregates()

