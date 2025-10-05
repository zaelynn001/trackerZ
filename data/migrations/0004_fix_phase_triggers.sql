-- data/migrations/0004_fix_phase_triggers.sql
-- Fix: remove unsafe PRAGMA usage inside triggers; recreate validation triggers safely.

BEGIN;

-- ----------------------------
-- TASKS: validation (no PRAGMA)
-- ----------------------------
DROP TRIGGER IF EXISTS trg_tasks_phase_validate;
CREATE TRIGGER trg_tasks_phase_validate
BEFORE UPDATE OF phase_id ON tasks
FOR EACH ROW
BEGIN
  -- Block no-op
  SELECT CASE
           WHEN NEW.phase_id = OLD.phase_id
           THEN RAISE(ABORT, 'no_change')
         END;

  -- Block leaving Closed
  SELECT CASE
           WHEN EXISTS (
             SELECT 1 FROM phases p WHERE p.id = OLD.phase_id AND p.name = 'Closed'
           )
           THEN RAISE(ABORT, 'invalid_transition')
         END;

  -- Enforce allowed transitions
  SELECT CASE
           WHEN NOT EXISTS (
             SELECT 1
             FROM phase_transitions t
             WHERE t.from_phase_id = OLD.phase_id
               AND t.to_phase_id   = NEW.phase_id
           )
           THEN RAISE(ABORT, 'invalid_transition')
         END;
END;

-- ----------------------------
-- SUBTASKS: validation (no PRAGMA)
-- ----------------------------
DROP TRIGGER IF EXISTS trg_subtasks_phase_validate;
CREATE TRIGGER trg_subtasks_phase_validate
BEFORE UPDATE OF phase_id ON subtasks
FOR EACH ROW
BEGIN
  -- Block no-op
  SELECT CASE
           WHEN NEW.phase_id = OLD.phase_id
           THEN RAISE(ABORT, 'no_change')
         END;

  -- Block leaving Closed
  SELECT CASE
           WHEN EXISTS (
             SELECT 1 FROM phases p WHERE p.id = OLD.phase_id AND p.name = 'Closed'
           )
           THEN RAISE(ABORT, 'invalid_transition')
         END;

  -- Enforce allowed transitions
  SELECT CASE
           WHEN NOT EXISTS (
             SELECT 1
             FROM phase_transitions t
             WHERE t.from_phase_id = OLD.phase_id
               AND t.to_phase_id   = NEW.phase_id
           )
           THEN RAISE(ABORT, 'invalid_transition')
         END;
END;

COMMIT;

