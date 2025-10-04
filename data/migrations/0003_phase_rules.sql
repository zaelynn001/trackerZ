-- 0003-phase-rules.sql
-- Enforce allowed phase transitions via phases/phase_transitions (no manager gating)
-- SQLite dialect

BEGIN IMMEDIATE TRANSACTION;

PRAGMA foreign_keys = ON;

----------------------------------------------------------------------
-- Diagnostic views (optional)
----------------------------------------------------------------------

DROP VIEW IF EXISTS v_invalid_task_phase_fk;
CREATE VIEW v_invalid_task_phase_fk AS
SELECT t.id, t.phase_id
FROM tasks t
LEFT JOIN phases ph ON ph.id = t.phase_id
WHERE ph.id IS NULL;

DROP VIEW IF EXISTS v_invalid_subtask_phase_fk;
CREATE VIEW v_invalid_subtask_phase_fk AS
SELECT s.id, s.phase_id
FROM subtasks s
LEFT JOIN phases ph ON ph.id = s.phase_id
WHERE ph.id IS NULL;

----------------------------------------------------------------------
-- Tasks: validate phase transitions before update
----------------------------------------------------------------------

DROP TRIGGER IF EXISTS trg_tasks_phase_validate;
CREATE TRIGGER trg_tasks_phase_validate
BEFORE UPDATE OF phase_id ON tasks
FOR EACH ROW
BEGIN
  -- Block no-op
  SELECT
    CASE
      WHEN NEW.phase_id = OLD.phase_id THEN
        RAISE(ABORT, 'no_change')
      -- Block leaving a terminal phase
      WHEN (SELECT is_terminal FROM phases WHERE id = OLD.phase_id) = 1 THEN
        RAISE(ABORT, 'invalid_transition: terminal phase cannot change')
      -- Allow only if a row exists in phase_transitions (from=old -> to=new)
      WHEN EXISTS (
        SELECT 1
        FROM phase_transitions pt
        WHERE pt.from_phase_id = OLD.phase_id
          AND pt.to_phase_id   = NEW.phase_id
      ) THEN
        NULL
      ELSE
        RAISE(ABORT, 'invalid_transition')
    END;
END;

----------------------------------------------------------------------
-- Subtasks: validate phase transitions before update
----------------------------------------------------------------------

DROP TRIGGER IF EXISTS trg_subtasks_phase_validate;
CREATE TRIGGER trg_subtasks_phase_validate
BEFORE UPDATE OF phase_id ON subtasks
FOR EACH ROW
BEGIN
  SELECT
    CASE
      WHEN NEW.phase_id = OLD.phase_id THEN
        RAISE(ABORT, 'no_change')
      WHEN (SELECT is_terminal FROM phases WHERE id = OLD.phase_id) = 1 THEN
        RAISE(ABORT, 'invalid_transition: terminal phase cannot change')
      WHEN EXISTS (
        SELECT 1
        FROM phase_transitions pt
        WHERE pt.from_phase_id = OLD.phase_id
          AND pt.to_phase_id   = NEW.phase_id
      ) THEN
        NULL
      ELSE
        RAISE(ABORT, 'invalid_transition')
    END;
END;

----------------------------------------------------------------------
-- Touch updated_at_utc after a successful phase change
----------------------------------------------------------------------

DROP TRIGGER IF EXISTS trg_tasks_touch_updated_at_on_phase;
CREATE TRIGGER trg_tasks_touch_updated_at_on_phase
AFTER UPDATE OF phase_id ON tasks
FOR EACH ROW
BEGIN
  UPDATE tasks
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%fZ','now')
   WHERE id = NEW.id;
END;

DROP TRIGGER IF EXISTS trg_subtasks_touch_updated_at_on_phase;
CREATE TRIGGER trg_subtasks_touch_updated_at_on_phase
AFTER UPDATE OF phase_id ON subtasks
FOR EACH ROW
BEGIN
  UPDATE subtasks
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%fZ','now')
   WHERE id = NEW.id;
END;

----------------------------------------------------------------------
-- Helpful indexes (if not already present)
----------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_phase_transitions_from_to
  ON phase_transitions(from_phase_id, to_phase_id);

-- (tasks/subtasks phase & updated indexes exist from earlier migrations)

COMMIT;

