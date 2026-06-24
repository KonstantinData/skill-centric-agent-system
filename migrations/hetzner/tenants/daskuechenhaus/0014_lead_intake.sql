CREATE TABLE IF NOT EXISTS app.leads (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  lead_number TEXT,
  status TEXT NOT NULL DEFAULT 'new',
  source TEXT NOT NULL,
  source_channel TEXT NOT NULL DEFAULT 'unknown',
  salutation TEXT,
  title TEXT,
  first_name TEXT,
  last_name TEXT,
  company_name TEXT,
  display_name TEXT NOT NULL,
  primary_email TEXT,
  primary_phone TEXT,
  primary_phone_normalized TEXT,
  primary_mobile TEXT,
  primary_mobile_normalized TEXT,
  preferred_contact_channel TEXT NOT NULL DEFAULT 'phone',
  country TEXT NOT NULL DEFAULT 'DE',
  postal_code TEXT,
  city TEXT,
  project_summary TEXT,
  initial_message TEXT,
  notes TEXT,
  owner_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  converted_customer_id BIGINT REFERENCES app.customers (id) ON DELETE SET NULL,
  converted_at TIMESTAMPTZ,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT leads_lead_number_not_blank CHECK (
    lead_number IS NULL OR btrim(lead_number) <> ''
  ),
  CONSTRAINT leads_status CHECK (
    status IN (
      'new',
      'contacted',
      'waiting_for_customer',
      'appointment_scheduled',
      'converted',
      'not_reached',
      'not_interested',
      'not_qualified',
      'closed'
    )
  ),
  CONSTRAINT leads_source_not_blank CHECK (btrim(source) <> ''),
  CONSTRAINT leads_source_channel CHECK (
    source_channel IN (
      'website',
      'facebook',
      'instagram',
      'email',
      'phone',
      'whatsapp',
      'showroom',
      'referral',
      'partner',
      'other',
      'unknown'
    )
  ),
  CONSTRAINT leads_display_name_not_blank CHECK (btrim(display_name) <> ''),
  CONSTRAINT leads_email_lowercase CHECK (
    primary_email IS NULL OR primary_email = lower(primary_email)
  ),
  CONSTRAINT leads_preferred_contact_channel CHECK (
    preferred_contact_channel IN ('email', 'phone', 'mobile', 'whatsapp', 'post', 'none')
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS leads_lead_number_key
  ON app.leads (lead_number)
  WHERE lead_number IS NOT NULL;

CREATE INDEX IF NOT EXISTS leads_status_owner_idx
  ON app.leads (status, owner_user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS leads_display_name_search_idx
  ON app.leads (lower(display_name));

CREATE INDEX IF NOT EXISTS leads_contact_search_idx
  ON app.leads (
    lower(COALESCE(primary_email, '')),
    lower(COALESCE(primary_phone, '')),
    lower(COALESCE(primary_mobile, ''))
  );

CREATE TABLE IF NOT EXISTS app.lead_notes (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  lead_id BIGINT NOT NULL REFERENCES app.leads (id) ON DELETE CASCADE,
  note_type TEXT NOT NULL DEFAULT 'general',
  body TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'manual',
  created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT lead_notes_type CHECK (
    note_type IN (
      'general',
      'call',
      'email',
      'whatsapp',
      'social',
      'internal',
      'customer_request'
    )
  ),
  CONSTRAINT lead_notes_source CHECK (
    source IN ('manual', 'email_import', 'social_import', 'system_import', 'scas_agent')
  ),
  CONSTRAINT lead_notes_body_not_blank CHECK (btrim(body) <> '')
);

CREATE INDEX IF NOT EXISTS lead_notes_lead_idx
  ON app.lead_notes (lead_id, created_at DESC);

DO $$
DECLARE
  table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY['leads', 'lead_notes']
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS set_%I_updated_at ON app.%I', table_name, table_name);
    EXECUTE format(
      'CREATE TRIGGER set_%I_updated_at BEFORE UPDATE ON app.%I FOR EACH ROW EXECUTE FUNCTION app.set_updated_at()',
      table_name,
      table_name
    );
  END LOOP;
END;
$$;

INSERT INTO app.permissions (code, name, description)
VALUES
  ('leads.view', 'Leads ansehen', 'Leadakten und Lead-Kommunikation ansehen.'),
  ('leads.manage', 'Leads verwalten', 'Leads und Lead-Kommunikation anlegen und bearbeiten.')
ON CONFLICT (code) DO UPDATE
SET
  name = EXCLUDED.name,
  description = EXCLUDED.description;

INSERT INTO app.role_permissions (role_id, permission_id)
SELECT roles.id, permissions.id
FROM app.roles
JOIN app.permissions ON permissions.code IN ('leads.view', 'leads.manage')
WHERE roles.code IN ('admin', 'sales')
ON CONFLICT DO NOTHING;

INSERT INTO app.role_permissions (role_id, permission_id)
SELECT roles.id, permissions.id
FROM app.roles
JOIN app.permissions ON permissions.code = 'leads.view'
WHERE roles.code = 'employee'
ON CONFLICT DO NOTHING;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_daskuechenhaus_app') THEN
    GRANT USAGE ON SCHEMA app TO tenant_daskuechenhaus_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app
      TO tenant_daskuechenhaus_app;
    GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA app
      TO tenant_daskuechenhaus_app;
  END IF;
END;
$$;
