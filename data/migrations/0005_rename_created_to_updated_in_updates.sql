-- Rev 0.2.0: Add index to speed timeline queries
-- 0008_rename_created_to_updated_in_updates.sql
-- Purpose: Rename created_at_utc -> updated_at_utc across *_updates tables
-- and update related indexes to match the new column name.

BEGIN TRANSACTION;

-- project_updates
ALTER TABLE project_updates RENAME COLUMN created_at_utc TO updated_at_utc;
DROP INDEX IF EXISTS idx_project_updates_created_at;
DROP INDEX IF EXISTS idx_project_updates_project_id_created_at;
CREATE INDEX IF NOT EXISTS idx_project_updates_updated_at
  ON project_updates(updated_at_utc);
CREATE INDEX IF NOT EXISTS idx_project_updates_project_id_updated_at
  ON project_updates(project_id, updated_at_utc);

-- task_updates
ALTER TABLE task_updates RENAME COLUMN created_at_utc TO updated_at_utc;
DROP INDEX IF EXISTS idx_task_updates_created_at;
DROP INDEX IF EXISTS idx_task_updates_task_id_created_at;
CREATE INDEX IF NOT EXISTS idx_task_updates_updated_at
  ON task_updates(updated_at_utc);
CREATE INDEX IF NOT EXISTS idx_task_updates_task_id_updated_at
  ON task_updates(task_id, updated_at_utc);

-- subtask_updates
ALTER TABLE subtask_updates RENAME COLUMN created_at_utc TO updated_at_utc;
DROP INDEX IF EXISTS idx_subtask_updates_created_at;
DROP INDEX IF EXISTS idx_subtask_updates_subtask_id_created_at;
CREATE INDEX IF NOT EXISTS idx_subtask_updates_updated_at
  ON subtask_updates(updated_at_utc);
CREATE INDEX IF NOT EXISTS idx_subtask_updates_subtask_id_updated_at
  ON subtask_updates(subtask_id, updated_at_utc);

COMMIT;
