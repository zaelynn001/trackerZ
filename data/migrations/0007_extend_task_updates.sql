-- Rev 0.5.0

-- 000Y_extend_task_updates.sql
BEGIN;

-- Keep only the index (guarded) on the post-rename column name.
CREATE INDEX IF NOT EXISTS ix_task_updates_task_updated_at_utc
  ON task_updates(task_id, updated_at_utc DESC);

COMMIT;
