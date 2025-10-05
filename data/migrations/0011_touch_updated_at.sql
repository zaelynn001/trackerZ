BEGIN;

DROP TRIGGER IF EXISTS trg_tasks_touch_updated_at_on_phase;
CREATE TRIGGER trg_tasks_touch_updated_at_on_phase
AFTER UPDATE OF phase_id ON tasks
FOR EACH ROW
BEGIN
  UPDATE tasks
  SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
  WHERE id = NEW.id;
END;

DROP TRIGGER IF EXISTS trg_subtasks_touch_updated_at_on_phase;
CREATE TRIGGER trg_subtasks_touch_updated_at_on_phase
AFTER UPDATE OF phase_id ON subtasks
FOR EACH ROW
BEGIN
  UPDATE subtasks
  SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
  WHERE id = NEW.id;
END;

COMMIT;

