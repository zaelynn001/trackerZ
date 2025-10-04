-- Create one project, one task, one subtask in 'Open' phase
INSERT INTO projects (project_number, title, description, phase_id, priority, created_at_utc, updated_at_utc)
VALUES ('P0001', 'Museum Network Upgrade', 'Backbone refresh and camera VLAN rework', 1, 'High',
        strftime('%Y-%m-%dT%H:%M:%SZ','now'), strftime('%Y-%m-%dT%H:%M:%SZ','now'));

INSERT INTO project_updates (project_id, occurred_at_utc, actor, reason, new_phase_id, note)
SELECT id, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 'system', 'Created', 1, 'Initial seed'
FROM projects WHERE project_number='P0001';

INSERT INTO tasks (task_number, project_id, title, description, phase_id, priority, created_at_utc, updated_at_utc)
SELECT 'T000001', id, 'Install core switch', 'Rack, power, uplinks', 1, 'High',
       strftime('%Y-%m-%dT%H:%M:%SZ','now'), strftime('%Y-%m-%dT%H:%M:%SZ','now')
FROM projects WHERE project_number='P0001';

INSERT INTO task_updates (task_id, occurred_at_utc, actor, reason, new_phase_id, note)
SELECT t.id, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 'system', 'Created', 1, 'Initial seed'
FROM tasks t WHERE t.task_number='T000001';

INSERT INTO subtasks (subtask_number, task_id, title, description, phase_id, priority, created_at_utc, updated_at_utc)
SELECT 'S000001', t.id, 'Mount and cable', 'Rails, patch, label', 1, 'Medium',
       strftime('%Y-%m-%dT%H:%M:%SZ','now'), strftime('%Y-%m-%dT%H:%M:%SZ','now')
FROM tasks t WHERE t.task_number='T000001';

INSERT INTO subtask_updates (subtask_id, occurred_at_utc, actor, reason, new_phase_id, note)
SELECT s.id, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 'system', 'Created', 1, 'Initial seed'
FROM subtasks s WHERE s.subtask_number='S000001';

