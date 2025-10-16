# Rev 0.6.6 — M6.5 Unified Workspace
# trackerZ — Main Window refactor to single-window, stacked workspace
# Replaces multi-window flow with a QStackedWidget host.
# Signature preserved to match src/main.py call site.

from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QToolBar, QAction

from ui.window_mode import lock_maximized
from ui.workspace import WorkspaceStack
from ui.panels.projects_panel import ProjectsPanel
from ui.panels.project_overview_panel import ProjectOverviewPanel


class MainWindow(QMainWindow):
    """
    Unified main window hosting the stacked workspace.

    Constructor matches current src/main.py usage:
      MainWindow(
        projects_repo=..., tasks_repo=..., subtasks_repo=..., phases_repo=...,
        attachments_repo=None, expenses_repo=None, logfile=None, parent=None
      )
    """

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

        # --- Repos / context ---
        self._projects_repo = projects_repo
        self._tasks_repo = tasks_repo
        self._subtasks_repo = subtasks_repo
        self._phases_repo = phases_repo
        self._attachments_repo = attachments_repo
        self._expenses_repo = expenses_repo
        self._logfile = logfile

        self.setWindowTitle("trackerZ — Workspace")

        # --- Workspace stack ---
        self._ws = WorkspaceStack(self)
        self.setCentralWidget(self._ws)

        # --- Panels (QWidget-based) ---
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

        # --- Navigation toolbar (breadcrumb-ish) ---
        tb = QToolBar("Navigation", self)
        self.addToolBar(Qt.TopToolBarArea, tb)

        act_projects = QAction("Projects", self)
        act_projects.triggered.connect(self._nav_projects)
        tb.addAction(act_projects)

        # --- Wiring panel signals ---
        self._p_projects.projectSelected.connect(self._open_project_overview)

        # --- Initial route ---
        self._ws.show_panel("projects")
        self._p_projects.load()

        # --- Window policy: lock maximized (user preference) ---
        lock_maximized(self, lock_resize=True)

    # ---------------- Navigation handlers ----------------

    def _nav_projects(self) -> None:
        """Go to Projects list."""
        self._ws.show_panel("projects")
        self._p_projects.load()

    def _open_project_overview(self, project_id: int) -> None:
        """Open embedded Project Overview for given project_id."""
        self._ws.show_panel("overview")
        self._p_overview.load(project_id)
