BEGIN;
CREATE INDEX IF NOT EXISTS idx_task_updates_task_id_updated_at_utc
  ON task_updates(task_id, updated_at_utc DESC);
COMMIT;
