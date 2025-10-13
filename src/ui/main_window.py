# trackerZ – MainWindow (Rev 0.5.1)
from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QToolBar, QDockWidget,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction
from PySide6.QtCore import Qt, QSettings

from ui.project_overview_window import ProjectOverviewWindow
from ui.project_list_view import ProjectListView
from diagnostics.diagnostics_panel import DiagnosticsPanel


class MainWindow(QMainWindow):
    def __init__(
        self,
        projects_repo,
        tasks_repo,
        subtasks_repo,
        phases_repo,
        attachments_repo=None,
        expenses_repo=None,
        parent=None,
        logfile: str | None = None,
    ):
        super().__init__(parent)
        self._logfile = logfile

        self._projects_repo = projects_repo
        self._tasks_repo = tasks_repo
        self._subtasks_repo = subtasks_repo
        self._phases_repo = phases_repo
        self._attachments_repo = attachments_repo
        self._expenses_repo = expenses_repo

        self._overview_windows: dict[int, ProjectOverviewWindow] = {}
        self._projects_model: QStandardItemModel | None = None
        self._dock_diag: QDockWidget | None = None

        self._init_ui()
        self._connect_signals()

    # ------------------------- UI -------------------------
    def _init_ui(self):
        self.setWindowTitle("trackerZ – Projects")

        # Sensible initial size (overridden if geometry/state restored)
        screen = self.screen() or (self.windowHandle().screen() if self.windowHandle() else None)
        if screen:
            g = screen.availableGeometry()
            self.resize(int(g.width() * 0.7), int(g.height() * 0.7))
        else:
            self.resize(1000, 700)
        self.setMinimumSize(800, 500)

        # Toolbar with Refresh
        tb = QToolBar("Main", self)
        self.addToolBar(tb)
        act_refresh = QAction("Refresh", self)
        act_refresh.triggered.connect(self._reload_projects)
        tb.addAction(act_refresh)

        # Projects model + view
        self._projects_model = QStandardItemModel(0, 2, self)
        self._projects_model.setHorizontalHeaderLabels(["ID", "Name"])

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

        # Install docks (diagnostics) before restoring state
        self._install_diagnostics()

        # Restore geometry/state last so docks layout comes back
        s = QSettings()
        if (geo := s.value("main/geometry", None)) is not None:
            self.restoreGeometry(geo)
        if (st := s.value("main/state", None)) is not None:
            self.restoreState(st)

        # Initial data
        self._reload_projects()

    def _install_diagnostics(self):
        # Avoid duplicates if called again
        existing = self.findChild(QDockWidget, "DiagnosticsDock")
        if existing:
            self._dock_diag = existing
            return

        panel = DiagnosticsPanel(self, logfile=self._logfile) if _accepts_logfile(DiagnosticsPanel) else DiagnosticsPanel(self)

        # If panel already is a dock, use it; otherwise wrap once
        if isinstance(panel, QDockWidget):
            dock = panel
            if not dock.windowTitle():
                dock.setWindowTitle("Diagnostics")
        else:
            dock = QDockWidget("Diagnostics", self)
            dock.setWidget(panel)

        dock.setObjectName("DiagnosticsDock")
        dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable)
        dock.setMinimumHeight(140)

        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        self._dock_diag = dock

        # Ensure it has some space on first run
        try:
            self.resizeDocks([dock], [220], Qt.Vertical)
        except Exception:
            pass

        # View menu toggle (only once)
        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(dock.toggleViewAction())

    # ------------------------- Signals -------------------------
    def _connect_signals(self):
        self.projects_view.projectActivated.connect(self._open_project_overview)

    # ------------------------- Actions -------------------------
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
                parent=self,
            )
            self._overview_windows[project_id] = win
            win.destroyed.connect(lambda _: self._overview_windows.pop(project_id, None))
        win.show(); win.raise_(); win.activateWindow()

    def _reload_projects(self):
        # Clear
        self._projects_model.removeRows(0, self._projects_model.rowCount())

        rows = self._projects_repo.list_projects()  # expect [{id, name}, ...]
        # Toggle empty-state
        is_empty = len(rows) == 0
        self._empty.setVisible(is_empty)
        self.projects_view.setVisible(not is_empty)

        for r in rows:
            pid = r.get("id")
            name = r.get("name") or r.get("title") or f"Project {pid}"

            id_item = QStandardItem(str(pid))
            name_item = QStandardItem(name)

            id_item.setData(pid, Qt.UserRole)
            name_item.setData(pid, Qt.UserRole)

            self._projects_model.appendRow([id_item, name_item])

        self.projects_view.table.resizeColumnsToContents()
        print(f"[MainWindow] Loaded {len(rows)} projects")

    # ------------------------- Persistence -------------------------
    def closeEvent(self, e):
        s = QSettings()
        s.setValue("main/geometry", self.saveGeometry())
        s.setValue("main/state", self.saveState())
        super().closeEvent(e)


# ---- tiny helper ---------------------------------------------------------
def _accepts_logfile(cls) -> bool:
    """Duck-check whether DiagnosticsPanel __init__ accepts a 'logfile' kw.
    Prevents TypeError if an older panel doesn't take it yet.
    """
    try:
        import inspect
        sig = inspect.signature(cls.__init__)
        return "logfile" in sig.parameters
    except Exception:
        return False

