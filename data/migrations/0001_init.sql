-- Rev 0.0.1

PRAGMA foreign_keys=ON;

BEGIN;


-- phases
CREATE TABLE IF NOT EXISTS phases (
id INTEGER PRIMARY KEY,
name TEXT NOT NULL UNIQUE
);


INSERT OR IGNORE INTO phases(id, name) VALUES
(1,'Open'),(2,'In Progress'),(3,'In Hiatus'),(4,'Resolved'),(5,'Closed');


-- allowed phase transitions
CREATE TABLE IF NOT EXISTS phase_transitions (
from_phase_id INTEGER NOT NULL,
to_phase_id INTEGER NOT NULL,
PRIMARY KEY (from_phase_id, to_phase_id),
FOREIGN KEY (from_phase_id) REFERENCES phases(id),
FOREIGN KEY (to_phase_id) REFERENCES phases(id)
);


-- seed a simple default policy (edit later in M3)
INSERT OR IGNORE INTO phase_transitions(from_phase_id, to_phase_id) VALUES
(1,2),(2,3),(2,4),(4,5),(1,5),(3,2),(3,4);


-- projects
CREATE TABLE IF NOT EXISTS projects (
id INTEGER PRIMARY KEY,
name TEXT NOT NULL,
description TEXT,
created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
updated_at_utc TEXT
);


-- tasks
CREATE TABLE IF NOT EXISTS tasks (
id INTEGER PRIMARY KEY,
project_id INTEGER NOT NULL,
name TEXT NOT NULL,
description TEXT,
phase_id INTEGER NOT NULL DEFAULT 1,
created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
updated_at_utc TEXT,
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
FOREIGN KEY (phase_id) REFERENCES phases(id)
);


-- subtasks
CREATE TABLE IF NOT EXISTS subtasks (
id INTEGER PRIMARY KEY,
task_id INTEGER NOT NULL,
name TEXT NOT NULL,
description TEXT,
phase_id INTEGER NOT NULL DEFAULT 1,
created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
updated_at_utc TEXT,
FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
FOREIGN KEY (phase_id) REFERENCES phases(id)
);


-- timeline tables
CREATE TABLE IF NOT EXISTS task_updates (
id INTEGER PRIMARY KEY,
task_id INTEGER NOT NULL,
old_phase_id INTEGER,
new_phase_id INTEGER,
note TEXT,
reason TEXT,
created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
FOREIGN KEY (old_phase_id) REFERENCES phases(id),
FOREIGN KEY (new_phase_id) REFERENCES phases(id)
);


CREATE TABLE IF NOT EXISTS subtask_updates (
id INTEGER PRIMARY KEY,
subtask_id INTEGER NOT NULL,
old_phase_id INTEGER,
new_phase_id INTEGER,
note TEXT,
reason TEXT,
created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
FOREIGN KEY (subtask_id) REFERENCES subtasks(id) ON DELETE CASCADE,
FOREIGN KEY (old_phase_id) REFERENCES phases(id),
FOREIGN KEY (new_phase_id) REFERENCES phases(id)
);


-- attachments (filesystem-backed)
CREATE TABLE IF NOT EXISTS attachments (
id INTEGER PRIMARY KEY,
project_id INTEGER NOT NULL,
task_id INTEGER,
subtask_id INTEGER,
rel_path TEXT NOT NULL,
label TEXT,
created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
FOREIGN KEY (subtask_id) REFERENCES subtasks(id) ON DELETE CASCADE
);


-- purchases & expenses
CREATE TABLE IF NOT EXISTS purchases (
id INTEGER PRIMARY KEY,
project_id INTEGER NOT NULL,
vendor TEXT,
amount_cents INTEGER NOT NULL,
note TEXT,
created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS expenses (
id INTEGER PRIMARY KEY,
project_id INTEGER NOT NULL,
category TEXT,
amount_cents INTEGER NOT NULL,
note TEXT,
created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);


-- settings
CREATE TABLE IF NOT EXISTS settings (
key TEXT PRIMARY KEY,
value TEXT
);


-- triggers: validate phase changes; touch updated_at on phase change via separate AFTER triggers
DROP TRIGGER IF EXISTS trg_tasks_phase_validate;
CREATE TRIGGER trg_tasks_phase_validate
BEFORE UPDATE OF phase_id ON tasks
FOR EACH ROW
WHEN NOT EXISTS (
SELECT 1 FROM phase_transitions pt
WHERE pt.from_phase_id = OLD.phase_id AND pt.to_phase_id = NEW.phase_id
)
BEGIN
SELECT RAISE(ABORT, 'disallowed phase change for task');
END;


DROP TRIGGER IF EXISTS trg_tasks_touch_updated_at_on_phase;
CREATE TRIGGER trg_tasks_touch_updated_at_on_phase
AFTER UPDATE OF phase_id ON tasks
FOR EACH ROW
BEGIN
UPDATE tasks SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = NEW.id;
END;


DROP TRIGGER IF EXISTS trg_subtasks_phase_validate;
CREATE TRIGGER trg_subtasks_phase_validate
BEFORE UPDATE OF phase_id ON subtasks
FOR EACH ROW
WHEN NOT EXISTS (
SELECT 1 FROM phase_transitions pt
WHERE pt.from_phase_id = OLD.phase_id AND pt.to_phase_id = NEW.phase_id
)
BEGIN
SELECT RAISE(ABORT, 'disallowed phase change for subtask');
END;


DROP TRIGGER IF EXISTS trg_subtasks_touch_updated_at_on_phase;
CREATE TRIGGER trg_subtasks_touch_updated_at_on_phase
AFTER UPDATE OF phase_id ON subtasks
FOR EACH ROW
BEGIN
UPDATE subtasks SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = NEW.id;
END;


COMMIT;
