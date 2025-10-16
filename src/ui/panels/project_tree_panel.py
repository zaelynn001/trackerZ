# Rev 0.6.7 — ProjectTreePanel (Tasks/Subtasks view by name, ordered by hidden id)
from __future__ import annotations
from typing import Optional, Iterable, Tuple, Dict, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLabel


class ProjectTreePanel(QWidget):
    """
    Collapsible sidebar bound to the *current* project.
    Shows tasks (by name) and their subtasks (by name), both ordered by id (hidden).
    - IDs are stored in Qt.UserRole to enable future navigation.
    - Project switching remains owned by ProjectsPanel.
    """

    # Optional signals if you want clicks to navigate elsewhere later
    taskActivated = Signal(int)                 # task_id
    subtaskActivated = Signal(int, int)        # task_id, subtask_id

    def __init__(self, parent: Optional[QWidget] = None, *,
                 projects_repo=None, tasks_repo=None, subtasks_repo=None) -> None:
        super().__init__(parent)
        self._projects_repo = projects_repo
        self._tasks_repo = tasks_repo
        self._subtasks_repo = subtasks_repo

        self._project_id: Optional[int] = None
        self._project_name: str = ""

        self._title = QLabel("Project")
        self._title.setProperty("class", "sidebar-title")

        self._tree = QTreeWidget(self)
        self._tree.setHeaderHidden(True)
        self._tree.itemActivated.connect(self._on_item_activated)
        self._tree.itemClicked.connect(self._on_item_activated)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.addWidget(self._title)
        lay.addWidget(self._tree)

    # ------------------- public API -------------------

    def set_project(self, project_id: int, project_name: str) -> None:
        """
        Bind this sidebar to a single project and render its Tasks/Subtasks.
        """
        self._project_id = project_id
        self._project_name = project_name or f"Project {project_id}"
        self._title.setText(self._project_name)
        self._render()

    def clear_project(self) -> None:
        self._project_id = None
        self._project_name = ""
        self._title.setText("Project")
        self._tree.clear()

    # ------------------- internals -------------------

    def _render(self) -> None:
        self._tree.clear()
        if self._project_id is None:
            return

        root = QTreeWidgetItem([self._project_name])
        root.setFlags(root.flags() & ~Qt.ItemIsSelectable)  # label-only parent
        self._tree.addTopLevelItem(root)

        # Fetch tasks by id/name (ordered by id)
        tasks = self._fetch_tasks(self._project_id)
        for tid, tname in tasks:
            t_item = QTreeWidgetItem([tname or f"Task {tid}"])
            t_item.setData(0, Qt.UserRole, {"kind": "task", "task_id": tid})
            root.addChild(t_item)

            # Fetch subtasks by id/name (ordered by id)
            for sid, sname in self._fetch_subtasks(self._project_id, tid):
                s_item = QTreeWidgetItem([sname or f"Subtask {sid}"])
                s_item.setData(0, Qt.UserRole, {"kind": "subtask", "task_id": tid, "subtask_id": sid})
                t_item.addChild(s_item)

        self._tree.expandItem(root)

    def _on_item_activated(self, item: QTreeWidgetItem) -> None:
        data = item.data(0, Qt.UserRole)
        if not isinstance(data, dict):
            return
        if data.get("kind") == "task":
            self.taskActivated.emit(int(data["task_id"]))
        elif data.get("kind") == "subtask":
            self.subtaskActivated.emit(int(data["task_id"]), int(data["subtask_id"]))

    # ------------------- data fetch (robust) -------------------

    def _fetch_tasks(self, project_id: int) -> list[tuple[int, str]]:
        """
        Return [(task_id, name), ...], ordered by id asc.
        Tries repo methods first; falls back to raw SQL via extracted connection.
        """
        repo = self._tasks_repo
        rows: Iterable | None = None

        if repo:
            # Try likely method names across your variants
            for meth in ("list_tasks_for_project", "list_tasks", "list_project_tasks"):
                if hasattr(repo, meth):
                    try:
                        rows = getattr(repo, meth)(project_id=project_id)  # prefer kw
                    except TypeError:
                        rows = getattr(repo, meth)(project_id)            # positional fallback
                    break
            if rows is None and hasattr(repo, "list_tasks_filtered"):
                # Your code commonly uses list_tasks_filtered(project_id=..., phase_id=...)
                try:
                    rows = repo.list_tasks_filtered(project_id=project_id, phase_id=None)
                except TypeError:
                    try:
                        rows = repo.list_tasks_filtered(project_id=project_id)
                    except Exception:
                        rows = None

        if rows is not None:
            parsed = []
            for r in rows:
                if isinstance(r, dict):
                    parsed.append((int(r.get("id")), r.get("name", "")))
                else:
                    # assume row[0]=id, row[1]=name
                    tid = int(r[0])
                    name = r[1] if len(r) > 1 else ""
                    parsed.append((tid, name))
            # order by id
            parsed.sort(key=lambda x: x[0])
            return parsed

        # Raw SQL fallback
        con = self._extract_conn(repo or self._projects_repo)
        if con is None:
            return []
        cur = con.cursor()
        cur.execute("SELECT id, name FROM tasks WHERE project_id = ? ORDER BY id ASC", (project_id,))
        return [(int(r[0]), r[1] or "") for r in cur.fetchall()]

    def _fetch_subtasks(self, project_id: int, task_id: int) -> list[tuple[int, str]]:
        """
        Return [(subtask_id, name), ...], ordered by id asc.
        """
        repo = self._subtasks_repo
        rows: Iterable | None = None

        if repo:
            for meth in ("list_subtasks_for_project", "list_subtasks", "list_for_task"):
                if hasattr(repo, meth):
                    try:
                        rows = getattr(repo, meth)(project_id=project_id, task_id=task_id)
                    except TypeError:
                        try:
                            rows = getattr(repo, meth)(project_id, task_id)
                        except Exception:
                            pass
                    break

        if rows is not None:
            parsed = []
            for r in rows:
                if isinstance(r, dict):
                    parsed.append((int(r.get("id")), r.get("name", "")))
                else:
                    sid = int(r[0])
                    name = r[1] if len(r) > 1 else ""
                    parsed.append((sid, name))
            parsed.sort(key=lambda x: x[0])
            return parsed

        con = self._extract_conn(repo or self._projects_repo)
        if con is None:
            return []
        cur = con.cursor()
        cur.execute(
            "SELECT id, name FROM subtasks WHERE project_id = ? AND task_id = ? ORDER BY id ASC",
            (project_id, task_id),
        )
        return [(int(r[0]), r[1] or "") for r in cur.fetchall()]

    # ---------- connection fishing (mirrors your existing pattern) ----------

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
