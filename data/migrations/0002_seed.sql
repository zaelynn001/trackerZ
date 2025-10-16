-- 0002_seed.sql — Rev 1.1.0-seed
-- trackerZ development dataset for fresh installs
-- Assumes 0001_init.sql (Rev 1.1.0) has been applied.

PRAGMA foreign_keys = ON;
BEGIN;

-------------------------------------------------------
-- PROJECTS
-------------------------------------------------------
INSERT INTO projects (id, name, description, phase_id, priority_id, created_at_utc, updated_at_utc)
VALUES
  (1,
   'trackerZ Sample Project',
   'Demo project to verify the app shell, phase/priority flows, and timelines.',
   2,   -- In Progress
   2,   -- Medium
   strftime('%Y-%m-%dT%H:%M:%SZ','now','-7 day'),
   strftime('%Y-%m-%dT%H:%M:%SZ','now','-7 day')
  );

-------------------------------------------------------
-- TASKS
-------------------------------------------------------
INSERT INTO tasks (id, project_id, name, description, phase_id, priority_id, created_at_utc, updated_at_utc)
VALUES
  (1, 1, 'Bootstrap Environment',
      'Initialize logging, schema, and base UI shell.',
      5, 2,
      strftime('%Y-%m-%dT%H:%M:%SZ','now','-6 day'),
      strftime('%Y-%m-%dT%H:%M:%SZ','now','-5 day')),
  (2, 1, 'Implement Task CRUD',
      'Build task creation, editing, and timeline logging.',
      2, 3,
      strftime('%Y-%m-%dT%H:%M:%SZ','now','-4 day'),
      strftime('%Y-%m-%dT%H:%M:%SZ','now','-2 day'));

-------------------------------------------------------
-- SUBTASKS
-------------------------------------------------------
INSERT INTO subtasks (id, task_id, name, description, phase_id, priority_id, created_at_utc, updated_at_utc)
VALUES
  (1, 1, 'Set up data directories',
      'Ensure ~/.local/state/trackerZ exists.',
      5, 2,
      strftime('%Y-%m-%dT%H:%M:%SZ','now','-6 day'),
      strftime('%Y-%m-%dT%H:%M:%SZ','now','-5 day')),
  (2, 2, 'Implement SQLiteTaskRepository',
      'Provide list/filter/count queries.',
      2, 3,
      strftime('%Y-%m-%dT%H:%M:%SZ','now','-3 day'),
      strftime('%Y-%m-%dT%H:%M:%SZ','now','-2 day')),
  (3, 2, 'Wire UI to ViewModel',
      'Connect signals between view and repo.',
      1, 2,
      strftime('%Y-%m-%dT%H:%M:%SZ','now','-1 day'),
      strftime('%Y-%m-%dT%H:%M:%SZ','now','-1 day'));

-------------------------------------------------------
-- PROJECT UPDATES (explicit reasons to satisfy NOT NULL)
-------------------------------------------------------
-- Phase: Open→In Progress, Priority: Medium→Medium (no change)
INSERT INTO project_updates (project_id, old_phase_id, new_phase_id,
                             old_priority_id, new_priority_id,
                             note, reason, updated_at_utc)
VALUES
  (1, 1, 2, 2, 2,
   'Project initialized and work started.',
   'phase_change',
   strftime('%Y-%m-%dT%H:%M:%SZ','now','-7 day'));

-------------------------------------------------------
-- TASK UPDATES
-------------------------------------------------------
INSERT INTO task_updates (task_id, old_phase_id, new_phase_id,
                          old_priority_id, new_priority_id,
                          note, reason, updated_at_utc)
VALUES
  (1, 1, 5, 2, 2,
   'Bootstrap completed successfully.',
   'phase_change',
   strftime('%Y-%m-%dT%H:%M:%SZ','now','-5 day')),

  -- Task 2 created (Open) then moved to In Progress; priority bumped Medium→High
  (2, 1, 1, 2, 2,
   'CRUD task created.',
   'create',
   strftime('%Y-%m-%dT%H:%M:%SZ','now','-4 day')),
  (2, 1, 2, 2, 3,
   'Development in progress; raising urgency.',
   'phase_change',
   strftime('%Y-%m-%dT%H:%M:%SZ','now','-2 day'));

-------------------------------------------------------
-- SUBTASK UPDATES
-------------------------------------------------------
INSERT INTO subtask_updates (subtask_id, old_phase_id, new_phase_id,
                             old_priority_id, new_priority_id,
                             note, reason, updated_at_utc)
VALUES
  (1, 1, 5, 2, 2,
   'Directory structure created and verified.',
   'phase_change',
   strftime('%Y-%m-%dT%H:%M:%SZ','now','-5 day')),
  (2, 1, 2, 3, 3,
   'Repo methods drafted; continuing.',
   'phase_change',
   strftime('%Y-%m-%dT%H:%M:%SZ','now','-2 day')),
  (3, 1, 1, 2, 2,
   'Pending UI event wiring.',
   'note',
   strftime('%Y-%m-%dT%H:%M:%SZ','now','-1 day'));

-------------------------------------------------------
-- ATTACHMENTS (note may be NULL)
-------------------------------------------------------
INSERT INTO attachments (project_id, task_id, subtask_id, rel_path, label, note, created_at_utc)
VALUES
  (1, NULL, NULL, 'docs/schema_diagram.png', 'Schema Diagram', NULL,
   strftime('%Y-%m-%dT%H:%M:%SZ','now','-6 day')),
  (1, NULL, NULL, 'docs/roadmap.md', 'Project Roadmap', 'Initial milestone outline',
   strftime('%Y-%m-%dT%H:%M:%SZ','now','-6 day'));

-------------------------------------------------------
-- EXPENSES (exact column order; only note is nullable)
-- Columns: id, project_id, item, supplier, type, amount, purchaser, created_at_utc, order_id, note
-------------------------------------------------------
INSERT INTO expenses (id, project_id, item, supplier, type, amount, purchaser, created_at_utc, order_id, note)
VALUES
  (1, 1, 'Prototype hardware', 'Linux Depot', 'Development', 129.90, 'Dean',
   strftime('%Y-%m-%dT%H:%M:%SZ','now','-3 day'), 'PO-0001', 'USB C dock for testing'),
  (2, 1, 'PySide6 wheels check', 'PyPI', 'Tooling', 2.99, 'Dean',
   strftime('%Y-%m-%dT%H:%M:%SZ','now','-6 day'), 'PO-0000', NULL);

-------------------------------------------------------
-- SETTINGS
-------------------------------------------------------
INSERT INTO settings (key, value) VALUES
  ('ui.diagnostics_visible', 'true'),
  ('ui.splitter_positions',  'main:0.6,diag:0.4'),
  ('repo.data_dir',          'trackerZ/data');

COMMIT;
