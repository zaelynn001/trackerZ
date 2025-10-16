-- Rev 1.1.0 — trackerZ consolidated baseline (priorities + strict NOT NULLs)
-- One-shot schema with seeds, triggers, and indexes.
-- Conventions:
--   • Only NOTE columns may be NULL. All other columns are NOT NULL.
--   • *_updates tables use updated_at_utc (NOT created_at_utc)
--   • Phase validation triggers + "touch updated_at_utc" on tasks/subtasks phase change
--   • Reason-autofill triggers on project/task/subtask updates (phase_change, priority_change, note, fallback=update)
--   • Timestamps default to UTC ISO 8601 with 'Z'

PRAGMA foreign_keys = ON;

BEGIN;

-- =========================
-- Phases + Allowed Changes
-- =========================
CREATE TABLE IF NOT EXISTS phases (
  id   INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

INSERT OR IGNORE INTO phases(id, name) VALUES
  (1,'Open'),
  (2,'In Progress'),
  (3,'In Hiatus'),
  (4,'Resolved'),
  (5,'Closed');

CREATE TABLE IF NOT EXISTS phase_transitions (
  from_phase_id INTEGER NOT NULL,
  to_phase_id   INTEGER NOT NULL,
  PRIMARY KEY (from_phase_id, to_phase_id),
  FOREIGN KEY (from_phase_id) REFERENCES phases(id),
  FOREIGN KEY (to_phase_id)   REFERENCES phases(id)
);

-- Practical default policy (adjust in M3 if needed)
INSERT OR IGNORE INTO phase_transitions(from_phase_id, to_phase_id) VALUES
  (1,2),(2,3),(2,4),(4,5),(1,5),(3,2),(3,4);

-- ==========
-- Priorities
-- ==========
CREATE TABLE IF NOT EXISTS priorities (
  id   INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

INSERT OR IGNORE INTO priorities (id, name) VALUES
  (1,'Low'),
  (2,'Medium'),
  (3,'High'),
  (4,'Critical');

-- ========
-- Projects
-- ========
CREATE TABLE IF NOT EXISTS projects (
  id              INTEGER PRIMARY KEY,
  name            TEXT    NOT NULL,
  description     TEXT    NOT NULL DEFAULT '',
  phase_id        INTEGER NOT NULL DEFAULT 1,   -- new
  priority_id     INTEGER NOT NULL DEFAULT 2,   -- new
  created_at_utc  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  FOREIGN KEY (phase_id)    REFERENCES phases(id),
  FOREIGN KEY (priority_id) REFERENCES priorities(id)
);

-- =====
-- Tasks
-- =====
CREATE TABLE IF NOT EXISTS tasks (
  id              INTEGER PRIMARY KEY,
  project_id      INTEGER NOT NULL,
  name            TEXT    NOT NULL,
  description     TEXT    NOT NULL DEFAULT '',
  phase_id        INTEGER NOT NULL DEFAULT 1,
  priority_id     INTEGER NOT NULL DEFAULT 2,   -- new
  created_at_utc  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  FOREIGN KEY (project_id)  REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (phase_id)    REFERENCES phases(id),
  FOREIGN KEY (priority_id) REFERENCES priorities(id)
);

-- =========
-- Subtasks
-- =========
CREATE TABLE IF NOT EXISTS subtasks (
  id              INTEGER PRIMARY KEY,
  task_id         INTEGER NOT NULL,
  name            TEXT    NOT NULL,
  description     TEXT    NOT NULL DEFAULT '',
  phase_id        INTEGER NOT NULL DEFAULT 1,
  priority_id     INTEGER NOT NULL DEFAULT 2,   -- new
  created_at_utc  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  FOREIGN KEY (task_id)     REFERENCES tasks(id)   ON DELETE CASCADE,
  FOREIGN KEY (phase_id)    REFERENCES phases(id),
  FOREIGN KEY (priority_id) REFERENCES priorities(id)
);

-- ============
-- Attachments
-- ============
CREATE TABLE IF NOT EXISTS attachments (
  id              INTEGER PRIMARY KEY,
  project_id      INTEGER NOT NULL,
  task_id         INTEGER,
  subtask_id      INTEGER,
  rel_path        TEXT    NOT NULL,
  label           TEXT    NOT NULL DEFAULT '',
  note            TEXT,  -- only NOTE may be NULL
  created_at_utc  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (task_id)    REFERENCES tasks(id)    ON DELETE CASCADE,
  FOREIGN KEY (subtask_id) REFERENCES subtasks(id) ON DELETE CASCADE
);

-- =========
-- Expenses
-- =========
-- New order and NOT NULL rules: id, project_id, item, supplier, type, amount, purchaser, created_at_utc, order_id, note
CREATE TABLE IF NOT EXISTS expenses (
  id              INTEGER PRIMARY KEY,
  project_id      INTEGER NOT NULL,
  item            TEXT    NOT NULL,
  supplier        TEXT    NOT NULL,
  type            TEXT    NOT NULL,
  amount          NUMERIC NOT NULL,
  purchaser       TEXT    NOT NULL,
  created_at_utc  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  order_id        TEXT    NOT NULL,
  note            TEXT,  -- only NOTE may be NULL
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- ========
-- Settings
-- ========
CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- ==========================
-- Timeline / Updates Tables
-- ==========================

-- Project-level updates
CREATE TABLE IF NOT EXISTS project_updates (
  id               INTEGER PRIMARY KEY,
  project_id       INTEGER NOT NULL,
  old_phase_id     INTEGER NOT NULL DEFAULT 1,
  new_phase_id     INTEGER NOT NULL DEFAULT 1,
  old_priority_id  INTEGER NOT NULL DEFAULT 2,  -- new
  new_priority_id  INTEGER NOT NULL DEFAULT 2,  -- new
  note             TEXT,                        -- only NOTE may be NULL
  reason           TEXT NOT NULL,               -- will be auto-filled by trigger
  updated_at_utc   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  FOREIGN KEY (project_id)      REFERENCES projects(id)   ON DELETE CASCADE,
  FOREIGN KEY (old_phase_id)    REFERENCES phases(id),
  FOREIGN KEY (new_phase_id)    REFERENCES phases(id),
  FOREIGN KEY (old_priority_id) REFERENCES priorities(id),
  FOREIGN KEY (new_priority_id) REFERENCES priorities(id)
);

-- Task-level updates
CREATE TABLE IF NOT EXISTS task_updates (
  id               INTEGER PRIMARY KEY,
  task_id          INTEGER NOT NULL,
  old_phase_id     INTEGER NOT NULL DEFAULT 1,
  new_phase_id     INTEGER NOT NULL DEFAULT 1,
  old_priority_id  INTEGER NOT NULL DEFAULT 2,  -- new
  new_priority_id  INTEGER NOT NULL DEFAULT 2,  -- new
  note             TEXT,                        -- only NOTE may be NULL
  reason           TEXT NOT NULL,               -- auto-filled by trigger
  updated_at_utc   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  FOREIGN KEY (task_id)         REFERENCES tasks(id)    ON DELETE CASCADE,
  FOREIGN KEY (old_phase_id)    REFERENCES phases(id),
  FOREIGN KEY (new_phase_id)    REFERENCES phases(id),
  FOREIGN KEY (old_priority_id) REFERENCES priorities(id),
  FOREIGN KEY (new_priority_id) REFERENCES priorities(id)
);

-- Subtask-level updates
CREATE TABLE IF NOT EXISTS subtask_updates (
  id               INTEGER PRIMARY KEY,
  subtask_id       INTEGER NOT NULL,
  old_phase_id     INTEGER NOT NULL DEFAULT 1,
  new_phase_id     INTEGER NOT NULL DEFAULT 1,
  old_priority_id  INTEGER NOT NULL DEFAULT 2,  -- new
  new_priority_id  INTEGER NOT NULL DEFAULT 2,  -- new
  note             TEXT,                        -- only NOTE may be NULL
  reason           TEXT NOT NULL,               -- auto-filled by trigger
  updated_at_utc   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  FOREIGN KEY (subtask_id)      REFERENCES subtasks(id) ON DELETE CASCADE,
  FOREIGN KEY (old_phase_id)    REFERENCES phases(id),
  FOREIGN KEY (new_phase_id)    REFERENCES phases(id),
  FOREIGN KEY (old_priority_id) REFERENCES priorities(id),
  FOREIGN KEY (new_priority_id) REFERENCES priorities(id)
);

-- =======
-- Indexes
-- =======

-- project_updates
CREATE INDEX IF NOT EXISTS idx_project_updates_updated_at
  ON project_updates(updated_at_utc);
CREATE INDEX IF NOT EXISTS idx_project_updates_project_id_updated_at
  ON project_updates(project_id, updated_at_utc);

-- task_updates
CREATE INDEX IF NOT EXISTS idx_task_updates_updated_at
  ON task_updates(updated_at_utc);
CREATE INDEX IF NOT EXISTS idx_task_updates_task_id_updated_at
  ON task_updates(task_id, updated_at_utc);

-- subtask_updates
CREATE INDEX IF NOT EXISTS idx_subtask_updates_updated_at
  ON subtask_updates(updated_at_utc);
CREATE INDEX IF NOT EXISTS idx_subtask_updates_subtask_id_updated_at
  ON subtask_updates(subtask_id, updated_at_utc);

-- expenses
CREATE INDEX IF NOT EXISTS idx_expenses_project_id_created_at
  ON expenses(project_id, created_at_utc);

-- ===============================
-- Phase Validation + Touch Trigs
-- ===============================

-- Disallow illegal task phase changes
DROP TRIGGER IF EXISTS trg_tasks_phase_validate;
CREATE TRIGGER trg_tasks_phase_validate
BEFORE UPDATE OF phase_id ON tasks
FOR EACH ROW
WHEN NOT EXISTS (
  SELECT 1 FROM phase_transitions pt
  WHERE pt.from_phase_id = OLD.phase_id
    AND pt.to_phase_id   = NEW.phase_id
)
BEGIN
  SELECT RAISE(ABORT, 'disallowed phase change for task');
END;

-- Touch updated_at_utc on tasks when phase changes
DROP TRIGGER IF EXISTS trg_tasks_touch_updated_at_on_phase;
CREATE TRIGGER trg_tasks_touch_updated_at_on_phase
AFTER UPDATE OF phase_id ON tasks
FOR EACH ROW
BEGIN
  UPDATE tasks
  SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
  WHERE id = NEW.id;
END;

-- Disallow illegal subtask phase changes
DROP TRIGGER IF EXISTS trg_subtasks_phase_validate;
CREATE TRIGGER trg_subtasks_phase_validate
BEFORE UPDATE OF phase_id ON subtasks
FOR EACH ROW
WHEN NOT EXISTS (
  SELECT 1 FROM phase_transitions pt
  WHERE pt.from_phase_id = OLD.phase_id
    AND pt.to_phase_id   = NEW.phase_id
)
BEGIN
  SELECT RAISE(ABORT, 'disallowed phase change for subtask');
END;

-- Touch updated_at_utc on subtasks when phase changes
DROP TRIGGER IF EXISTS trg_subtasks_touch_updated_at_on_phase;
CREATE TRIGGER trg_subtasks_touch_updated_at_on_phase
AFTER UPDATE OF phase_id ON subtasks
FOR EACH ROW
BEGIN
  UPDATE subtasks
  SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
  WHERE id = NEW.id;
END;

-- ===================================
-- Reason Autofill on *_updates tables
-- ===================================

-- Projects
DROP TRIGGER IF EXISTS trg_project_updates_autofill_reason;
CREATE TRIGGER trg_project_updates_autofill_reason
AFTER INSERT ON project_updates
FOR EACH ROW
BEGIN
  -- normalize blank to NULL for detection
  UPDATE project_updates
  SET reason = NULL
  WHERE id = NEW.id AND (reason = '' OR reason IS NULL);

  -- precedence: priority_change
  UPDATE project_updates
  SET reason = 'priority_change'
  WHERE id = NEW.id
    AND reason IS NULL
    AND NEW.old_priority_id <> NEW.new_priority_id;

  -- precedence: phase_change
  UPDATE project_updates
  SET reason = 'phase_change'
  WHERE id = NEW.id
    AND reason IS NULL
    AND NEW.old_phase_id <> NEW.new_phase_id;

  -- precedence: note
  UPDATE project_updates
  SET reason = 'note'
  WHERE id = NEW.id
    AND reason IS NULL
    AND NEW.note IS NOT NULL
    AND trim(NEW.note) <> '';

  -- fallback
  UPDATE project_updates
  SET reason = 'update'
  WHERE id = NEW.id
    AND reason IS NULL;
END;

-- Tasks
DROP TRIGGER IF EXISTS trg_task_updates_autofill_reason;
CREATE TRIGGER trg_task_updates_autofill_reason
AFTER INSERT ON task_updates
FOR EACH ROW
BEGIN
  UPDATE task_updates
  SET reason = NULL
  WHERE id = NEW.id AND (reason = '' OR reason IS NULL);

  UPDATE task_updates
  SET reason = 'priority_change'
  WHERE id = NEW.id
    AND reason IS NULL
    AND NEW.old_priority_id <> NEW.new_priority_id;

  UPDATE task_updates
  SET reason = 'phase_change'
  WHERE id = NEW.id
    AND reason IS NULL
    AND NEW.old_phase_id <> NEW.new_phase_id;

  UPDATE task_updates
  SET reason = 'note'
  WHERE id = NEW.id
    AND reason IS NULL
    AND NEW.note IS NOT NULL
    AND trim(NEW.note) <> '';

  UPDATE task_updates
  SET reason = 'update'
  WHERE id = NEW.id
    AND reason IS NULL;
END;

-- Subtasks
DROP TRIGGER IF EXISTS trg_subtask_updates_autofill_reason;
CREATE TRIGGER trg_subtask_updates_autofill_reason
AFTER INSERT ON subtask_updates
FOR EACH ROW
BEGIN
  UPDATE subtask_updates
  SET reason = NULL
  WHERE id = NEW.id AND (reason = '' OR reason IS NULL);

  UPDATE subtask_updates
  SET reason = 'priority_change'
  WHERE id = NEW.id
    AND reason IS NULL
    AND NEW.old_priority_id <> NEW.new_priority_id;

  UPDATE subtask_updates
  SET reason = 'phase_change'
  WHERE id = NEW.id
    AND reason IS NULL
    AND NEW.old_phase_id <> NEW.new_phase_id;

  UPDATE subtask_updates
  SET reason = 'note'
  WHERE id = NEW.id
    AND reason IS NULL
    AND NEW.note IS NOT NULL
    AND trim(NEW.note) <> '';

  UPDATE subtask_updates
  SET reason = 'update'
  WHERE id = NEW.id
    AND reason IS NULL;
END;

-- ========================
-- Removed legacy artifacts
-- ========================
-- purchases table removed per spec: do not create it here.

COMMIT;
