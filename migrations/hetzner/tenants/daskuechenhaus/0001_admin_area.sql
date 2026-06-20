CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS app.users (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT,
  job_title TEXT,
  department TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  is_admin BOOLEAN NOT NULL DEFAULT FALSE,
  timezone TEXT NOT NULL DEFAULT 'Europe/Berlin',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT users_email_not_blank CHECK (btrim(email) <> ''),
  CONSTRAINT users_email_has_at CHECK (position('@' IN email) > 1),
  CONSTRAINT users_email_lowercase CHECK (email = lower(email)),
  CONSTRAINT users_timezone_not_blank CHECK (btrim(timezone) <> ''),
  CONSTRAINT users_name_not_blank CHECK (
    btrim(first_name) <> '' AND btrim(last_name) <> ''
  )
);

DROP INDEX IF EXISTS app.users_email_key;
CREATE INDEX IF NOT EXISTS users_email_idx ON app.users (email);

CREATE TABLE IF NOT EXISTS app.roles (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  is_system_role BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT roles_code_not_blank CHECK (btrim(code) <> ''),
  CONSTRAINT roles_name_not_blank CHECK (btrim(name) <> ''),
  CONSTRAINT roles_code_format CHECK (code ~ '^[a-z][a-z0-9_]*$')
);

CREATE UNIQUE INDEX IF NOT EXISTS roles_code_key ON app.roles (code);

CREATE TABLE IF NOT EXISTS app.permissions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT permissions_code_not_blank CHECK (btrim(code) <> ''),
  CONSTRAINT permissions_name_not_blank CHECK (btrim(name) <> ''),
  CONSTRAINT permissions_code_format CHECK (code ~ '^[a-z][a-z0-9_.]*$')
);

CREATE UNIQUE INDEX IF NOT EXISTS permissions_code_key ON app.permissions (code);

CREATE TABLE IF NOT EXISTS app.role_permissions (
  role_id BIGINT NOT NULL REFERENCES app.roles (id) ON DELETE CASCADE,
  permission_id BIGINT NOT NULL REFERENCES app.permissions (id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS app.user_roles (
  user_id BIGINT NOT NULL REFERENCES app.users (id) ON DELETE CASCADE,
  role_id BIGINT NOT NULL REFERENCES app.roles (id) ON DELETE RESTRICT,
  assigned_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS app.user_preferences (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES app.users (id) ON DELETE CASCADE,
  timezone TEXT NOT NULL DEFAULT 'Europe/Berlin',
  date_format TEXT NOT NULL DEFAULT 'DD.MM.YYYY',
  time_format TEXT NOT NULL DEFAULT '24h',
  dashboard_default_route TEXT NOT NULL DEFAULT '/admin.php',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT user_preferences_user_key UNIQUE (user_id),
  CONSTRAINT user_preferences_timezone_not_blank CHECK (btrim(timezone) <> ''),
  CONSTRAINT user_preferences_date_format_not_blank CHECK (btrim(date_format) <> ''),
  CONSTRAINT user_preferences_time_format CHECK (time_format = '24h'),
  CONSTRAINT user_preferences_dashboard_route CHECK (
    dashboard_default_route ~ '^/[a-z0-9_./-]*$'
  )
);

CREATE TABLE IF NOT EXISTS app.user_workdays (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES app.users (id) ON DELETE CASCADE,
  weekday SMALLINT NOT NULL,
  is_working_day BOOLEAN NOT NULL DEFAULT FALSE,
  morning_start_time TIME,
  morning_end_time TIME,
  afternoon_start_time TIME,
  afternoon_end_time TIME,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT user_workdays_user_weekday_key UNIQUE (user_id, weekday),
  CONSTRAINT user_workdays_weekday_range CHECK (weekday BETWEEN 1 AND 6),
  CONSTRAINT user_workdays_morning_pair CHECK (
    (morning_start_time IS NULL AND morning_end_time IS NULL)
    OR (morning_start_time IS NOT NULL AND morning_end_time IS NOT NULL)
  ),
  CONSTRAINT user_workdays_afternoon_pair CHECK (
    (afternoon_start_time IS NULL AND afternoon_end_time IS NULL)
    OR (afternoon_start_time IS NOT NULL AND afternoon_end_time IS NOT NULL)
  ),
  CONSTRAINT user_workdays_morning_order CHECK (
    morning_start_time IS NULL OR morning_end_time > morning_start_time
  ),
  CONSTRAINT user_workdays_afternoon_order CHECK (
    afternoon_start_time IS NULL OR afternoon_end_time > afternoon_start_time
  ),
  CONSTRAINT user_workdays_window_order CHECK (
    morning_end_time IS NULL
    OR afternoon_start_time IS NULL
    OR afternoon_start_time > morning_end_time
  ),
  CONSTRAINT user_workdays_working_day_has_time CHECK (
    (
      is_working_day
      AND (morning_start_time IS NOT NULL OR afternoon_start_time IS NOT NULL)
    )
    OR (
      NOT is_working_day
      AND morning_start_time IS NULL
      AND morning_end_time IS NULL
      AND afternoon_start_time IS NULL
      AND afternoon_end_time IS NULL
    )
  )
);

CREATE TABLE IF NOT EXISTS app.user_notification_settings (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES app.users (id) ON DELETE CASCADE,
  email_notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  notify_tasks_due BOOLEAN NOT NULL DEFAULT TRUE,
  notify_status_changes BOOLEAN NOT NULL DEFAULT TRUE,
  notify_new_assignments BOOLEAN NOT NULL DEFAULT TRUE,
  notify_comments BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT user_notification_settings_user_key UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS app.user_security_settings (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES app.users (id) ON DELETE CASCADE,
  external_identity_provider TEXT NOT NULL DEFAULT 'cloudflare_access',
  external_subject TEXT,
  last_login_at TIMESTAMPTZ,
  password_login_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  mfa_required BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT user_security_settings_user_key UNIQUE (user_id),
  CONSTRAINT user_security_settings_provider_not_blank CHECK (
    btrim(external_identity_provider) <> ''
  ),
  CONSTRAINT user_security_settings_password_disabled CHECK (
    password_login_enabled = FALSE
  )
);

CREATE TABLE IF NOT EXISTS app.company_settings (
  id SMALLINT PRIMARY KEY DEFAULT 1,
  company_name TEXT NOT NULL,
  legal_name TEXT NOT NULL,
  street TEXT,
  postal_code TEXT,
  city TEXT,
  country TEXT NOT NULL DEFAULT 'DE',
  phone TEXT,
  fax TEXT,
  email TEXT,
  website TEXT,
  vat_id TEXT,
  commercial_register TEXT,
  managing_director TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT company_settings_singleton CHECK (id = 1),
  CONSTRAINT company_settings_company_name_not_blank CHECK (btrim(company_name) <> ''),
  CONSTRAINT company_settings_legal_name_not_blank CHECK (btrim(legal_name) <> '')
);

CREATE TABLE IF NOT EXISTS app.admin_settings (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  setting_key TEXT NOT NULL,
  setting_value_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  description TEXT,
  updated_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT admin_settings_key_not_blank CHECK (btrim(setting_key) <> ''),
  CONSTRAINT admin_settings_key_format CHECK (setting_key ~ '^[a-z][a-z0-9_.]*$')
);

CREATE UNIQUE INDEX IF NOT EXISTS admin_settings_setting_key_key
  ON app.admin_settings (setting_key);

CREATE TABLE IF NOT EXISTS app.integrations (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT integrations_code_not_blank CHECK (btrim(code) <> ''),
  CONSTRAINT integrations_name_not_blank CHECK (btrim(name) <> ''),
  CONSTRAINT integrations_code_format CHECK (code ~ '^[a-z][a-z0-9_]*$')
);

CREATE UNIQUE INDEX IF NOT EXISTS integrations_code_key ON app.integrations (code);

CREATE TABLE IF NOT EXISTS app.integration_connections (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  integration_id BIGINT NOT NULL REFERENCES app.integrations (id) ON DELETE CASCADE,
  display_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  secret_reference TEXT,
  last_checked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT integration_connections_display_name_not_blank CHECK (
    btrim(display_name) <> ''
  ),
  CONSTRAINT integration_connections_status CHECK (
    status IN ('pending', 'configured', 'disabled', 'error')
  )
);

CREATE TABLE IF NOT EXISTS audit.change_log (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  actor_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  entity_schema TEXT NOT NULL,
  entity_table TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  old_value_json JSONB,
  new_value_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT change_log_entity_schema_not_blank CHECK (btrim(entity_schema) <> ''),
  CONSTRAINT change_log_entity_table_not_blank CHECK (btrim(entity_table) <> ''),
  CONSTRAINT change_log_entity_id_not_blank CHECK (btrim(entity_id) <> ''),
  CONSTRAINT change_log_action CHECK (
    action IN ('insert', 'update', 'delete', 'login', 'configure')
  )
);

CREATE INDEX IF NOT EXISTS change_log_entity_idx
  ON audit.change_log (entity_schema, entity_table, entity_id, created_at DESC);

CREATE INDEX IF NOT EXISTS change_log_actor_idx
  ON audit.change_log (actor_user_id, created_at DESC);

CREATE OR REPLACE FUNCTION app.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS set_users_updated_at ON app.users;
CREATE TRIGGER set_users_updated_at
BEFORE UPDATE ON app.users
FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

DROP TRIGGER IF EXISTS set_roles_updated_at ON app.roles;
CREATE TRIGGER set_roles_updated_at
BEFORE UPDATE ON app.roles
FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

DROP TRIGGER IF EXISTS set_permissions_updated_at ON app.permissions;
CREATE TRIGGER set_permissions_updated_at
BEFORE UPDATE ON app.permissions
FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

DROP TRIGGER IF EXISTS set_user_preferences_updated_at ON app.user_preferences;
CREATE TRIGGER set_user_preferences_updated_at
BEFORE UPDATE ON app.user_preferences
FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

DROP TRIGGER IF EXISTS set_user_workdays_updated_at ON app.user_workdays;
CREATE TRIGGER set_user_workdays_updated_at
BEFORE UPDATE ON app.user_workdays
FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

DROP TRIGGER IF EXISTS set_user_notification_settings_updated_at
  ON app.user_notification_settings;
CREATE TRIGGER set_user_notification_settings_updated_at
BEFORE UPDATE ON app.user_notification_settings
FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

DROP TRIGGER IF EXISTS set_user_security_settings_updated_at
  ON app.user_security_settings;
CREATE TRIGGER set_user_security_settings_updated_at
BEFORE UPDATE ON app.user_security_settings
FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

DROP TRIGGER IF EXISTS set_company_settings_updated_at ON app.company_settings;
CREATE TRIGGER set_company_settings_updated_at
BEFORE UPDATE ON app.company_settings
FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

DROP TRIGGER IF EXISTS set_admin_settings_updated_at ON app.admin_settings;
CREATE TRIGGER set_admin_settings_updated_at
BEFORE UPDATE ON app.admin_settings
FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

DROP TRIGGER IF EXISTS set_integrations_updated_at ON app.integrations;
CREATE TRIGGER set_integrations_updated_at
BEFORE UPDATE ON app.integrations
FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

DROP TRIGGER IF EXISTS set_integration_connections_updated_at
  ON app.integration_connections;
CREATE TRIGGER set_integration_connections_updated_at
BEFORE UPDATE ON app.integration_connections
FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

INSERT INTO app.roles (code, name, description, is_system_role)
VALUES
  ('admin', 'Admin', 'Voller Zugriff auf den Admin-Bereich.', TRUE),
  ('employee', 'Mitarbeiter', 'Standardrolle fuer registrierte Mitarbeiter.', TRUE),
  ('sales', 'Verkauf', 'Rolle fuer Mitarbeiter im Verkauf.', TRUE)
ON CONFLICT (code) DO UPDATE
SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  is_system_role = EXCLUDED.is_system_role;

INSERT INTO app.permissions (code, name, description)
VALUES
  ('admin.view', 'Admin-Bereich ansehen', 'Erlaubt den Zugriff auf admin.php.'),
  ('admin.users.manage', 'Benutzer verwalten', 'Benutzer anlegen und bearbeiten.'),
  ('admin.roles.manage', 'Rollen verwalten', 'Rollen und Rechte verwalten.'),
  ('admin.settings.manage', 'Einstellungen verwalten', 'Firmen- und Systemeinstellungen bearbeiten.'),
  ('admin.integrations.manage', 'Integrationen verwalten', 'Externe Anbindungen konfigurieren.')
ON CONFLICT (code) DO UPDATE
SET
  name = EXCLUDED.name,
  description = EXCLUDED.description;

INSERT INTO app.role_permissions (role_id, permission_id)
SELECT roles.id, permissions.id
FROM app.roles
CROSS JOIN app.permissions
WHERE roles.code = 'admin'
ON CONFLICT DO NOTHING;

WITH upserted_user AS (
  INSERT INTO app.users (
    first_name,
    last_name,
    email,
    job_title,
    department,
    is_active,
    is_admin,
    timezone
  )
  SELECT
    'Konstantin',
    'Milonas',
    'k.milonas@schober-daskuechenhaus.de',
    'Admin',
    'Administration',
    TRUE,
    TRUE,
    'Europe/Berlin'
  WHERE NOT EXISTS (
    SELECT 1
    FROM app.users
    WHERE email = 'k.milonas@schober-daskuechenhaus.de'
      AND is_admin = TRUE
  )
  RETURNING id
),
existing_user AS (
  SELECT id
  FROM app.users
  WHERE email = 'k.milonas@schober-daskuechenhaus.de'
    AND is_admin = TRUE
  ORDER BY id
  LIMIT 1
),
target_user AS (
  SELECT id FROM upserted_user
  UNION ALL
  SELECT id FROM existing_user
  LIMIT 1
),
admin_role AS (
  SELECT id FROM app.roles WHERE code = 'admin'
)
INSERT INTO app.user_roles (user_id, role_id)
SELECT target_user.id, admin_role.id
FROM target_user
CROSS JOIN admin_role
ON CONFLICT DO NOTHING;

INSERT INTO app.user_preferences (user_id, timezone)
SELECT id, timezone
FROM app.users
WHERE email = 'k.milonas@schober-daskuechenhaus.de'
ON CONFLICT (user_id) DO UPDATE
SET timezone = EXCLUDED.timezone;

INSERT INTO app.user_security_settings (
  user_id,
  external_identity_provider,
  password_login_enabled,
  mfa_required
)
SELECT id, 'cloudflare_access', FALSE, TRUE
FROM app.users
WHERE email = 'k.milonas@schober-daskuechenhaus.de'
ON CONFLICT (user_id) DO UPDATE
SET
  external_identity_provider = EXCLUDED.external_identity_provider,
  password_login_enabled = FALSE,
  mfa_required = EXCLUDED.mfa_required;

INSERT INTO app.company_settings (
  id,
  company_name,
  legal_name,
  street,
  postal_code,
  city,
  country,
  phone,
  fax,
  email,
  website,
  vat_id,
  commercial_register,
  managing_director
)
VALUES (
  1,
  'das kuechenhaus',
  'das kuechenhaus ralph schober GmbH',
  'Blumenstrasse 17',
  '73728',
  'Esslingen',
  'DE',
  '0711/36550747',
  '0711/36550746',
  'info@schober-daskuechenhaus.de',
  'https://www.schober-daskuechenhaus.de',
  'DE265715198',
  'Amtsgericht Stuttgart, HR 730338',
  'Ralph Schober'
)
ON CONFLICT (id) DO UPDATE
SET
  company_name = EXCLUDED.company_name,
  legal_name = EXCLUDED.legal_name,
  street = EXCLUDED.street,
  postal_code = EXCLUDED.postal_code,
  city = EXCLUDED.city,
  country = EXCLUDED.country,
  phone = EXCLUDED.phone,
  fax = EXCLUDED.fax,
  email = EXCLUDED.email,
  website = EXCLUDED.website,
  vat_id = EXCLUDED.vat_id,
  commercial_register = EXCLUDED.commercial_register,
  managing_director = EXCLUDED.managing_director;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_daskuechenhaus_app') THEN
    GRANT USAGE ON SCHEMA app TO tenant_daskuechenhaus_app;
    GRANT USAGE ON SCHEMA audit TO tenant_daskuechenhaus_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app
      TO tenant_daskuechenhaus_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA audit
      TO tenant_daskuechenhaus_app;
    GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA app
      TO tenant_daskuechenhaus_app;
    GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA audit
      TO tenant_daskuechenhaus_app;
  END IF;
END;
$$;
