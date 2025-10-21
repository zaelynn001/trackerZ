# Rev 0.6.8 — Coalesce + only flag real changes + decorate names
from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from repositories.sqlite_task_updates_repository import SQLiteTaskUpdatesRepository
from repositories.sqlite_phase_repository import SQLitePhaseRepository


class TasksViewModel(QObject):
    tasksReloaded = Signal(int, list)
    timelineLoaded = Signal(int, list)

    def __init__(self, tasks_repo):
        super().__init__()
        self._tasks = tasks_repo
        self._project_id: Optional[int] = None
        self._phase_id: Optional[int] = None
        self._search: Optional[str] = None

        self._updates_repo: Optional[SQLiteTaskUpdatesRepository] = None
        self._phase_repo: Optional[SQLitePhaseRepository] = None
        self._phase_cache: Dict[int, str] = {}

        self._priority_names: Dict[int, str] = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}

    # ---- filters
    def set_filters(self, project_id: int, phase_id: Optional[int] = None, search: Optional[str] = None) -> None:
        self._project_id, self._phase_id, self._search = project_id, phase_id, search

    # ---- queries
    def reload(self) -> None:
        if self._project_id is None:
            self.tasksReloaded.emit(0, [])
            return
        total = self._tasks.count_tasks_total(project_id=self._project_id, phase_id=self._phase_id, search=self._search)
        rows = self._tasks.list_tasks_filtered(project_id=self._project_id, phase_id=self._phase_id, search=self._search, limit=500, offset=0)
        self.tasksReloaded.emit(total, rows)

    # ---- commands
    def create_task(self, *, project_id: int, name: str, description: str | None, phase_id: int = 1, note_on_create: str | None = None, priority_id: int | None = None) -> int | None:
        try:
            tid = self._tasks.create_task(project_id=project_id, name=name, description=description or "", phase_id=phase_id, priority_id=(priority_id if priority_id is not None else 2), note_on_create=note_on_create)
            self.reload()
            return tid
        except Exception:
            self.reload()
            return None

    def update_task_fields(self, *, task_id: int, name: Optional[str] = None, description: Optional[str] = None, note: Optional[str] = None) -> bool:
        ok = self._tasks.update_task_fields(task_id, name=name, description=description, note=note)
        if ok: self.reload()
        return ok

    def delete_task(self, task_id: int) -> bool:
        ok = self._tasks.delete_task(task_id)
        if ok: self.reload()
        return ok

    def change_task_phase(self, *, task_id: int, new_phase_id: int, reason: Optional[str] = None, note: Optional[str] = None) -> bool:
        try:
            ok = self._tasks.change_task_phase(task_id, new_phase_id, reason=reason or "phase_change", note=note)
            if ok: self.reload()
            return ok
        except Exception:
            self.reload()
            return False

    def set_task_priority(self, *, task_id: int, new_priority_id: int, note: str | None = None) -> bool:
        try:
            ok = self._tasks.set_task_priority(task_id, new_priority_id, note=note)
            if ok: self.reload()
            return bool(ok)
        except Exception:
            self.reload()
            return False

    # ---- timeline
    def load_timeline(self, task_id: int, *, newest_first: bool = True) -> None:
        repo = self._get_updates_repo()
        updates = repo.list_updates_for_task(task_id, order_desc=newest_first)
        updates = self._coalesce_updates(updates, window_secs=2)     # merge near-simultaneous rows
        updates = self._normalize_changes(updates)                   # only keep real diffs
        updates = self._decorate_updates(updates)                    # add *_name and updated_local
        self.timelineLoaded.emit(task_id, updates)

    # ---- internals
    def _get_db_handle(self):
        db_handle = getattr(self._tasks, "_db_or_conn", None)
        if db_handle is None:
            db_handle = getattr(self._tasks, "_conn", None)
        if db_handle is None:
            raise RuntimeError("TasksViewModel: unable to locate DB handle from tasks repo.")
        return db_handle

    def _get_updates_repo(self) -> SQLiteTaskUpdatesRepository:
        if self._updates_repo is None:
            self._updates_repo = SQLiteTaskUpdatesRepository(self._get_db_handle())
        return self._updates_repo

    def _get_phase_repo(self) -> SQLitePhaseRepository:
        if self._phase_repo is None:
            self._phase_repo = SQLitePhaseRepository(self._get_db_handle())
        return self._phase_repo

    def _phase_name(self, phase_id: Optional[int]) -> Optional[str]:
        if phase_id is None: return None
        pid = int(phase_id)
        if pid in self._phase_cache: return self._phase_cache[pid]
        rec = self._get_phase_repo().get_phase(pid)
        name = rec["name"] if rec else str(pid)
        self._phase_cache[pid] = name
        return name

    def _priority_name(self, priority_id: Optional[int]) -> Optional[str]:
        if priority_id is None: return None
        return self._priority_names.get(int(priority_id), str(priority_id))

    # ---------- coalescing ----------
    @staticmethod
    def _parse_ts(s: str | None) -> datetime | None:
        if not s: return None
        try:
            return datetime.fromisoformat(s.replace("Z", "")) if "T" in s else datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None

    @staticmethod
    def _merge_reason(flags: set[str], phase_changed: bool, prio_changed: bool) -> str:
        # Badge choice; the panel will list all lines anyway.
        if phase_changed and prio_changed: return "update"
        if phase_changed: return "phase_change"
        if prio_changed: return "priority_change"
        if "create" in flags: return "create"
        if "note" in flags: return "note"
        return "update"

    def _coalesce_updates(self, updates: List[Dict[str, Any]], window_secs: int = 2) -> List[Dict[str, Any]]:
        if not updates: return []
        items = list(updates)  # newest-first
        out: List[Dict[str, Any]] = []
        cur: List[Dict[str, Any]] = []

        def flush(group: List[Dict[str, Any]]):
            if not group: return
            reasons = {(u.get("reason") or "update").lower() for u in group}
            merged = dict(group[0])  # start from newest
            merged["updated_at_utc"] = group[0].get("updated_at_utc")

            # notes (unique, keep newest-first)
            notes = [(u.get("note") or "").strip() for u in group if (u.get("note") or "").strip()]
            if notes:
                seen, uniq = set(), []
                for n in notes:
                    if n in seen: continue
                    seen.add(n); uniq.append(n)
                merged["note"] = "\n".join(uniq)

            # phase merge: earliest old → latest new within the group
            olds = [u.get("old_phase_id") for u in group if u.get("old_phase_id") is not None]
            news = [u.get("new_phase_id") for u in group if u.get("new_phase_id") is not None]
            merged["old_phase_id"] = olds[-1] if olds else None
            merged["new_phase_id"] = news[0] if news else None

            # priority merge: earliest old → latest new
            p_olds = [u.get("old_priority_id") for u in group if u.get("old_priority_id") is not None]
            p_news = [u.get("new_priority_id") for u in group if u.get("new_priority_id") is not None]
            merged["old_priority_id"] = p_olds[-1] if p_olds else None
            merged["new_priority_id"] = p_news[0] if p_news else None

            # compute real diffs; if equal or missing, null them so UI won't render phantom changes
            phase_changed = False
            if merged["old_phase_id"] is None or merged["new_phase_id"] is None or int(merged["old_phase_id"]) == int(merged["new_phase_id"]):
                merged["old_phase_id"] = None
                merged["new_phase_id"] = None
            else:
                phase_changed = True

            prio_changed = False
            if merged["old_priority_id"] is None or merged["new_priority_id"] is None or int(merged["old_priority_id"]) == int(merged["new_priority_id"]):
                merged["old_priority_id"] = None
                merged["new_priority_id"] = None
            else:
                prio_changed = True

            merged["reason"] = self._merge_reason(reasons, phase_changed, prio_changed)
            out.append(merged)

        prev = self._parse_ts(items[0].get("updated_at_utc"))
        cur.append(items[0])
        for u in items[1:]:
            ts = self._parse_ts(u.get("updated_at_utc"))
            same_bucket = (prev and ts and abs((prev - ts).total_seconds()) <= window_secs) or (u.get("updated_at_utc") == cur[0].get("updated_at_utc"))
            if same_bucket:
                cur.append(u)
            else:
                flush(cur)
                cur = [u]
                prev = ts
        flush(cur)
        return out
        
    def _normalize_changes(self, updates: list[dict]) -> list[dict]:
        """
        Final cleanup pass per entry:
          - Only keep phase/priority pairs if they actually changed.
          - Recompute a sane badge reason based on what changed (and any existing reason).
        """
        out: list[dict] = []
        for u in updates:
            w = dict(u)  # copy

            # Phase
            op = w.get("old_phase_id")
            np = w.get("new_phase_id")
            phase_changed = False
            try:
                phase_changed = (op is not None and np is not None and int(op) != int(np))
            except Exception:
                phase_changed = False
            if not phase_changed:
                w["old_phase_id"] = None
                w["new_phase_id"] = None

            # Priority
            opr = w.get("old_priority_id")
            npr = w.get("new_priority_id")
            prio_changed = False
            try:
                prio_changed = (opr is not None and npr is not None and int(opr) != int(npr))
            except Exception:
                prio_changed = False
            if not prio_changed:
                w["old_priority_id"] = None
                w["new_priority_id"] = None

            # Badge reason
            flags = {(w.get("reason") or "update").lower()}
            w["reason"] = self._merge_reason(flags, phase_changed, prio_changed)

            out.append(w)
        return out
        
    def get_task_details(self, task_id: int) -> Optional[dict]:
        """
        Thin pass-through so the UI can fetch current Name/Description/Phase/Priority.
        """
        try:
            return self._tasks.get_task(task_id)
        except Exception:
            return None

        

    # ---------- decoration ----------
    def _decorate_updates(self, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for u in updates:
            u = dict(u)
            # only decorate when IDs present (means a real change)
            if u.get("old_phase_id") is not None:
                u["old_phase_name"] = self._phase_name(u.get("old_phase_id"))
            if u.get("new_phase_id") is not None:
                u["new_phase_name"] = self._phase_name(u.get("new_phase_id"))
            if u.get("old_priority_id") is not None:
                u["old_priority_name"] = self._priority_name(u.get("old_priority_id"))
            if u.get("new_priority_id") is not None:
                u["new_priority_name"] = self._priority_name(u.get("new_priority_id"))
            u["updated_local"] = u.get("updated_at_utc")
            out.append(u)
        return out
