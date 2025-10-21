# Rev 0.6.8
"""
Developer seed for M5 CRUD + timeline tests.
Creates sample projects, phases, and tasks in the SQLite database and prints summaries.

Usage:
    python -m src.dev_seed_m5
"""

import os
import sqlite3
from pathlib import Path

from repositories.sqlite_task_repository import SQLiteTaskRepository
from repositories.sqlite_task_updates_repository import SQLiteTaskUpdatesRepository


DB_PATH = Path.home() / "Dev" / "trackerZ" / "data" / "trackerZ.db"


def seed_projects_and_phases(conn: sqlite3.Connection):
    """Ensure minimal reference data exists without assuming timestamp columns on phases."""
    cur = conn.cursor()

    # Create phases if not present (phases has NO created_at_utc/updated_at_utc)
    phases = [
        (1, "Open"),
        (2, "In Progress"),
        (3, "On Hold"),
        (4, "Resolved"),
        (5, "Closed"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO phases(id, name) VALUES (?, ?)",
        phases,
    )

    # Create a sample project (avoid assuming timestamp columns here too)
    cur.execute(
        """
        INSERT OR IGNORE INTO projects(id, name, description)
        VALUES (1, 'Example Project', 'A test project for dev seeding.')
        """
    )
    conn.commit()


def run_seed():
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    seed_projects_and_phases(conn)

    tasks_repo = SQLiteTaskRepository(conn)
    updates_repo = SQLiteTaskUpdatesRepository(conn)

    print("=== Creating sample tasks ===")
    t1 = tasks_repo.create_task(project_id=1, name="Initialize repo", description="Create the repository structure.", phase_id=1)
    t2 = tasks_repo.create_task(project_id=1, name="Implement CRUD", description="CRUD implementation for tasks.", phase_id=1)

    print(f"Created task IDs: {t1}, {t2}")

    print("=== Updating task fields ===")
    tasks_repo.update_task_fields(t1, description="Repository skeleton + migrations complete.", note="Updated description")

    print("=== Changing phase for task 1 ===")
    tasks_repo.change_task_phase(t1, new_phase_id=2, reason="dev_progress", note="Started implementation")

    print("=== Adding manual note ===")
    updates_repo.add_note(t1, "Remember to add tests for phase transitions")

    print("=== Listing tasks ===")
    tasks = tasks_repo.list_tasks_filtered(project_id=1)
    for row in tasks:
        print(f"Task #{row['id']} [{row['phase_id']}] {row['name']} (updated {row['updated_at_utc']})")

    print("=== Listing timeline for task 1 ===")
    updates = updates_repo.list_updates_for_task(t1)
    for up in updates:
        print(f" - {up['updated_at_utc']}: reason={up['reason']} note={up['note']} old={up['old_phase_id']} new={up['new_phase_id']}")

    print("=== Deleting task 2 (CRUD test) ===")
    tasks_repo.delete_task(t2)

    remaining = tasks_repo.list_tasks_filtered(project_id=1)
    print(f"Remaining tasks: {[r['id'] for r in remaining]}")

    conn.close()
    print("=== Seed complete ===")


if __name__ == "__main__":
    run_seed()
