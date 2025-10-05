# src/models/dao.py
from typing import Optional, List, Dict, Tuple
import logging
from src.models.db import tx
from src.services.phase_rules import is_allowed_phase_change, current_phase_id_for

# ─────────────────────────────────────────────────────────────
# Phase helpers
# ─────────────────────────────────────────────────────────────
def get_all_phases() -> List[Dict]:
    with tx() as conn:
        return conn.execute("SELECT id, name, is_terminal, sort_order FROM phases ORDER BY sort_order").fetchall()

def get_phase_id_by_name(name: str) -> Optional[int]:
    with tx() as conn:
        row = conn.execute("SELECT id FROM phases WHERE name = ?", (name,)).fetchone()
        return row["id"] if row else None

def allowed_phase_targets(current_phase_id: int) -> List[Dict]:
    with tx() as conn:
        rows = conn.execute("""
            SELECT p.id, p.name
            FROM phase_transitions pt
            JOIN phases p ON p.id = pt.to_phase_id
            WHERE pt.from_phase_id = ?
            ORDER BY p.sort_order
        """, (current_phase_id,)).fetchall()
        return rows

# ─────────────────────────────────────────────────────────────
# Projects
# ─────────────────────────────────────────────────────────────
def list_projects_flat() -> List[Dict]:
    with tx() as conn:
        return conn.execute("""
            SELECT pr.id, pr.project_number, pr.title, pr.description, pr.priority,
                   pr.created_at_utc, pr.updated_at_utc, ph.name AS phase, ph.id AS phase_id
            FROM projects pr
            JOIN phases ph ON ph.id = pr.phase_id
            ORDER BY pr.updated_at_utc DESC, pr.id DESC
        """).fetchall()

def get_project(project_id: int) -> Optional[Dict]:
    with tx() as conn:
        return conn.execute("""
            SELECT pr.*, ph.name AS phase_name
            FROM projects pr
            JOIN phases ph ON ph.id = pr.phase_id
            WHERE pr.id = ?
        """, (project_id,)).fetchone()

def update_project_metadata(project_id: int, title: str, description: str, priority: Optional[str]) -> None:
    with tx() as conn:
        exists = conn.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not exists:
            raise ValueError(f"Project {project_id} not found")
        conn.execute("""
            UPDATE projects
               SET title = ?, description = ?, priority = ?, updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
             WHERE id = ?
        """, (title, description, priority, project_id))
    logging.info("Project %s metadata updated (title=%r, priority=%r)", project_id, title, priority)

def change_project_phase(project_id: int, actor: str, new_phase_id: int, note: str = "") -> Tuple[int, int]:
    old_phase_id = current_phase_id_for("projects", "id", project_id)
    if old_phase_id is None:
        raise ValueError(f"Project {project_id} not found")

    with tx() as conn:
        if old_phase_id == new_phase_id:
            conn.execute("""
                INSERT INTO project_updates (project_id, changed_at_utc, actor, reason, old_phase_id, new_phase_id, note)
                VALUES (?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), ?, 'Note', ?, ?, ?)
            """, (project_id, actor, old_phase_id, new_phase_id, note or "No phase change"))
            return old_phase_id, new_phase_id

        if not is_allowed_phase_change(old_phase_id, new_phase_id):
            raise ValueError(f"Phase change not allowed: {old_phase_id} → {new_phase_id}")

        conn.execute("""
            UPDATE projects
               SET phase_id = ?, updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
             WHERE id = ?
        """, (new_phase_id, project_id))
        conn.execute("""
            INSERT INTO project_updates (project_id, changed_at_utc, actor, reason, old_phase_id, new_phase_id, note)
            VALUES (?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), ?, 'Phase Change', ?, ?, ?)
        """, (project_id, actor, old_phase_id, new_phase_id, note))
        logging.info("Project %s phase change: %s -> %s", project_id, old_phase_id, new_phase_id)
        return old_phase_id, new_phase_id

# ─────────────────────────────────────────────────────────────
# Project-related lists (Overview tabs)
# ─────────────────────────────────────────────────────────────
def list_tasks_for_project(project_id: int) -> List[Dict]:
    with tx() as conn:
        return conn.execute("""
            SELECT t.id, t.task_number, t.title, t.description, t.priority, t.created_at_utc, t.updated_at_utc,
                   ph.name AS phase, t.phase_id
            FROM tasks t
            JOIN phases ph ON ph.id = t.phase_id
            WHERE t.project_id = ?
            ORDER BY t.updated_at_utc DESC, t.id DESC
        """, (project_id,)).fetchall()

def list_subtasks_for_project(project_id: int) -> List[Dict]:
    with tx() as conn:
        return conn.execute("""
            SELECT s.id, s.subtask_number, s.title, s.description, s.priority, s.created_at_utc, s.updated_at_utc,
                   ph.name AS phase, s.phase_id, s.task_id
            FROM subtasks s
            JOIN tasks t  ON t.id = s.task_id
            JOIN phases ph ON ph.id = s.phase_id
            WHERE t.project_id = ?
            ORDER BY s.updated_at_utc DESC, s.id DESC
        """, (project_id,)).fetchall()

def list_project_updates(project_id: int) -> List[Dict]:
    with tx() as conn:
        return conn.execute("""
            SELECT u.id, u.changed_at_utc, u.actor, u.reason,
                   (SELECT name FROM phases WHERE id = u.old_phase_id) AS old_phase,
                   (SELECT name FROM phases WHERE id = u.new_phase_id) AS new_phase,
                   u.note
            FROM project_updates u
            WHERE u.project_id = ?
            ORDER BY u.changed_at_utc DESC, u.id DESC
        """, (project_id,)).fetchall()

def list_attachments_for_project(project_id: int) -> List[Dict]:
    return []  # placeholder

def list_expenses_for_project(project_id: int) -> List[Dict]:
    return []  # placeholder

# ─────────────────────────────────────────────────────────────
# Task services
# ─────────────────────────────────────────────────────────────
def change_task_phase(task_id: int, new_phase_id: int, note: str = "") -> Tuple[int, int]:
    old_phase_id = current_phase_id_for("tasks", "id", task_id)
    if old_phase_id is None:
        raise ValueError(f"Task {task_id} not found")

    with tx() as conn:
        if old_phase_id == new_phase_id:
            conn.execute("""
                INSERT INTO task_updates (task_id, changed_at_utc, reason, old_phase_id, new_phase_id, note)
                VALUES (?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 'Note', ?, ?, ?)
            """, (task_id, old_phase_id, new_phase_id, note or "No phase change"))
            return old_phase_id, new_phase_id

        if not is_allowed_phase_change(old_phase_id, new_phase_id):
            raise ValueError(f"Phase change not allowed: {old_phase_id} → {new_phase_id}")

        conn.execute("""
            UPDATE tasks
               SET phase_id = ?, updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
             WHERE id = ?
        """, (new_phase_id, task_id))
        conn.execute("""
            INSERT INTO task_updates (task_id, changed_at_utc, reason, old_phase_id, new_phase_id, note)
            VALUES (?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 'Phase Change', ?, ?, ?)
        """, (task_id, old_phase_id, new_phase_id, note))
        logging.info("Task %s phase change: %s -> %s", task_id, old_phase_id, new_phase_id)
        return old_phase_id, new_phase_id

# ─────────────────────────────────────────────────────────────
# Subtask services
# ─────────────────────────────────────────────────────────────
def change_subtask_phase(subtask_id: int, new_phase_id: int, note: str = "") -> Tuple[int, int]:
    old_phase_id = current_phase_id_for("subtasks", "id", subtask_id)
    if old_phase_id is None:
        raise ValueError(f"Subtask {subtask_id} not found")

    with tx() as conn:
        if old_phase_id == new_phase_id:
            conn.execute("""
                INSERT INTO subtask_updates (subtask_id, changed_at_utc, reason, old_phase_id, new_phase_id, note)
                VALUES (?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 'Note', ?, ?, ?)
            """, (subtask_id, old_phase_id, new_phase_id, note or "No phase change"))
            return old_phase_id, new_phase_id

        if not is_allowed_phase_change(old_phase_id, new_phase_id):
            raise ValueError(f"Phase change not allowed: {old_phase_id} → {new_phase_id}")

        conn.execute("""
            UPDATE subtasks
               SET phase_id = ?, updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
             WHERE id = ?
        """, (new_phase_id, subtask_id))
        conn.execute("""
            INSERT INTO subtask_updates (subtask_id, changed_at_utc, reason, old_phase_id, new_phase_id, note)
            VALUES (?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 'Phase Change', ?, ?, ?)
        """, (subtask_id, old_phase_id, new_phase_id, note))
        logging.info("Subtask %s phase change: %s -> %s", subtask_id, old_phase_id, new_phase_id)
        return old_phase_id, new_phase_id

# ── Single item getters ───────────────────────────────────────

def get_task(task_id: int) -> Optional[Dict]:
    with tx() as conn:
        return conn.execute("""
            SELECT t.*, ph.name AS phase_name
            FROM tasks t
            JOIN phases ph ON ph.id = t.phase_id
            WHERE t.id = ?
        """, (task_id,)).fetchone()

def get_subtask(subtask_id: int) -> Optional[Dict]:
    with tx() as conn:
        return conn.execute("""
            SELECT s.*, ph.name AS phase_name
            FROM subtasks s
            JOIN phases ph ON ph.id = s.phase_id
            WHERE s.id = ?
        """, (subtask_id,)).fetchone()

# ── Histories ─────────────────────────────────────────────────

def list_task_updates(task_id: int) -> List[Dict]:
    with tx() as conn:
        return conn.execute("""
            SELECT u.id, u.changed_at_utc, u.reason,
                   (SELECT name FROM phases WHERE id = u.old_phase_id) AS old_phase,
                   (SELECT name FROM phases WHERE id = u.new_phase_id) AS new_phase,
                   u.note
            FROM task_updates u
            WHERE u.task_id = ?
            ORDER BY u.changed_at_utc DESC, u.id DESC
        """, (task_id,)).fetchall()

def list_subtask_updates(subtask_id: int) -> List[Dict]:
    with tx() as conn:
        return conn.execute("""
            SELECT u.id, u.changed_at_utc, u.reason,
                   (SELECT name FROM phases WHERE id = u.old_phase_id) AS old_phase,
                   (SELECT name FROM phases WHERE id = u.new_phase_id) AS new_phase,
                   u.note
            FROM subtask_updates u
            WHERE u.subtask_id = ?
            ORDER BY u.changed_at_utc DESC, u.id DESC
        """, (subtask_id,)).fetchall()

