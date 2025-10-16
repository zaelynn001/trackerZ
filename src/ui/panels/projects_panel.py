# Rev 0.0.1

# =====================================
# File: src/ui/panels/projects_panel.py
# =====================================
from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
)


class ProjectsPanel(QWidget):
    projectSelected = Signal(int) # project_id
    
    def __init__(self, *, projects_repo, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._projects_repo = projects_repo
        self._title = QLabel("Projects")
        self._list = QListWidget(self)
        lay = QVBoxLayout(self)
        lay.addWidget(self._title)
        lay.addWidget(self._list)
        self._list.itemDoubleClicked.connect(self._emit_selection)
        
    def load(self) -> None:
        self._list.clear()
        if not self._projects_repo:
            for pid in (1, 2, 3):
                self._list.addItem(f"{pid}: Placeholder Project {pid}")
            return
        rows = self._projects_repo.list_projects_basic() # expected: [(id, name), ...] or iterable of dicts
        for r in rows:
            if isinstance(r, dict):
                pid, name = int(r.get("id")), r.get("name", "")
            else:
                pid, name = int(r[0]), r[1]
            item = QListWidgetItem(f"{pid}: {name}")
            item.setData(Qt.UserRole, pid)
            self._list.addItem(item)
            
    def _emit_selection(self):
        it = self._list.currentItem()
        if not it:
            return
        pid = int(it.data(Qt.UserRole) or str(it.text()).split(":", 1)[0])
        self.projectSelected.emit(pid)
