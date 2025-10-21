# Rev 0.6.8 — Show ALL change lines (phase + priority if both), no phantom badges
from __future__ import annotations
from typing import List, Dict, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QSizePolicy


class HistoryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._title = QLabel("History")
        self._title.setObjectName("HistoryPanelTitle")
        self._title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        header = QHBoxLayout()
        header.addWidget(self._title, 1)

        self._list_layout = QVBoxLayout()
        self._list_layout.setContentsMargins(12, 8, 12, 12)
        self._list_layout.setSpacing(8)

        body = QWidget()
        body.setObjectName("HistoryPanelBody")
        body.setLayout(self._list_layout)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(body)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addLayout(header)
        root.addWidget(self._scroll, 1)

        self.set_updates([])

    # ---- Public API
    def set_updates(self, updates: List[Dict[str, Any]]) -> None:
        self._clear()
        if not updates:
            self._list_layout.addWidget(self._empty_state())
            self._list_layout.addStretch(1)
            return
        for u in updates:
            self._list_layout.addWidget(self._make_card(u))
        self._list_layout.addStretch(1)

    # ---- Internals
    def _clear(self) -> None:
        while (item := self._list_layout.takeAt(0)):
            w = item.widget()
            if w: w.deleteLater()

    def _empty_state(self) -> QWidget:
        box = QFrame()
        box.setFrameShape(QFrame.StyledPanel)
        lay = QVBoxLayout(box)
        lbl = QLabel("No history yet. Edit a task or change its phase/priority to see updates here.")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setObjectName("HistoryEmpty")
        lay.addWidget(lbl)
        return box

    def _make_card(self, u: Dict[str, Any]) -> QWidget:
        ts = u.get("updated_local") or u.get("updated_at_utc") or ""
        reason = (u.get("reason") or "update").lower()

        card = QFrame()
        card.setObjectName("HistoryCard")
        card.setFrameShape(QFrame.StyledPanel)
        card.setProperty("historyReason", reason)

        outer = QVBoxLayout(card)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(6)

        # row 1: timestamp + badge
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        ts_lbl = QLabel(ts); ts_lbl.setObjectName("HistoryTimestamp"); ts_lbl.setProperty("dim", True)
        badge = QLabel(self._badge_text(reason)); badge.setObjectName("HistoryBadge"); badge.setProperty("badgeKind", reason)
        badge.setMargin(4); badge.setAlignment(Qt.AlignCenter); badge.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        badge.setStyleSheet("QLabel#HistoryBadge { border-radius: 6px; padding: 2px 6px; }")
        row1.addWidget(ts_lbl, 1); row1.addWidget(badge, 0, Qt.AlignRight)
        outer.addLayout(row1)

        # summary lines (can be multiple)
        for line in self._summary_lines(u):
            s_lbl = QLabel(line); s_lbl.setObjectName("HistorySummary")
            outer.addWidget(s_lbl)

        # note (optional)
        note = (u.get("note") or "").strip()
        if note:
            note_lbl = QLabel(note); note_lbl.setWordWrap(True); note_lbl.setObjectName("HistoryNote")
            outer.addWidget(note_lbl)

        return card

    @staticmethod
    def _badge_text(reason: str) -> str:
        mapping = {
            "phase_change": "phase change",
            "priority_change": "priority change",
            "create": "create",
            "note": "note",
            "update": "update",
        }
        return mapping.get(reason, reason)

    @staticmethod
    def _summary_lines(u: Dict[str, Any]) -> List[str]:
        lines: List[str] = []

        # Only produce lines if both sides are present (ViewModel already nulls non-changes)
        if u.get("old_phase_id") is not None and u.get("new_phase_id") is not None:
            oldn = u.get("old_phase_name") or str(u.get("old_phase_id"))
            newn = u.get("new_phase_name") or str(u.get("new_phase_id"))
            lines.append(f"Phase: {oldn} → {newn}")

        if u.get("old_priority_id") is not None and u.get("new_priority_id") is not None:
            oldp = u.get("old_priority_name") or str(u.get("old_priority_id"))
            newp = u.get("new_priority_name") or str(u.get("new_priority_id"))
            lines.append(f"Priority: {oldp} → {newp}")

        if not lines and (u.get("reason") == "create"):
            lines.append("Created")

        return lines
