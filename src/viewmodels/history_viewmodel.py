# Rev 0.6.8
# src/viewmodels/history_viewmodel.py  (Rev 0.6.8)
class HistoryViewModel:
    def __init__(self, tasks_repo, subtasks_repo, phases_repo, priorities_repo):
        self._tasks = tasks_repo
        self._subs = subtasks_repo
        self._phases = phases_repo
        self._priorities = priorities_repo

    def load(self, kind, obj_id, limit=100, reason_filter=None):
        if kind == 'task':
            rows = self._tasks.list_task_updates(obj_id, limit=limit, reason_filter=reason_filter)
        else:
            rows = self._subs.list_subtask_updates(obj_id, limit=limit, reason_filter=reason_filter)
        # decorate with names & local times for display
        for r in rows:
            r["old_phase_name"] = self._phases.name_for_id(r.get("old_phase_id"))
            r["new_phase_name"] = self._phases.name_for_id(r.get("new_phase_id"))
            r["old_priority_name"] = self._priorities.name_for_id(r.get("old_priority_id"))
            r["new_priority_name"] = self._priorities.name_for_id(r.get("new_priority_id"))
            r["updated_local"] = self._to_local(r["updated_at_utc"])
        return rows

    def _to_local(self, s):  # implement with your existing utils
        return s
