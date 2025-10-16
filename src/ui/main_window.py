# Rev 0.6.7 — M6.5 Workspace (+ Project Tree Dock)

from __future__ import annotations
from collections import deque
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QToolBar, QDockWidget

from ui.window_mode import lock_maximized
from ui.workspace import WorkspaceStack
from ui.panels.projects_panel import ProjectsPanel
from ui.panels.project_overview_panel import ProjectOverviewPanel
from ui.panels.project_tree_panel import ProjectTreePanel  # <-- NEW

# Diagnostics optional
try:
    from ui.diagnostics_panel import DiagnosticsPanel
    _HAS_DIAG = True
except Exception:
    _HAS_DIAG = False


class MainWindow(QMainWindow):
    def __init__(
        self,
        *,
        projects_repo,
        tasks_repo,
        subtasks_repo,
        phases_repo,
        attachments_repo=None,
        expenses_repo=None,
        logfile: str | None = None,
        parent=None,
        **_ignored,
    ) -> None:
        super().__init__(parent)

        # --- Context ---
        self._projects_repo = projects_repo
        self._tasks_repo = tasks_repo
        self._subtasks_repo = subtasks_repo
        self._phases_repo = phases_repo
        self._attachments_repo = attachments_repo
        self._expenses_repo = expenses_repo
        self._logfile = logfile

        self.setWindowTitle("trackerZ — Workspace")

        # --- Workspace ---
        self._ws = WorkspaceStack(self)
        self.setCentralWidget(self._ws)

        # --- Panels ---
        self._p_projects = ProjectsPanel(projects_repo=self._projects_repo, parent=self)
        self._p_overview = ProjectOverviewPanel(
            projects_repo=self._projects_repo,
            tasks_repo=self._tasks_repo,
            subtasks_repo=self._subtasks_repo,
            phases_repo=self._phases_repo,
            attachments_repo=self._attachments_repo,
            expenses_repo=self._expenses_repo,
            parent=self,
        )

        self._ws.add_panel("projects", self._p_projects)
        self._ws.add_panel("overview", self._p_overview)

        # --- History (Back) ---
        from collections import deque
        self._history: deque[str] = deque(maxlen=20)

        # --- Toolbar ---
        tb = QToolBar("Navigation", self)
        self.addToolBar(Qt.TopToolBarArea, tb)

        self._act_back = QAction("Back", self)
        self._act_back.setEnabled(False)
        self._act_back.triggered.connect(self._nav_back)
        tb.addAction(self._act_back)

        act_projects = QAction("Projects", self)
        act_projects.triggered.connect(self._nav_projects)
        tb.addAction(act_projects)

        # --- Left Dock: Project Tree (collapsible) ---
        # inside __init__ (replace the existing tree panel creation):
        self._dock_tree = QDockWidget("Project", self)
        self._dock_tree.setObjectName("ProjectTreeDock")
        self._dock_tree.setAllowedAreas(Qt.LeftDockWidgetArea)
        self._dock_tree.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable
        )
        self._tree_panel = ProjectTreePanel(
            self,
            projects_repo=self._projects_repo,
            tasks_repo=self._tasks_repo,
            subtasks_repo=self._subtasks_repo,
        )
        self._dock_tree.setWidget(self._tree_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._dock_tree)

        # --- Diagnostics dock (optional) ---
        if _HAS_DIAG:
            self._dock_diag = QDockWidget("Diagnostics", self)
            self._dock_diag.setObjectName("DiagnosticsDock")
            self._diag_widget = DiagnosticsPanel(self)
            self._dock_diag.setWidget(self._diag_widget)
            self.addDockWidget(Qt.BottomDockWidgetArea, self._dock_diag)

        # --- Wiring panel signals ---
        self._p_projects.projectSelected.connect(self._open_project_overview)

        # --- Initial ---
        self._route_to("projects")
        self._p_projects.load()

        # --- Window policy ---
        lock_maximized(self, lock_resize=True)

    # ---------- routing ----------

    def _route_to(self, key: str) -> None:
        cur = self._ws.current_key()
        if cur and cur != key:
            self._history.append(cur)
        self._ws.show_panel(key)
        self._act_back.setEnabled(len(self._history) > 0)

    def _nav_back(self) -> None:
        if not self._history:
            return
        key = self._history.pop()
        self._ws.show_panel(key)
        self._act_back.setEnabled(len(self._history) > 0)

    def _nav_projects(self) -> None:
        # When leaving a project, clear the static tree
        self._tree_panel.clear_project()
        self._route_to("projects")
        self._p_projects.load()

    # ---------- panel-driven navigation ----------

    def _open_project_overview(self, project_id: int) -> None:
        """
        Open embedded Project Overview and pin the tree to this project,
        keeping it static while navigating sections.
        """
        # Obtain a friendly name for the sidebar (fallback to "Project <id>")
        pname = f"Project {project_id}"
        try:
            # Try a light lookup (works with your repositories)
            con = self._extract_conn(self._projects_repo)
            if con:
                cur = con.cursor()
                cur.execute("SELECT name FROM projects WHERE id = ?", (project_id,))
                row = cur.fetchone()
                if row and row[0]:
                    pname = row[0]
        except Exception:
            pass

        self._tree_panel.set_project(project_id, pname)
        self._route_to("overview")
        self._p_overview.load(project_id)
        if hasattr(self._p_overview, "select_tab"):
            self._p_overview.select_tab("overview")  # center shows Overview tab now

    # ---------- tree-driven navigation ----------

    def _on_tree_navigate(self, key: str) -> None:
        # Always show the Overview panel in the center...
        self._route_to("overview")
        # ...then select the requested tab inside it.
        if hasattr(self._p_overview, "select_tab"):
            self._p_overview.select_tab(key)

    # ---------- utils ----------

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
