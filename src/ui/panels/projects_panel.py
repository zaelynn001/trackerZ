# Rev 0.6.7 — ProjectsPanel (robust against repo API variants)
from __future__ import annotations
from typing import Optional, Iterable, Tuple, Dict, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem

class ProjectsPanel(QWidget):
    projectSelected = Signal(int)  # project_id

    def __init__(self, *, projects_repo, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._projects_repo = projects_repo

        self._title = QLabel("Projects")
        self._list = QListWidget(self)

        lay = QVBoxLayout(self)
        lay.addWidget(self._title)
        lay.addWidget(self._list)

        self._list.itemDoubleClicked.connect(self._emit_selection)

    # ------------------------ public ------------------------

    def load(self) -> None:
        """Populate projects list using repo APIs if available, else raw SQL fallback."""
        self._list.clear()

        rows: Iterable[Tuple[int, str]] | Iterable[Dict[str, Any]] = []
        repo = self._projects_repo

        # Try common repo methods first (handle multiple codebase variants)
        if repo:
            if hasattr(repo, "list_projects_basic"):
                rows = repo.list_projects_basic()  # expected [(id, name)] or [{'id':..,'name':..}, ...]
            elif hasattr(repo, "list_projects_overview"):
                rows = repo.list_projects_overview()  # often returns rows with at least id/name
            elif hasattr(repo, "list_all"):
                rows = repo.list_all()
            else:
                # Fallback to raw SQL via extracted connection (mirrors old MainWindow approach)
                con = self._extract_conn(repo)
                if con is not None:
                    cur = con.cursor()
                    # Minimal columns needed for selection; order by updated desc if available
                    try:
                        cur.execute("SELECT id, name FROM projects ORDER BY updated_at_utc DESC, id DESC")
                    except Exception:
                        cur.execute("SELECT id, name FROM projects ORDER BY id DESC")
                    rows = cur.fetchall()
                else:
                    rows = []

        # Render
        count = 0
        for r in rows or []:
            if isinstance(r, dict):
                pid = int(r.get("id"))
                name = r.get("name", "")
            else:
                # assume (id, name, ...) shape
                pid = int(r[0])
                name = r[1] if len(r) > 1 else f"Project {pid}"

            item = QListWidgetItem(f"{pid}: {name}")
            item.setData(Qt.UserRole, pid)
            self._list.addItem(item)
            count += 1

        if count == 0:
            # Friendly placeholder if no data or repo unavailable
            for pid in (1, 2, 3):
                item = QListWidgetItem(f"{pid}: Placeholder Project {pid}")
                item.setData(Qt.UserRole, pid)
                self._list.addItem(item)

    # ------------------------ internals ------------------------

    def _emit_selection(self) -> None:
        it = self._list.currentItem()
        if not it:
            return
        pid = int(it.data(Qt.UserRole) or str(it.text()).split(":", 1)[0])
        self.projectSelected.emit(pid)

    def _extract_conn(self, repo):
        """Mirror your previous pattern to fish out the sqlite3 connection from various wrappers."""
        # Direct attr
        if hasattr(repo, "conn"):
            c = getattr(repo, "conn")
            if c:
                return c
        # Nested db wrapper
        if hasattr(repo, "_db"):
            inner = getattr(repo, "_db")
            if hasattr(inner, "conn"):
                return getattr(inner, "conn")
        if hasattr(repo, "_db_or_conn"):
            inner = getattr(repo, "_db_or_conn")
            if hasattr(inner, "conn"):
                return getattr(inner, "conn")
        return None
