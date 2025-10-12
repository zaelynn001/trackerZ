-- Rev 0.0.1

-- Indexes + reason autofill for task_updates and subtask_updates (Rev 0.1.0)
PRAGMA foreign_keys=ON;


BEGIN;


-- ===== Indexes =====
CREATE INDEX IF NOT EXISTS idx_task_updates_task_id_created_at
ON task_updates(task_id, created_at_utc);
CREATE INDEX IF NOT EXISTS idx_task_updates_created_at
ON task_updates(created_at_utc);


CREATE INDEX IF NOT EXISTS idx_subtask_updates_subtask_id_created_at
ON subtask_updates(subtask_id, created_at_utc);
CREATE INDEX IF NOT EXISTS idx_subtask_updates_created_at
ON subtask_updates(created_at_utc);


-- ===== Triggers: autofill reason with same semantics used for project_updates =====
-- task_updates
DROP TRIGGER IF EXISTS trg_task_updates_autofill_reason;
CREATE TRIGGER trg_task_updates_autofill_reason
AFTER INSERT ON task_updates
FOR EACH ROW
BEGIN
-- normalize empty string to NULL
UPDATE task_updates
SET reason = NULL
WHERE id = NEW.id AND (reason = '' OR reason IS NULL);


-- precedence: phase_change
UPDATE task_updates
SET reason = 'phase_change'
WHERE id = NEW.id
AND reason IS NULL
AND old_phase_id IS NOT NULL
AND new_phase_id IS NOT NULL
AND old_phase_id <> new_phase_id;


-- precedence: note
UPDATE task_updates
SET reason = 'note'
WHERE id = NEW.id
AND reason IS NULL
AND note IS NOT NULL
AND trim(note) <> '';


-- fallback
UPDATE task_updates
SET reason = 'update'
WHERE id = NEW.id
AND reason IS NULL;
END;


-- subtask_updates
DROP TRIGGER IF EXISTS trg_subtask_updates_autofill_reason;
CREATE TRIGGER trg_subtask_updates_autofill_reason
AFTER INSERT ON subtask_updates
FOR EACH ROW
BEGIN
-- normalize empty string to NULL
UPDATE subtask_updates
SET reason = NULL
WHERE id = NEW.id AND (reason = '' OR reason IS NULL);


-- precedence: phase_change
UPDATE subtask_updates
SET reason = 'phase_change'
WHERE id = NEW.id
AND reason IS NULL
AND old_phase_id IS NOT NULL
AND new_phase_id IS NOT NULL
AND old_phase_id <> new_phase_id;


-- precedence: note
UPDATE subtask_updates
SET reason = 'note'
WHERE id = NEW.id
AND reason IS NULL
AND note IS NOT NULL
AND trim(note) <> '';


-- fallback
UPDATE subtask_updates
SET reason = 'update'
WHERE id = NEW.id
AND reason IS NULL;
END;


-- ===== Backfill existing rows (if any) =====
-- tasks
UPDATE task_updates SET reason = NULL WHERE reason = '' OR reason IS NULL;
UPDATE task_updates
SET reason = CASE
WHEN old_phase_id IS NOT NULL AND new_phase_id IS NOT NULL AND old_phase_id <> new_phase_id THEN 'phase_change'
WHEN note IS NOT NULL AND trim(note) <> '' THEN 'note'
ELSE 'update'
END
WHERE reason IS NULL;


-- subtasks
UPDATE subtask_updates SET reason = NULL WHERE reason = '' OR reason IS NULL;
UPDATE subtask_updates
SET reason = CASE
WHEN old_phase_id IS NOT NULL AND new_phase_id IS NOT NULL AND old_phase_id <> new_phase_id THEN 'phase_change'
WHEN note IS NOT NULL AND trim(note) <> '' THEN 'note'
ELSE 'update'
END
WHERE reason IS NULL;


COMMIT;
