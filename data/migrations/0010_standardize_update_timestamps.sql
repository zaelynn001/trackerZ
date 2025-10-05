-- data/migrations/0010_standardize_update_timestamps.sql
-- Goal: replace occurred_at_utc with changed_at_utc on *_updates tables.

BEGIN;

-- ===== TASK UPDATES =====
-- 1) Create new table with desired schema
CREATE TABLE IF NOT EXISTS task_updates_new (
  id              INTEGER PRIMARY KEY,
  task_id         INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  changed_at_utc  TEXT    NOT NULL,
  old_phase_id    INTEGER,
  new_phase_id    INTEGER,
  note            TEXT
);

-- 2) Copy existing data, mapping occurred_at_utc -> changed_at_utc
INSERT INTO task_updates_new (id, task_id, changed_at_utc, old_phase_id, new_phase_id, note)
SELECT
  id,
  task_id,
  occurred_at_utc,             -- rename
  old_phase_id,
  new_phase_id,
  note
FROM task_updates;

-- 3) Swap tables
DROP TABLE task_updates;
ALTER TABLE task_updates_new RENAME TO task_updates;

-- 4) Helpful index (idempotent in case it already exists)
CREATE INDEX IF NOT EXISTS idx_task_updates_task_id ON task_updates(task_id);

-- ===== SUBTASK UPDATES =====
CREATE TABLE IF NOT EXISTS subtask_updates_new (
  id              INTEGER PRIMARY KEY,
  subtask_id      INTEGER NOT NULL REFERENCES subtasks(id) ON DELETE CASCADE,
  changed_at_utc  TEXT    NOT NULL,
  old_phase_id    INTEGER,
  new_phase_id    INTEGER,
  note            TEXT
);

INSERT INTO subtask_updates_new (id, subtask_id, changed_at_utc, old_phase_id, new_phase_id, note)
SELECT
  id,
  subtask_id,
  occurred_at_utc,             -- rename
  old_phase_id,
  new_phase_id,
  note
FROM subtask_updates;

DROP TABLE subtask_updates;
ALTER TABLE subtask_updates_new RENAME TO subtask_updates;

CREATE INDEX IF NOT EXISTS idx_subtask_updates_subtask_id ON subtask_updates(subtask_id);

COMMIT;

