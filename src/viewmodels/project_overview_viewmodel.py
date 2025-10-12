# Rev 0.4.1
# trackerZ – ProjectOverviewViewModel (Rev 0.4.1)
class ProjectOverviewViewModel:
    def __init__(self, projects_repo, tasks_repo, subtasks_repo, attachments_repo=None, expenses_repo=None):
        self._projects = projects_repo
        self._tasks = tasks_repo
        self._subtasks = subtasks_repo
        self._attachments = attachments_repo
        self._expenses = expenses_repo
        self._project = None
        self._counts = {}

    def load(self, project_id:int):
        self._project = self._projects.get_project(project_id)
        # Use fast COUNT queries; keep names aligned with your schema
        self._counts = {
            "tasks_total": self._tasks.count_tasks_total(project_id=project_id),
            "subtasks_total": self._subtasks.count_subtasks_total(project_id=project_id),
            "attachments_total": (self._attachments.count_project_attachments(project_id) if self._attachments else 0),
            "expenses_total": (self._expenses.count_project_expenses(project_id) if self._expenses else 0),
        }

    def project_name(self)->str:
        return getattr(self._project, "name", None) or getattr(self._project, "title", None) or ""

    def counts(self)->dict:
        return dict(self._counts)

