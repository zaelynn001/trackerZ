# Rev 0.4.1

# trackerZ – MainWindow (Rev 0.4.1)
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QToolBar, QDockWidget
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction
from PySide6.QtCore import Qt, QSettings

from ui.project_overview_window import ProjectOverviewWindow
from ui.project_list_view import ProjectListView 
from diagnostics.diagnostics_panel import DiagnosticsPanel

class MainWindow(QMainWindow):
    def __init__(self, projects_repo, tasks_repo, subtasks_repo, phases_repo,
                 attachments_repo=None, expenses_repo=None, parent=None, logfile=None,):
        super().__init__(parent)
        self._logfile = logfile
        self._projects_repo = projects_repo
        self._tasks_repo = tasks_repo
        self._subtasks_repo = subtasks_repo
        self._phases_repo = phases_repo
        self._attachments_repo = attachments_repo
        self._expenses_repo = expenses_repo

        self._overview_windows = {}   # project_id -> ProjectOverviewWindow
        self._projects_model = None

        self._init_ui()               # <-- builds self.projects_view
        self._connect_signals()  

    def _init_ui(self):
        self.setWindowTitle("trackerZ – Projects")
        screen = self.screen() or self.windowHandle().screen()
        if screen:
            g = screen.availableGeometry()
            self.resize(int(g.width()*0.7), int(g.height()*0.7))
        else:
            self.resize(1000, 700)
        self.setMinimumSize(800, 500)
        
        s = QSettings()
        geo = s.value("main/geometry", None)
        if geo is not None:
            self.restoreGeometry(geo)

        # toolbar with Refresh
        tb = QToolBar("Main", self)
        self.addToolBar(tb)
        act_refresh = QAction("Refresh", self)
        act_refresh.triggered.connect(self._reload_projects)
        tb.addAction(act_refresh)

        # Model with 2 columns: ID (hidden), Name
        self._projects_model = QStandardItemModel(0, 2, self)
        self._projects_model.setHorizontalHeaderLabels(["ID", "Name"])

        # View
        self.projects_view = ProjectListView(model=self._projects_model, proxy=None, parent=self)
        self.projects_view.table.setColumnHidden(0, True)

        # Empty-state label
        self._empty = QLabel("No projects found.\nCreate a project or load sample data.")
        self._empty.setAlignment(Qt.AlignCenter)
        self._empty.setStyleSheet("color: #888; font-size: 14px; padding: 24px;")

        # Central layout
        c = QWidget(self)
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.projects_view)
        lay.addWidget(self._empty)
        self.setCentralWidget(c)

        # initial load
        self._reload_projects()
        
        self._dock_diag = QDockWidget("Diagnostics", self)
        self._dock_diag.setObjectName("DiagnosticsDock")
        self._diag_widget = DiagnosticsPanel(self)
        self._dock_diag.setWidget(self._diag_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self._dock_diag)

        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self._dock_diag.toggleViewAction())
        
    def _connect_signals(self):
        self.projects_view.projectActivated.connect(self._open_project_overview)

    # ---------- Actions ----------
    def _open_project_overview(self, project_id: int):
        win = self._overview_windows.get(project_id)
        if win is None:
            win = ProjectOverviewWindow(
                project_id,
                projects_repo=self._projects_repo,
                tasks_repo=self._tasks_repo,
                subtasks_repo=self._subtasks_repo,
                phases_repo=self._phases_repo,
                attachments_repo=self._attachments_repo,
                expenses_repo=self._expenses_repo,
                parent=self
            )
            self._overview_windows[project_id] = win
            win.destroyed.connect(lambda _: self._overview_windows.pop(project_id, None))
        win.show(); win.raise_(); win.activateWindow()

    def _reload_projects(self):
        # clear
        self._projects_model.removeRows(0, self._projects_model.rowCount())

        rows = self._projects_repo.list_projects()  # expect [{id, name}, ...]
        # Toggle empty-state
        self._empty.setVisible(len(rows) == 0)
        self.projects_view.setVisible(len(rows) > 0)

        for r in rows:
            pid = r.get("id")
            name = r.get("name") or r.get("title") or f"Project {pid}"

            id_item = QStandardItem(str(pid))
            name_item = QStandardItem(name)

            id_item.setData(pid, Qt.UserRole)
            name_item.setData(pid, Qt.UserRole)

            self._projects_model.appendRow([id_item, name_item])

        # optional: resize columns
        self.projects_view.table.resizeColumnsToContents()
        # log to stdout (shows in run log)
        print(f"[MainWindow] Loaded {len(rows)} projects")
        
    def closeEvent(self, e):
        QSettings().setValue("main/geometry", self.saveGeometry())
        super().closeEvent(e)

