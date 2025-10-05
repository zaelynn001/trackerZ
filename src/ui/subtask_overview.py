# src/ui/subtask_overview.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QTabWidget, QMessageBox
)
from PySide6.QtCore import Qt
from src.models.dao import get_subtask, list_subtask_updates
from src.ui.subtask_editor import SubtaskEditorDialog

class _Table(QTableWidget):
    def __init__(self, headers, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setEditTriggers(QTableWidget.NoEditTriggers)

    def load_rows(self, rows, keys):
        self.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, key in enumerate(keys):
                self.setItem(r, c, QTableWidgetItem(str(row.get(key, ""))))

class SubtaskOverviewDialog(QDialog):
    def __init__(self, subtask_id: int, parent=None):
        super().__init__(parent)
        self.subtask_id = subtask_id
        self.setWindowTitle(f"Subtask Overview — #{subtask_id}")
        self.resize(800, 520)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.btn_edit = QPushButton("Edit Subtask")
        self.btn_edit.clicked.connect(self._open_editor)

        top = QHBoxLayout()
        top.addWidget(self.title_label, 1)
        top.addWidget(self.btn_edit, 0, Qt.AlignRight)

        self.tabs = QTabWidget()
        self.tab_details = QWidget()
        self.tab_history = QWidget()
        self.tabs.addTab(self.tab_details, "Details")
        self.tabs.addTab(self.tab_history, "History")

        # details
        self.details_num = QLabel("")
        self.details_title = QLabel("")
        self.details_desc = QLabel("")
        self.details_desc.setWordWrap(True)
        self.details_phase = QLabel("")
        self.details_priority = QLabel("")
        self.details_times = QLabel("")

        form = QFormLayout(self.tab_details)
        form.addRow("Subtask #", self.details_num)
        form.addRow("Title", self.details_title)
        form.addRow("Description", self.details_desc)
        form.addRow("Phase", self.details_phase)
        form.addRow("Priority", self.details_priority)
        form.addRow("Created / Updated (UTC)", self.details_times)

        # history
        self.history_table = _Table(["When (UTC)", "Reason", "Old Phase", "New Phase", "Note"], parent=self.tab_history)
        layh = QVBoxLayout(self.tab_history)
        layh.addWidget(self.history_table)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(self.tabs)

        self._load()

    def _load(self):
        s = get_subtask(self.subtask_id)
        if not s:
            QMessageBox.critical(self, "Not found", f"Subtask {self.subtask_id} not found")
            self.reject()
            return
        self.title_label.setText(f"{s.get('title','')} — {s.get('subtask_number','')}")
        self.details_num.setText(s.get("subtask_number",""))
        self.details_title.setText(s.get("title",""))
        self.details_desc.setText(s.get("description","") or "—")
        self.details_phase.setText(s.get("phase_name",""))
        self.details_priority.setText(s.get("priority","") or "—")
        self.details_times.setText(f"{s.get('created_at_utc','')} / {s.get('updated_at_utc','')}")
        # history
        hrows = list_subtask_updates(self.subtask_id)
        self.history_table.load_rows(hrows, ["occurred_at_utc","reason","old_phase","new_phase","note"])

    def _open_editor(self):
        dlg = SubtaskEditorDialog(self.subtask_id, parent=self)
        if dlg.exec():
            self._load()

