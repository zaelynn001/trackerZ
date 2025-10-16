# Rev 0.0.1

# =========================
# File: src/ui/workspace.py
# =========================
from __future__ import annotations
from typing import Optional, Dict
from PySide6.QtWidgets import QWidget, QStackedWidget, QVBoxLayout


class WorkspaceStack(QWidget):
    """Host inner panels and provide keyed navigation."""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._stack = QStackedWidget(self)
        self._keys: Dict[str, int] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._stack)
        
    def add_panel(self, key: str, panel: QWidget) -> None:
        self._keys[key] = self._stack.addWidget(panel)
        
    def show_panel(self, key: str) -> None:
        idx = self._keys.get(key, -1)
        if idx >= 0:
            self._stack.setCurrentIndex(idx)
            
    def current_key(self) -> Optional[str]:
        idx = self._stack.currentIndex()
        for k, i in self._keys.items():
            if i == idx:
                return k
        return None
