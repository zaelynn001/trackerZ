# src/ui/task_overview.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QTabWidget, QMessageBox
)
from PySide6.QtCore import Qt
from src.models.dao import get_task, list_subtasks_for_project, list_task_updates
from src.ui.task_editor import TaskEditorDialog

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

class TaskOverviewDialog(QDialog):
    def __init__(self, task_id: int, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.setWindowTitle(f"Task Overview — #{task_id}")
        self.resize(900, 560)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.btn_edit = QPushButton("Edit Task")
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
        self.details_tasknum = QLabel("")
        self.details_title = QLabel("")
        self.details_desc = QLabel("")
        self.details_desc.setWordWrap(True)
        self.details_phase = QLabel("")
        self.details_priority = QLabel("")
        self.details_times = QLabel("")

        form = QFormLayout(self.tab_details)
        form.addRow("Task #", self.details_tasknum)
        form.addRow("Title", self.details_title)
        form.addRow("Description", self.details_desc)
        form.addRow("Phase", self.details_phase)
        form.addRow("Priority", self.details_priority)
        form.addRow("Created / Updated (UTC)", self.details_times)

        # history
        self.history_table = _Table(["When (UTC)", "Actor", "Reason", "Old Phase", "New Phase", "Note"], parent=self.tab_history)
        layh = QVBoxLayout(self.tab_history)
        layh.addWidget(self.history_table)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(self.tabs)

        self._load()

    def _load(self):
        t = get_task(self.task_id)
        if not t:
            QMessageBox.critical(self, "Not found", f"Task {self.task_id} not found")
            self.reject()
            return
        self.title_label.setText(f"{t.get('title','')} — {t.get('task_number','')}")
        self.details_tasknum.setText(t.get("task_number",""))
        self.details_title.setText(t.get("title",""))
        self.details_desc.setText(t.get("description","") or "—")
        self.details_phase.setText(t.get("phase_name",""))
        self.details_priority.setText(t.get("priority","") or "—")
        self.details_times.setText(f"{t.get('created_at_utc','')} / {t.get('updated_at_utc','')}")
        # history
        hrows = list_task_updates(self.task_id)
        self.history_table.load_rows(hrows, ["occurred_at_utc","actor","reason","old_phase","new_phase","note"])

    def _open_editor(self):
        dlg = TaskEditorDialog(self.task_id, parent=self)
        if dlg.exec():
            self._load()

