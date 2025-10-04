-- 0002_add_extras.sql
-- Finishes M2 (Schema v1) by adding: attachments, purchases, expenses, settings
-- All timestamps are stored as UTC ISO-8601 strings (e.g., 2025-10-03T20:15:00Z)
-- SQLite dialect

BEGIN;

----------------------------------------------------------------------
-- ATTACHMENTS
-- Files live on disk; DB stores metadata and linkage.
-- An attachment must belong to a project OR a task OR a subtask.
----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS attachments (
  id                INTEGER PRIMARY KEY,
  project_id        INTEGER REFERENCES projects(id) ON DELETE CASCADE,
  task_id           INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
  subtask_id        INTEGER REFERENCES subtasks(id) ON DELETE CASCADE,
  -- file metadata
  filename          TEXT NOT NULL,                -- user-facing name
  stored_path       TEXT NOT NULL,                -- absolute or app-relative path
  mime_type         TEXT,                         -- best-effort sniffed type
  size_bytes        INTEGER CHECK (size_bytes >= 0),
  sha256_hex        TEXT,                         -- optional content checksum
  -- bookkeeping
  created_at_utc    TEXT NOT NULL,
  updated_at_utc    TEXT NOT NULL,
  note              TEXT,
  -- enforce at least one linkage
  CHECK (
    project_id IS NOT NULL OR
    task_id    IS NOT NULL OR
    subtask_id IS NOT NULL
  )
);

CREATE INDEX IF NOT EXISTS idx_attachments_project   ON attachments(project_id);
CREATE INDEX IF NOT EXISTS idx_attachments_task      ON attachments(task_id);
CREATE INDEX IF NOT EXISTS idx_attachments_subtask   ON attachments(subtask_id);
CREATE INDEX IF NOT EXISTS idx_attachments_updated   ON attachments(updated_at_utc);

----------------------------------------------------------------------
-- PURCHASES
-- Lightweight purchase order tracking tied to a project, optional task/subtask.
----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS purchases (
  id                INTEGER PRIMARY KEY,
  project_id        INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  task_id           INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
  subtask_id        INTEGER REFERENCES subtasks(id) ON DELETE SET NULL,
  status            TEXT NOT NULL DEFAULT 'draft'
                      CHECK (status IN ('draft','submitted','approved','ordered','received','cancelled')),
  vendor            TEXT,
  reference_code    TEXT,                         -- PO number, invoice, etc.
  description       TEXT,
  total_cents       INTEGER NOT NULL DEFAULT 0 CHECK (total_cents >= 0),
  currency          TEXT NOT NULL DEFAULT 'USD',
  requested_by      TEXT,                         -- freeform username/display
  ordered_at_utc    TEXT,                         -- when placed
  received_at_utc   TEXT,                         -- when goods received
  created_at_utc    TEXT NOT NULL,
  updated_at_utc    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_purchases_project   ON purchases(project_id);
CREATE INDEX IF NOT EXISTS idx_purchases_task      ON purchases(task_id);
CREATE INDEX IF NOT EXISTS idx_purchases_subtask   ON purchases(subtask_id);
CREATE INDEX IF NOT EXISTS idx_purchases_status    ON purchases(status);
CREATE INDEX IF NOT EXISTS idx_purchases_updated   ON purchases(updated_at_utc);

----------------------------------------------------------------------
-- EXPENSES
-- Simple expense records per project with optional task/subtask linkage.
-- Optional receipt attachment via attachments.id.
----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS expenses (
  id                    INTEGER PRIMARY KEY,
  project_id            INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  task_id               INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
  subtask_id            INTEGER REFERENCES subtasks(id) ON DELETE SET NULL,
  category              TEXT,                      -- e.g., 'materials','labor','shipping','misc'
  description           TEXT,
  amount_cents          INTEGER NOT NULL CHECK (amount_cents >= 0),
  currency              TEXT NOT NULL DEFAULT 'USD',
  incurred_at_utc       TEXT NOT NULL,             -- date of expense
  receipt_attachment_id INTEGER REFERENCES attachments(id) ON DELETE SET NULL,
  created_at_utc        TEXT NOT NULL,
  updated_at_utc        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_expenses_project    ON expenses(project_id);
CREATE INDEX IF NOT EXISTS idx_expenses_task       ON expenses(task_id);
CREATE INDEX IF NOT EXISTS idx_expenses_subtask    ON expenses(subtask_id);
CREATE INDEX IF NOT EXISTS idx_expenses_category   ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_expenses_incurred   ON expenses(incurred_at_utc);
CREATE INDEX IF NOT EXISTS idx_expenses_updated    ON expenses(updated_at_utc);

----------------------------------------------------------------------
-- SETTINGS
-- App- and project-scoped key/value configuration.
-- Keys are unique per scope+project (project_id is NULL for app/global scope).
----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS settings (
  key             TEXT NOT NULL,
  scope           TEXT NOT NULL DEFAULT 'app'
                   CHECK (scope IN ('app','ui','project')),
  project_id      INTEGER REFERENCES projects(id) ON DELETE CASCADE,
  value           TEXT NOT NULL,
  updated_at_utc  TEXT NOT NULL,
  PRIMARY KEY (key, project_id)                    -- (key,NULL) is app/global
);

CREATE INDEX IF NOT EXISTS idx_settings_scope      ON settings(scope);
CREATE INDEX IF NOT EXISTS idx_settings_project    ON settings(project_id);

COMMIT;

