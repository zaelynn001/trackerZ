-- Rev 0.0.1

PRAGMA foreign_keys=ON;


BEGIN;


CREATE TABLE IF NOT EXISTS project_updates (
id INTEGER PRIMARY KEY,
project_id INTEGER NOT NULL,
old_phase_id INTEGER,
new_phase_id INTEGER,
note TEXT,
reason TEXT,
created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
FOREIGN KEY (old_phase_id) REFERENCES phases(id),
FOREIGN KEY (new_phase_id) REFERENCES phases(id)
);


COMMIT;
