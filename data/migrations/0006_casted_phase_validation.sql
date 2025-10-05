-- data/migrations/0006_casted_phase_validation.sql
-- Enforce phase transitions with explicit integer casting to avoid type-affinity mismatches.

BEGIN;

-- TASKS
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

  -- Block leaving Closed (terminal)
  SELECT CASE
           WHEN EXISTS (
             SELECT 1
             FROM phases p
             WHERE CAST(p.id AS INTEGER) = CAST(OLD.phase_id AS INTEGER)
               AND p.name = 'Closed'
           )
           THEN RAISE(ABORT, 'invalid_transition')
         END;

  -- Enforce allowed transitions with explicit CASTs
  SELECT CASE
           WHEN NOT EXISTS (
             SELECT 1
             FROM phase_transitions t
             WHERE CAST(t.from_phase_id AS INTEGER) = CAST(OLD.phase_id AS INTEGER)
               AND CAST(t.to_phase_id   AS INTEGER) = CAST(NEW.phase_id AS INTEGER)
           )
           THEN RAISE(ABORT, 'invalid_transition')
         END;
END;

-- SUBTASKS
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

  -- Block leaving Closed (terminal)
  SELECT CASE
           WHEN EXISTS (
             SELECT 1
             FROM phases p
             WHERE CAST(p.id AS INTEGER) = CAST(OLD.phase_id AS INTEGER)
               AND p.name = 'Closed'
           )
           THEN RAISE(ABORT, 'invalid_transition')
         END;

  -- Enforce allowed transitions with explicit CASTs
  SELECT CASE
           WHEN NOT EXISTS (
             SELECT 1
             FROM phase_transitions t
             WHERE CAST(t.from_phase_id AS INTEGER) = CAST(OLD.phase_id AS INTEGER)
               AND CAST(t.to_phase_id   AS INTEGER) = CAST(NEW.phase_id AS INTEGER)
           )
           THEN RAISE(ABORT, 'invalid_transition')
         END;
END;

COMMIT;

