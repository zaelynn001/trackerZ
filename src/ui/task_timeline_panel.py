# Rev 0.6.7 — show phase/priority transitions + reason badges
# --- keep your imports/constants at top ---
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QSizePolicy, QHBoxLayout

_TEXT   = "#222222"
_HEAD   = "#111111"
_CARD   = "#fafafa"
_BORDER = "#e5e5e5"

_PHASE = {1: "Open", 2: "In Progress", 3: "In Hiatus", 4: "Resolved", 5: "Closed"}
_PRIO  = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}

_REASON_STYLES = {
    "create":                   ("#00bb66", "#e6fff5"),
    "update":                   ("#0066cc", "#e6f2ff"),
    "note":                     ("#555555", "#f2f2f2"),
    "phase_change":             ("#aa4400", "#fff2e6"),
    "priority_change":          ("#aa0066", "#ffe6f5"),
    "subtask_update":           ("#555555", "#f2f2f2"),
    "subtask_priority_change":  ("#aa0066", "#ffe6f5"),
}

def _badge(reason: str) -> QLabel:
    fg, bg = _REASON_STYLES.get(reason, ("#444444", "#eeeeee"))
    lab = QLabel(reason.replace("_", " "))
    lab.setStyleSheet(
        "QLabel {"
        f"  color: {fg};"
        f"  background-color: {bg};"
        f"  border: 1px solid {fg};"
        "  border-radius: 8px;"
        "  padding: 2px 6px;"
        "  font-size: 11px;"
        "}"
    )
    lab.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    return lab

def _phase_label(pid: int | None) -> str:
    return _PHASE.get(int(pid)) if pid is not None else "—"

def _prio_label(pid: int | None) -> str:
    return _PRIO.get(int(pid)) if pid is not None else "—"


class TaskTimelinePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(6, 6, 6, 6)
        self._root.setSpacing(8)

    # --- recursive clear prevents stale child layouts/widgets ---
    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            child_layout = item.layout()
            child_widget = item.widget()
            if child_layout is not None:
                self._clear_layout(child_layout)  # recurse
                # no explicit delete needed; Qt owns it once detached
            if child_widget is not None:
                child_widget.deleteLater()

    def clear(self):
        self._clear_layout(self._root)

    # In TaskTimelinePanel.set_updates(), replace the body with stricter filtering:
    def set_updates(self, updates: list[dict]):
        self.clear()
        if not updates:
            lbl = QLabel("No history yet.")
            lbl.setStyleSheet(f"color: {_TEXT};")
            self._root.addWidget(lbl)
            self._root.addStretch(1)
            return

        rendered = 0
        for u in updates:
            w = self._render_update(u)
            if w is None:
                continue
            self._root.addWidget(w)
            rendered += 1

        if rendered == 0:
            lbl = QLabel("No meaningful changes yet.")
            lbl.setStyleSheet(f"color: {_TEXT};")
            self._root.addWidget(lbl)

        self._root.addStretch(1)


    # In _render_update(), add “only-if-changed” logic and return None if empty
    def _render_update(self, u: dict) -> QFrame | None:
        old_phase = u.get("old_phase_id")
        new_phase = u.get("new_phase_id")
        old_prio  = u.get("old_priority_id")
        new_prio  = u.get("new_priority_id")
        note = (u.get("note") or "").strip()

        changed_phase = (
            old_phase is not None and new_phase is not None and
            str(old_phase) != str(new_phase)
        )
        changed_prio = (
            old_prio is not None and new_prio is not None and
            str(old_prio) != str(new_prio)
        )
        has_note = bool(note)

        # If there is nothing meaningful to show, don’t render a card.
        if not (changed_phase or changed_prio or has_note):
            return None

        # --- existing card creation code below (styling + header) ---
        box = QFrame()
        box.setFrameShape(QFrame.StyledPanel)
        box.setStyleSheet(
            "QFrame {"
            f"  background-color: {_CARD};"
            f"  border: 1px solid {_BORDER};"
            "  border-radius: 8px;"
            "}"
        )

        lay = QVBoxLayout(box)
        lay.setContentsMargins(8, 6, 8, 8)
        lay.setSpacing(6)

        head = QHBoxLayout()
        ts = u.get("updated_at_utc") or ""
        reason = (u.get("reason") or "update").lower()
        ts_lbl = QLabel(ts)
        ts_lbl.setStyleSheet(f"color: {_HEAD}; font-weight: 600;")
        head.addWidget(ts_lbl)
        head.addSpacing(8)
        head.addWidget(_badge(reason))
        head.addStretch(1)
        lay.addLayout(head)

        if changed_phase:
            phase_line = QLabel(f"Phase: {_phase_label(old_phase)} → {_phase_label(new_phase)}")
            phase_line.setStyleSheet(f"color: {_TEXT};")
            lay.addWidget(phase_line)

        if changed_prio:
            prio_line = QLabel(f"Priority: {_prio_label(old_prio)} → {_prio_label(new_prio)}")
            prio_line.setStyleSheet(f"color: {_TEXT};")
            lay.addWidget(prio_line)

        if has_note:
            note_lbl = QLabel(note)
            note_lbl.setWordWrap(True)
            note_lbl.setStyleSheet(f"color: {_TEXT};")
            lay.addWidget(note_lbl)

        return box



