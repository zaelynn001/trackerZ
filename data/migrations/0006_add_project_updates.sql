-- Rev 0.5.0


CREATE INDEX IF NOT EXISTS ix_project_updates_proj_updated_at_utc ON project_updates(project_id, updated_at_utc DESC);
