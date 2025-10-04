# src/ui/project_overview.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QWidget, QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt
from src.models.dao import (
    get_project, list_tasks_for_project, list_subtasks_for_project,
    list_attachments_for_project, list_expenses_for_project, list_project_updates
)
from src.ui.project_editor import ProjectEditorDialog
from src.ui.task_overview import TaskOverviewDialog
from src.ui.subtask_overview import SubtaskOverviewDialog


class _Table(QTableWidget):
    def __init__(self, headers: list[str], parent=None):
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

class ProjectOverviewDialog(QDialog):
    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Project Overview — #{project_id}")
        self.resize(980, 640)
        self.project_id = project_id

        # Top bar: Title + Edit button
        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.btn_edit = QPushButton("Edit Project")
        self.btn_edit.clicked.connect(self._open_editor)

        top = QHBoxLayout()
        top.addWidget(self.title_label, 1)
        top.addWidget(self.btn_edit, 0, Qt.AlignRight)

        # Tabs
        self.tabs = QTabWidget()
        self.tab_details = QWidget()
        self.tab_tasks = QWidget()
        self.tab_subtasks = QWidget()
        self.tab_attachments = QWidget()
        self.tab_expenses = QWidget()
        self.tab_history = QWidget()

        self.tabs.addTab(self.tab_details, "Details")
        self.tabs.addTab(self.tab_tasks, "Tasks")
        self.tabs.addTab(self.tab_subtasks, "Subtasks")
        self.tabs.addTab(self.tab_attachments, "Attachments")
        self.tabs.addTab(self.tab_expenses, "Expenses")
        self.tabs.addTab(self.tab_history, "History")

        # Root layout
        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(self.tabs)

        # Build tab UIs
        self._build_details_tab()
        self._build_tasks_tab()
        self._build_subtasks_tab()
        self._build_attachments_tab()
        self._build_expenses_tab()
        self._build_history_tab()

        # Load data
        self._load_all()

    # ─────────────────────────────────────────────────────────
    # Tabs
    # ─────────────────────────────────────────────────────────
    def _build_details_tab(self):
        self.details_title = QLabel("")
        self.details_desc  = QLabel("")
        self.details_desc.setWordWrap(True)
        self.details_phase = QLabel("")
        self.details_priority = QLabel("")
        self.details_numbers = QLabel("")  # project number + DB id
        form = QFormLayout()
        form.addRow("Project # / ID", self.details_numbers)
        form.addRow("Title", self.details_title)
        form.addRow("Description", self.details_desc)
        form.addRow("Phase", self.details_phase)
        form.addRow("Priority", self.details_priority)
        wrap = QVBoxLayout(self.tab_details)
        wrap.addLayout(form)

    def _build_tasks_tab(self):
        self.tasks_table = _Table(
            ["ID", "Task #", "Title", "Description", "Phase", "Priority", "Created (UTC)", "Updated (UTC)"],
            parent=self.tab_tasks
        )
        lay = QVBoxLayout(self.tab_tasks)
        lay.addWidget(self.tasks_table)
        self.tasks_table.doubleClicked.connect(self._open_task_overview) 

    def _build_subtasks_tab(self):
        self.subtasks_table = _Table(
            ["ID", "Subtask #", "Task ID", "Title", "Description", "Phase", "Priority", "Created (UTC)", "Updated (UTC)"],
            parent=self.tab_subtasks
        )
        lay = QVBoxLayout(self.tab_subtasks)
        lay.addWidget(self.subtasks_table)
        self.subtasks_table.doubleClicked.connect(self._open_subtask_overview)

    def _build_attachments_tab(self):
        self.attachments_table = _Table(
            ["(stub) Filename", "Note"],
            parent=self.tab_attachments
        )
        lay = QVBoxLayout(self.tab_attachments)
        lay.addWidget(self.attachments_table)

    def _build_expenses_tab(self):
        self.expenses_table = _Table(
            ["(stub) Date", "Vendor", "Amount", "Note"],
            parent=self.tab_expenses
        )
        lay = QVBoxLayout(self.tab_expenses)
        lay.addWidget(self.expenses_table)

    def _build_history_tab(self):
        self.history_table = _Table(
            ["When (UTC)", "Actor", "Reason", "Old Phase", "New Phase", "Note"],
            parent=self.tab_history
        )
        lay = QVBoxLayout(self.tab_history)
        lay.addWidget(self.history_table)

    # ─────────────────────────────────────────────────────────
    # Data loading
    # ─────────────────────────────────────────────────────────
    def _load_all(self):
        pr = get_project(self.project_id)
        if not pr:
            QMessageBox.critical(self, "Not found", f"Project {self.project_id} was not found.")
            self.reject()
            return

        self.title_label.setText(f"{pr.get('title','')} — {pr.get('project_number','')}")
        self.details_title.setText(pr.get("title", ""))
        self.details_desc.setText(pr.get("description", "") or "—")
        self.details_phase.setText(pr.get("phase_name", ""))
        self.details_priority.setText(pr.get("priority", "") or "—")
        self.details_numbers.setText(f"{pr.get('project_number','')} / {pr.get('id','')}")

        # Tasks
        trows = list_tasks_for_project(self.project_id)
        self.tasks_table.load_rows(trows, ["id","task_number","title","description","phase","priority","created_at_utc","updated_at_utc"])

        # Subtasks
        srows = list_subtasks_for_project(self.project_id)
        self.subtasks_table.load_rows(srows, ["id","subtask_number","task_id","title","description","phase","priority","created_at_utc","updated_at_utc"])

        # Attachments (stub)
        arows = list_attachments_for_project(self.project_id)
        self.attachments_table.load_rows(arows, [])

        # Expenses (stub)
        erows = list_expenses_for_project(self.project_id)
        self.expenses_table.load_rows(erows, [])

        # History
        hrows = list_project_updates(self.project_id)
        self.history_table.load_rows(hrows, ["occurred_at_utc","actor","reason","old_phase","new_phase","note"])

    # ─────────────────────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────────────────────
    def _open_editor(self):
        dlg = ProjectEditorDialog(self.project_id, parent=self)
        if dlg.exec():
            # After a successful edit or phase change, reload overview
            self._load_all()
    def _open_task_overview(self):
        row = self.tasks_table.currentRow()
        if row < 0: return
        task_id = int(self.tasks_table.item(row, 0).text())
        dlg = TaskOverviewDialog(task_id, parent=self)
        dlg.exec()
        self._load_all()  # refresh after potential edits

    def _open_subtask_overview(self):
        row = self.subtasks_table.currentRow()
        if row < 0: return
        subtask_id = int(self.subtasks_table.item(row, 0).text())
        dlg = SubtaskOverviewDialog(subtask_id, parent=self)
        dlg.exec()
        self._load_all()

