PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────
-- Phases & allowed phase changes
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS phases (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,
  is_terminal INTEGER NOT NULL DEFAULT 0,
  sort_order  INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_phases_name ON phases(name);
CREATE INDEX IF NOT EXISTS idx_phases_sort ON phases(sort_order);

CREATE TABLE IF NOT EXISTS phase_transitions (
  from_phase_id INTEGER NOT NULL,
  to_phase_id   INTEGER NOT NULL,
  PRIMARY KEY (from_phase_id, to_phase_id),
  FOREIGN KEY (from_phase_id) REFERENCES phases(id) ON DELETE CASCADE,
  FOREIGN KEY (to_phase_id)   REFERENCES phases(id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────────────────────
-- Projects
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
  id              INTEGER PRIMARY KEY,
  project_number  TEXT NOT NULL UNIQUE,   -- e.g., P0001
  title           TEXT NOT NULL,
  description     TEXT,
  phase_id        INTEGER NOT NULL,
  priority        TEXT,                   -- Low/Medium/High/Urgent (free text for now)
  created_at_utc  TEXT NOT NULL,          -- ISO8601 UTC
  updated_at_utc  TEXT NOT NULL,
  FOREIGN KEY (phase_id) REFERENCES phases(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_projects_phase   ON projects(phase_id);
CREATE INDEX IF NOT EXISTS idx_projects_updated ON projects(updated_at_utc);

CREATE TABLE IF NOT EXISTS project_updates (
  id               INTEGER PRIMARY KEY,
  project_id       INTEGER NOT NULL,
  occurred_at_utc  TEXT NOT NULL,
  actor            TEXT,
  reason           TEXT NOT NULL,         -- Created | Phase Change | Edited | Note
  old_phase_id     INTEGER,
  new_phase_id     INTEGER,
  note             TEXT,
  FOREIGN KEY (project_id)  REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (old_phase_id) REFERENCES phases(id),
  FOREIGN KEY (new_phase_id) REFERENCES phases(id)
);

CREATE INDEX IF NOT EXISTS idx_project_updates ON project_updates(project_id, occurred_at_utc DESC);

-- ─────────────────────────────────────────────────────────────
-- Tasks (child of Project)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
  id              INTEGER PRIMARY KEY,
  task_number     TEXT NOT NULL UNIQUE,   -- e.g., T000001
  project_id      INTEGER NOT NULL,
  title           TEXT NOT NULL,
  description     TEXT,
  phase_id        INTEGER NOT NULL,
  priority        TEXT,
  created_at_utc  TEXT NOT NULL,
  updated_at_utc  TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (phase_id)   REFERENCES phases(id)   ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_phase   ON tasks(phase_id);
CREATE INDEX IF NOT EXISTS idx_tasks_updated ON tasks(updated_at_utc);

CREATE TABLE IF NOT EXISTS task_updates (
  id               INTEGER PRIMARY KEY,
  task_id          INTEGER NOT NULL,
  occurred_at_utc  TEXT NOT NULL,
  actor            TEXT,
  reason           TEXT NOT NULL,
  old_phase_id     INTEGER,
  new_phase_id     INTEGER,
  note             TEXT,
  FOREIGN KEY (task_id)     REFERENCES tasks(id) ON DELETE CASCADE,
  FOREIGN KEY (old_phase_id) REFERENCES phases(id),
  FOREIGN KEY (new_phase_id) REFERENCES phases(id)
);

CREATE INDEX IF NOT EXISTS idx_task_updates ON task_updates(task_id, occurred_at_utc DESC);

-- ─────────────────────────────────────────────────────────────
-- Subtasks (child of Task)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subtasks (
  id              INTEGER PRIMARY KEY,
  subtask_number  TEXT NOT NULL UNIQUE,   -- e.g., S000001
  task_id         INTEGER NOT NULL,
  title           TEXT NOT NULL,
  description     TEXT,
  phase_id        INTEGER NOT NULL,
  priority        TEXT,
  created_at_utc  TEXT NOT NULL,
  updated_at_utc  TEXT NOT NULL,
  FOREIGN KEY (task_id)  REFERENCES tasks(id)  ON DELETE CASCADE,
  FOREIGN KEY (phase_id) REFERENCES phases(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_subtasks_task   ON subtasks(task_id);
CREATE INDEX IF NOT EXISTS idx_subtasks_phase  ON subtasks(phase_id);
CREATE INDEX IF NOT EXISTS idx_subtasks_updated ON subtasks(updated_at_utc);

CREATE TABLE IF NOT EXISTS subtask_updates (
  id               INTEGER PRIMARY KEY,
  subtask_id       INTEGER NOT NULL,
  occurred_at_utc  TEXT NOT NULL,
  actor            TEXT,
  reason           TEXT NOT NULL,
  old_phase_id     INTEGER,
  new_phase_id     INTEGER,
  note             TEXT,
  FOREIGN KEY (subtask_id)  REFERENCES subtasks(id) ON DELETE CASCADE,
  FOREIGN KEY (old_phase_id) REFERENCES phases(id),
  FOREIGN KEY (new_phase_id) REFERENCES phases(id)
);

CREATE INDEX IF NOT EXISTS idx_subtask_updates ON subtask_updates(subtask_id, occurred_at_utc DESC);

-- ─────────────────────────────────────────────────────────────
-- Seeds
-- ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO phases (id, name, is_terminal, sort_order) VALUES
  (1, 'Open',        0, 10),
  (2, 'In Progress', 0, 20),
  (3, 'In Hiatus',   0, 30),
  (4, 'Resolved',    0, 40),
  (5, 'Closed',      1, 50);

INSERT OR IGNORE INTO phase_transitions (from_phase_id, to_phase_id) VALUES
  (1, 2),           -- Open → In Progress
  (2, 3), (2, 4),   -- In Progress → In Hiatus | Resolved
  (3, 2),           -- In Hiatus → In Progress
  (4, 5);           -- Resolved → Closed

-- Helpful flat views for UI tables
CREATE VIEW IF NOT EXISTS v_tasks_flat AS
SELECT
  t.id,
  t.task_number,
  t.project_id,
  p.project_number,
  t.title,
  t.description,
  ph.name AS phase,
  t.priority,
  t.created_at_utc,
  t.updated_at_utc
FROM tasks t
JOIN projects p ON p.id = t.project_id
JOIN phases ph  ON ph.id = t.phase_id;

CREATE VIEW IF NOT EXISTS v_subtasks_flat AS
SELECT
  s.id,
  s.subtask_number,
  s.task_id,
  t.task_number,
  t.project_id,
  p.project_number,
  s.title,
  s.description,
  ph.name AS phase,
  s.priority,
  s.created_at_utc,
  s.updated_at_utc
FROM subtasks s
JOIN tasks t   ON t.id = s.task_id
JOIN projects p ON p.id = t.project_id
JOIN phases ph  ON ph.id = s.phase_id;

