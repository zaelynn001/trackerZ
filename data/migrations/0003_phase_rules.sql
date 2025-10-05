-- data/migrations/0003_phase_rules.sql
-- Canonical phase rules & touch triggers
-- Safe to re-run if guards exist.

BEGIN;

-- Ensure canonical phases exist (idempotent inserts)
INSERT INTO phases(id, name)
SELECT 1, 'Open'
WHERE NOT EXISTS (SELECT 1 FROM phases WHERE id=1);

INSERT INTO phases(id, name)
SELECT 2, 'In Progress'
WHERE NOT EXISTS (SELECT 1 FROM phases WHERE id=2);

INSERT INTO phases(id, name)
SELECT 3, 'In Hiatus'
WHERE NOT EXISTS (SELECT 1 FROM phases WHERE id=3);

INSERT INTO phases(id, name)
SELECT 4, 'Resolved'
WHERE NOT EXISTS (SELECT 1 FROM phases WHERE id=4);

INSERT INTO phases(id, name)
SELECT 5, 'Closed'
WHERE NOT EXISTS (SELECT 1 FROM phases WHERE id=5);

-- Allowed transitions (idempotent)
INSERT INTO phase_transitions(from_phase_id, to_phase_id)
SELECT 1, 2
WHERE NOT EXISTS (SELECT 1 FROM phase_transitions WHERE from_phase_id=1 AND to_phase_id=2);

INSERT INTO phase_transitions(from_phase_id, to_phase_id)
SELECT 2, 3
WHERE NOT EXISTS (SELECT 1 FROM phase_transitions WHERE from_phase_id=2 AND to_phase_id=3);

INSERT INTO phase_transitions(from_phase_id, to_phase_id)
SELECT 2, 4
WHERE NOT EXISTS (SELECT 1 FROM phase_transitions WHERE from_phase_id=2 AND to_phase_id=4);

INSERT INTO phase_transitions(from_phase_id, to_phase_id)
SELECT 3, 2
WHERE NOT EXISTS (SELECT 1 FROM phase_transitions WHERE from_phase_id=3 AND to_phase_id=2);

INSERT INTO phase_transitions(from_phase_id, to_phase_id)
SELECT 4, 5
WHERE NOT EXISTS (SELECT 1 FROM phase_transitions WHERE from_phase_id=4 AND to_phase_id=5);

-- Helper views for readability (drop/create idempotent)
DROP VIEW IF EXISTS v_phase_names;
CREATE VIEW v_phase_names AS
SELECT id AS phase_id, name FROM phases;

-- ----------------------------
-- TASKS: validation & touch
-- ----------------------------

-- Validation BEFORE UPDATE: block no-ops, block illegal transitions, block leaving Closed
DROP TRIGGER IF EXISTS trg_tasks_phase_validate;
CREATE TRIGGER trg_tasks_phase_validate
BEFORE UPDATE OF phase_id ON tasks
FOR EACH ROW
BEGIN
  -- Block no-op
  SELECT
    CASE WHEN NEW.phase_id = OLD.phase_id
         THEN RAISE(ABORT, 'no_change') END;

  -- Block updates when current is Closed
  SELECT
    CASE
      WHEN (SELECT name FROM phases WHERE id = OLD.phase_id) = 'Closed'
      THEN RAISE(ABORT, 'invalid_transition')
    END;

  -- Enforce allowed transitions
  SELECT
    CASE
      WHEN NOT EXISTS (
        SELECT 1 FROM phase_transitions
        WHERE from_phase_id = OLD.phase_id AND to_phase_id = NEW.phase_id
      )
      THEN RAISE(ABORT, 'invalid_transition')
    END;
END;

-- Touch AFTER UPDATE: update updated_at_utc if present
DROP TRIGGER IF EXISTS trg_tasks_touch_updated_at_on_phase;
CREATE TRIGGER trg_tasks_touch_updated_at_on_phase
AFTER UPDATE OF phase_id ON tasks
FOR EACH ROW
WHEN EXISTS (
  SELECT 1 FROM pragma_table_info('tasks') WHERE name='updated_at_utc'
)
BEGIN
  UPDATE tasks
  SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
  WHERE id = NEW.id;
END;

-- ----------------------------
-- SUBTASKS: validation & touch
-- ----------------------------

DROP TRIGGER IF EXISTS trg_subtasks_phase_validate;
CREATE TRIGGER trg_subtasks_phase_validate
BEFORE UPDATE OF phase_id ON subtasks
FOR EACH ROW
BEGIN
  -- Block no-op
  SELECT
    CASE WHEN NEW.phase_id = OLD.phase_id
         THEN RAISE(ABORT, 'no_change') END;

  -- Block updates when current is Closed
  SELECT
    CASE
      WHEN (SELECT name FROM phases WHERE id = OLD.phase_id) = 'Closed'
      THEN RAISE(ABORT, 'invalid_transition')
    END;

  -- Enforce allowed transitions
  SELECT
    CASE
      WHEN NOT EXISTS (
        SELECT 1 FROM phase_transitions
        WHERE from_phase_id = OLD.phase_id AND to_phase_id = NEW.phase_id
      )
      THEN RAISE(ABORT, 'invalid_transition')
    END;
END;

DROP TRIGGER IF EXISTS trg_subtasks_touch_updated_at_on_phase;
CREATE TRIGGER trg_subtasks_touch_updated_at_on_phase
AFTER UPDATE OF phase_id ON subtasks
FOR EACH ROW
WHEN EXISTS (
  SELECT 1 FROM pragma_table_info('subtasks') WHERE name='updated_at_utc'
)
BEGIN
  UPDATE subtasks
  SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
  WHERE id = NEW.id;
END;

COMMIT;

