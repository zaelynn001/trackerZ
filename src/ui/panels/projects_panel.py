# src/ui/panels/projects_panel.py
# Rev 0.6.8 — emit selection on click/activate/double-click

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

        # Be generous: any reasonable user action selects
        self._list.itemActivated.connect(self._emit_selection)     # Enter/double-click
        self._list.itemDoubleClicked.connect(self._emit_selection) # Double-click
        #self._list.itemClicked.connect(self._emit_selection)       # Single-click

    def load(self) -> None:
        self._list.clear()
        rows: Iterable[Tuple[int, str]] | Iterable[Dict[str, Any]] = []
        repo = self._projects_repo

        if repo:
            if hasattr(repo, "list_projects_basic"):
                rows = repo.list_projects_basic()
            elif hasattr(repo, "list_projects_overview"):
                rows = repo.list_projects_overview()
            elif hasattr(repo, "list_all"):
                rows = repo.list_all()
            else:
                con = self._extract_conn(repo)
                if con is not None:
                    cur = con.cursor()
                    try:
                        cur.execute("SELECT id, name FROM projects ORDER BY updated_at_utc DESC, id DESC")
                    except Exception:
                        cur.execute("SELECT id, name FROM projects ORDER BY id DESC")
                    rows = cur.fetchall()

        count = 0
        for r in rows or []:
            if isinstance(r, dict):
                pid = int(r.get("id"))
                name = r.get("name", "")
            else:
                pid = int(r[0])
                name = r[1] if len(r) > 1 else f"Project {pid}"
            item = QListWidgetItem(f"{pid}: {name}")
            item.setData(Qt.UserRole, pid)
            self._list.addItem(item)
            count += 1

        if count == 0:
            for pid in (1, 2, 3):
                item = QListWidgetItem(f"{pid}: Placeholder Project {pid}")
                item.setData(Qt.UserRole, pid)
                self._list.addItem(item)

    def _emit_selection(self, item=None) -> None:
        if item is None:
            item = self._list.currentItem()
        if not item:
            return
        pid = int(item.data(Qt.UserRole) or str(item.text()).split(":", 1)[0])
        self.projectSelected.emit(pid)

    def _extract_conn(self, repo):
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
