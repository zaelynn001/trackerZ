-- Rev 0.0.1

-- Indexes + reason autofill for project_updates (Rev 0.1.0)
PRAGMA foreign_keys=ON;


BEGIN;


-- Helpful indexes for timelines and per‑project queries
CREATE INDEX IF NOT EXISTS idx_project_updates_project_id_created_at
ON project_updates(project_id, created_at_utc);
CREATE INDEX IF NOT EXISTS idx_project_updates_created_at
ON project_updates(created_at_utc);


-- Autofill 'reason' semantics, mirroring task/subtask plans
-- Precedence:
-- 1) phase_change (both phases present and differ)
-- 2) note (note present and non-empty)
-- 3) update (fallback)
DROP TRIGGER IF EXISTS trg_project_updates_autofill_reason;
CREATE TRIGGER trg_project_updates_autofill_reason
AFTER INSERT ON project_updates
FOR EACH ROW
BEGIN
-- normalize empty string to NULL
UPDATE project_updates
SET reason = NULL
WHERE id = NEW.id AND (reason = '' OR reason IS NULL);


-- precedence: phase_change
UPDATE project_updates
SET reason = 'phase_change'
WHERE id = NEW.id
AND reason IS NULL
AND old_phase_id IS NOT NULL
AND new_phase_id IS NOT NULL
AND old_phase_id <> new_phase_id;


-- precedence: note
UPDATE project_updates
SET reason = 'note'
WHERE id = NEW.id
AND reason IS NULL
AND note IS NOT NULL
AND trim(note) <> '';


-- fallback
UPDATE project_updates
SET reason = 'update'
WHERE id = NEW.id
AND reason IS NULL;
END;


-- Backfill existing rows (if any)
UPDATE project_updates SET reason = NULL WHERE reason = '' OR reason IS NULL;
UPDATE project_updates
SET reason = CASE
WHEN old_phase_id IS NOT NULL AND new_phase_id IS NOT NULL AND old_phase_id <> new_phase_id THEN 'phase_change'
WHEN note IS NOT NULL AND trim(note) <> '' THEN 'note'
ELSE 'update'
END
WHERE reason IS NULL;


COMMIT;
