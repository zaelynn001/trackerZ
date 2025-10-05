-- data/migrations/0012_reason_autofill_task_subtask.sql
-- Apply the same "reason" autofill behavior used for project_updates
-- to task_updates and subtask_updates.

BEGIN;

-- TASK UPDATES: reason autofill
DROP TRIGGER IF EXISTS trg_task_updates_reason_autofill;
CREATE TRIGGER trg_task_updates_reason_autofill
BEFORE INSERT ON task_updates
FOR EACH ROW
BEGIN
  -- Normalize empty string to NULL for easier checks
  SELECT CASE WHEN NEW.reason = '' THEN NEW.reason = NULL END;

  -- If reason is not provided:
  --  - If old/new phase IDs are both present and differ -> 'phase_change'
  --  - Else if only note is present -> 'note'
  --  - Else -> generic 'update'
  SELECT
    CASE
      WHEN NEW.reason IS NULL AND NEW.old_phase_id IS NOT NULL AND NEW.new_phase_id IS NOT NULL AND NEW.old_phase_id <> NEW.new_phase_id
        THEN NEW.reason = 'phase_change'
      WHEN NEW.reason IS NULL AND NEW.note IS NOT NULL
        THEN NEW.reason = 'note'
      WHEN NEW.reason IS NULL
        THEN NEW.reason = 'update'
    END;

  -- If changed_at_utc exists and is NULL, stamp it
  SELECT
    CASE
      WHEN NEW.changed_at_utc IS NULL
      THEN NEW.changed_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
    END;
END;

-- SUBTASK UPDATES: reason autofill
DROP TRIGGER IF EXISTS trg_subtask_updates_reason_autofill;
CREATE TRIGGER trg_subtask_updates_reason_autofill
BEFORE INSERT ON subtask_updates
FOR EACH ROW
BEGIN
  SELECT CASE WHEN NEW.reason = '' THEN NEW.reason = NULL END;

  SELECT
    CASE
      WHEN NEW.reason IS NULL AND NEW.old_phase_id IS NOT NULL AND NEW.new_phase_id IS NOT NULL AND NEW.old_phase_id <> NEW.new_phase_id
        THEN NEW.reason = 'phase_change'
      WHEN NEW.reason IS NULL AND NEW.note IS NOT NULL
        THEN NEW.reason = 'note'
      WHEN NEW.reason IS NULL
        THEN NEW.reason = 'update'
    END;

  SELECT
    CASE
      WHEN NEW.changed_at_utc IS NULL
      THEN NEW.changed_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
    END;
END;

COMMIT;

