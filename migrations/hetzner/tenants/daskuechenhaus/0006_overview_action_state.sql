ALTER TABLE app.tasks
  ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS archived_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS deleted_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS tasks_operational_visibility_idx
  ON app.tasks (archived_at, deleted_at, due_at);

ALTER TABLE app.email_messages
  ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS archived_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS deleted_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS email_messages_operational_visibility_idx
  ON app.email_messages (archived_at, deleted_at, received_at DESC);

INSERT INTO app.permissions (code, name, description)
VALUES
  (
    'overview.actions.manage',
    'Cockpit-Aktionen verwalten',
    'Aufgaben und E-Mails im Cockpit bearbeiten, archivieren und in den Papierkorb legen.'
  )
ON CONFLICT (code) DO UPDATE
SET
  name = EXCLUDED.name,
  description = EXCLUDED.description;

INSERT INTO app.role_permissions (role_id, permission_id)
SELECT roles.id, permissions.id
FROM app.roles
JOIN app.permissions ON permissions.code = 'overview.actions.manage'
WHERE roles.code IN ('admin', 'sales', 'employee')
ON CONFLICT DO NOTHING;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_daskuechenhaus_app') THEN
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app
      TO tenant_daskuechenhaus_app;
    GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA app
      TO tenant_daskuechenhaus_app;
  END IF;
END;
$$;
