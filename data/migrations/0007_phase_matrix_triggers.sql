-- data/migrations/0007_phase_matrix_triggers.sql
-- Strict phase validation using a constant matrix (no table lookups/joins/PRAGMA).
-- Matrix:
--   Open(1) -> In Progress(2)
--   In Progress(2) -> In Hiatus(3) | Resolved(4)
--   In Hiatus(3) -> In Progress(2)
--   Resolved(4) -> Closed(5)
--   Closed(5) -> (terminal)

BEGIN;

-- TASKS
DROP TRIGGER IF EXISTS trg_tasks_phase_validate;
CREATE TRIGGER trg_tasks_phase_validate
BEFORE UPDATE OF phase_id ON tasks
FOR EACH ROW
BEGIN
  -- no-op
  SELECT CASE WHEN NEW.phase_id = OLD.phase_id
              THEN RAISE(ABORT, 'no_change') END;

  -- closed is terminal
  SELECT CASE WHEN CAST(OLD.phase_id AS INTEGER) = 5
              THEN RAISE(ABORT, 'invalid_transition') END;

  -- matrix check (IDs as constants; CAST guards odd affinities)
  SELECT CASE
           WHEN NOT (
             (CAST(OLD.phase_id AS INTEGER) = 1 AND CAST(NEW.phase_id AS INTEGER) IN (2)) OR
             (CAST(OLD.phase_id AS INTEGER) = 2 AND CAST(NEW.phase_id AS INTEGER) IN (3,4)) OR
             (CAST(OLD.phase_id AS INTEGER) = 3 AND CAST(NEW.phase_id AS INTEGER) IN (2)) OR
             (CAST(OLD.phase_id AS INTEGER) = 4 AND CAST(NEW.phase_id AS INTEGER) IN (5))
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
  -- no-op
  SELECT CASE WHEN NEW.phase_id = OLD.phase_id
              THEN RAISE(ABORT, 'no_change') END;

  -- closed is terminal
  SELECT CASE WHEN CAST(OLD.phase_id AS INTEGER) = 5
              THEN RAISE(ABORT, 'invalid_transition') END;

  -- same matrix
  SELECT CASE
           WHEN NOT (
             (CAST(OLD.phase_id AS INTEGER) = 1 AND CAST(NEW.phase_id AS INTEGER) IN (2)) OR
             (CAST(OLD.phase_id AS INTEGER) = 2 AND CAST(NEW.phase_id AS INTEGER) IN (3,4)) OR
             (CAST(OLD.phase_id AS INTEGER) = 3 AND CAST(NEW.phase_id AS INTEGER) IN (2)) OR
             (CAST(OLD.phase_id AS INTEGER) = 4 AND CAST(NEW.phase_id AS INTEGER) IN (5))
           )
           THEN RAISE(ABORT, 'invalid_transition')
         END;
END;

COMMIT;

