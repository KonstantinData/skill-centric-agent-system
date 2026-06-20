CREATE TABLE IF NOT EXISTS app.customers (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_number TEXT,
  customer_type TEXT NOT NULL DEFAULT 'private',
  salutation TEXT,
  title TEXT,
  first_name TEXT,
  last_name TEXT,
  company_name TEXT,
  company_name_2 TEXT,
  company_name_3 TEXT,
  company_name_4 TEXT,
  vat_id TEXT,
  tax_number TEXT,
  display_name TEXT NOT NULL,
  primary_email TEXT,
  primary_phone TEXT,
  primary_mobile TEXT,
  preferred_contact_channel TEXT NOT NULL DEFAULT 'email',
  country TEXT NOT NULL DEFAULT 'DE',
  iso_country_code TEXT NOT NULL DEFAULT 'DE',
  is_nato BOOLEAN NOT NULL DEFAULT FALSE,
  has_custom_vat BOOLEAN NOT NULL DEFAULT FALSE,
  custom_vat_rate NUMERIC(5, 2),
  custom_vat_rate_label TEXT,
  reverse_charge BOOLEAN NOT NULL DEFAULT FALSE,
  marketing_allowed BOOLEAN NOT NULL DEFAULT FALSE,
  e_invoice BOOLEAN NOT NULL DEFAULT FALSE,
  source TEXT,
  tags TEXT[] NOT NULL DEFAULT '{}'::text[],
  notes TEXT,
  owner_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customers_customer_number_not_blank CHECK (
    customer_number IS NULL OR btrim(customer_number) <> ''
  ),
  CONSTRAINT customers_type CHECK (customer_type IN ('private', 'company')),
  CONSTRAINT customers_display_name_not_blank CHECK (btrim(display_name) <> ''),
  CONSTRAINT customers_private_or_company_name CHECK (
    (
      customer_type = 'private'
      AND (
        NULLIF(btrim(COALESCE(first_name, '')), '') IS NOT NULL
        OR NULLIF(btrim(COALESCE(last_name, '')), '') IS NOT NULL
        OR NULLIF(btrim(display_name), '') IS NOT NULL
      )
    )
    OR (
      customer_type = 'company'
      AND (
        NULLIF(btrim(COALESCE(company_name, '')), '') IS NOT NULL
        OR NULLIF(btrim(display_name), '') IS NOT NULL
      )
    )
  ),
  CONSTRAINT customers_email_lowercase CHECK (
    primary_email IS NULL OR primary_email = lower(primary_email)
  ),
  CONSTRAINT customers_preferred_contact_channel CHECK (
    preferred_contact_channel IN ('email', 'phone', 'mobile', 'post', 'none')
  ),
  CONSTRAINT customers_iso_country_code_not_blank CHECK (btrim(iso_country_code) <> ''),
  CONSTRAINT customers_custom_vat_rate_positive CHECK (
    custom_vat_rate IS NULL OR custom_vat_rate >= 0
  ),
  CONSTRAINT customers_custom_vat_requires_rate CHECK (
    NOT has_custom_vat OR custom_vat_rate IS NOT NULL
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS customers_customer_number_key
  ON app.customers (customer_number)
  WHERE customer_number IS NOT NULL;

CREATE INDEX IF NOT EXISTS customers_display_name_search_idx
  ON app.customers (lower(display_name));

CREATE INDEX IF NOT EXISTS customers_contact_search_idx
  ON app.customers (
    lower(COALESCE(primary_email, '')),
    lower(COALESCE(primary_phone, '')),
    lower(COALESCE(primary_mobile, ''))
  );

CREATE INDEX IF NOT EXISTS customers_owner_active_idx
  ON app.customers (owner_user_id, is_active);

CREATE TABLE IF NOT EXISTS app.customer_addresses (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_id BIGINT NOT NULL REFERENCES app.customers (id) ON DELETE CASCADE,
  address_type TEXT NOT NULL DEFAULT 'billing',
  recipient_name TEXT,
  street TEXT NOT NULL,
  house_number TEXT,
  address_extra TEXT,
  postal_code TEXT NOT NULL,
  city TEXT NOT NULL,
  country TEXT NOT NULL DEFAULT 'DE',
  iso_country_code TEXT NOT NULL DEFAULT 'DE',
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customer_addresses_type CHECK (
    address_type IN ('billing', 'delivery', 'installation', 'other')
  ),
  CONSTRAINT customer_addresses_street_not_blank CHECK (btrim(street) <> ''),
  CONSTRAINT customer_addresses_postal_code_not_blank CHECK (btrim(postal_code) <> ''),
  CONSTRAINT customer_addresses_city_not_blank CHECK (btrim(city) <> ''),
  CONSTRAINT customer_addresses_iso_country_code_not_blank CHECK (
    btrim(iso_country_code) <> ''
  )
);

CREATE INDEX IF NOT EXISTS customer_addresses_customer_idx
  ON app.customer_addresses (customer_id, address_type);

CREATE UNIQUE INDEX IF NOT EXISTS customer_addresses_primary_type_key
  ON app.customer_addresses (customer_id, address_type)
  WHERE is_primary;

CREATE TABLE IF NOT EXISTS app.customer_contacts (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_id BIGINT NOT NULL REFERENCES app.customers (id) ON DELETE CASCADE,
  contact_type TEXT NOT NULL DEFAULT 'other',
  salutation TEXT,
  title TEXT,
  first_name TEXT,
  last_name TEXT,
  display_name TEXT NOT NULL,
  role_title TEXT,
  email TEXT,
  phone TEXT,
  mobile TEXT,
  notes TEXT,
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customer_contacts_type CHECK (
    contact_type IN (
      'primary',
      'partner',
      'decision_maker',
      'invoice',
      'delivery',
      'installation',
      'other'
    )
  ),
  CONSTRAINT customer_contacts_display_name_not_blank CHECK (btrim(display_name) <> ''),
  CONSTRAINT customer_contacts_email_lowercase CHECK (email IS NULL OR email = lower(email))
);

CREATE INDEX IF NOT EXISTS customer_contacts_customer_idx
  ON app.customer_contacts (customer_id, contact_type);

CREATE INDEX IF NOT EXISTS customer_contacts_search_idx
  ON app.customer_contacts (
    lower(display_name),
    lower(COALESCE(email, ''))
  );

CREATE UNIQUE INDEX IF NOT EXISTS customer_contacts_primary_type_key
  ON app.customer_contacts (customer_id, contact_type)
  WHERE is_primary;

CREATE TABLE IF NOT EXISTS app.customer_case_status_phases (
  phase SMALLINT PRIMARY KEY,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  is_terminal BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customer_case_status_phases_range CHECK (phase BETWEEN 1 AND 10),
  CONSTRAINT customer_case_status_phases_code_not_blank CHECK (btrim(code) <> ''),
  CONSTRAINT customer_case_status_phases_name_not_blank CHECK (btrim(name) <> ''),
  CONSTRAINT customer_case_status_phases_category_not_blank CHECK (btrim(category) <> ''),
  CONSTRAINT customer_case_status_phases_code_format CHECK (code ~ '^[a-z][a-z0-9_]*$')
);

CREATE UNIQUE INDEX IF NOT EXISTS customer_case_status_phases_code_key
  ON app.customer_case_status_phases (code);

INSERT INTO app.customer_case_status_phases (
  phase,
  code,
  name,
  category,
  sort_order,
  is_terminal
)
VALUES
  (1, 'new_contact', 'Neuer Kontakt', 'qualification', 10, FALSE),
  (2, 'consultation_planned', 'Erstberatung geplant', 'qualification', 20, FALSE),
  (3, 'consultation_done', 'Beratung abgeschlossen', 'qualification', 30, FALSE),
  (4, 'measurement_planning', 'Aufmass / Planung', 'planning', 40, FALSE),
  (5, 'offer_created', 'Angebot erstellt', 'offer', 50, FALSE),
  (6, 'order_confirmed', 'Auftrag erteilt', 'order', 60, FALSE),
  (7, 'production_ordered', 'Bestellung / Produktion', 'fulfillment', 70, FALSE),
  (8, 'delivery_installation', 'Lieferung / Montage', 'fulfillment', 80, FALSE),
  (9, 'acceptance_invoice', 'Abnahme / Rechnung', 'billing', 90, FALSE),
  (10, 'aftersales_closed', 'Aftersales / Abgeschlossen', 'aftersales', 100, TRUE)
ON CONFLICT (phase) DO UPDATE
SET
  code = EXCLUDED.code,
  name = EXCLUDED.name,
  category = EXCLUDED.category,
  sort_order = EXCLUDED.sort_order,
  is_terminal = EXCLUDED.is_terminal;

ALTER TABLE app.customer_cases
  ADD COLUMN IF NOT EXISTS customer_id BIGINT REFERENCES app.customers (id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS case_title TEXT,
  ADD COLUMN IF NOT EXISTS case_type TEXT NOT NULL DEFAULT 'kitchen_project',
  ADD COLUMN IF NOT EXISTS status_phase_id SMALLINT REFERENCES app.customer_case_status_phases (phase) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS priority TEXT NOT NULL DEFAULT 'normal',
  ADD COLUMN IF NOT EXISTS case_status TEXT NOT NULL DEFAULT 'active',
  ADD COLUMN IF NOT EXISTS carat_project_number TEXT,
  ADD COLUMN IF NOT EXISTS carat_order_number TEXT,
  ADD COLUMN IF NOT EXISTS external_reference TEXT,
  ADD COLUMN IF NOT EXISTS budget_amount NUMERIC(12, 2),
  ADD COLUMN IF NOT EXISTS expected_close_date DATE,
  ADD COLUMN IF NOT EXISTS target_installation_date DATE,
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS responsible_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS needs_attention BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE app.customer_cases
SET status_phase_id = status_phase
WHERE status_phase_id IS NULL
  AND status_phase BETWEEN 1 AND 10;

UPDATE app.customer_cases
SET status_phase_id = 1
WHERE status_phase_id IS NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_cases_case_type'
      AND conrelid = 'app.customer_cases'::regclass
  ) THEN
    ALTER TABLE app.customer_cases
      ADD CONSTRAINT customer_cases_case_type CHECK (
        case_type IN ('kitchen_project', 'service', 'aftersales', 'complaint', 'other')
      );
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_cases_priority'
      AND conrelid = 'app.customer_cases'::regclass
  ) THEN
    ALTER TABLE app.customer_cases
      ADD CONSTRAINT customer_cases_priority CHECK (
        priority IN ('low', 'normal', 'high', 'urgent')
      );
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_cases_case_status'
      AND conrelid = 'app.customer_cases'::regclass
  ) THEN
    ALTER TABLE app.customer_cases
      ADD CONSTRAINT customer_cases_case_status CHECK (
        case_status IN ('active', 'paused', 'won', 'lost', 'closed')
      );
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_cases_budget_non_negative'
      AND conrelid = 'app.customer_cases'::regclass
  ) THEN
    ALTER TABLE app.customer_cases
      ADD CONSTRAINT customer_cases_budget_non_negative CHECK (
        budget_amount IS NULL OR budget_amount >= 0
      );
  END IF;
END;
$$;

CREATE UNIQUE INDEX IF NOT EXISTS customer_cases_case_number_key
  ON app.customer_cases (case_number)
  WHERE case_number IS NOT NULL;

CREATE INDEX IF NOT EXISTS customer_cases_customer_idx
  ON app.customer_cases (customer_id, is_active);

CREATE INDEX IF NOT EXISTS customer_cases_phase_priority_idx
  ON app.customer_cases (status_phase_id, priority, updated_at DESC);

CREATE INDEX IF NOT EXISTS customer_cases_carat_project_idx
  ON app.customer_cases (lower(COALESCE(carat_project_number, '')));

CREATE TABLE IF NOT EXISTS app.customer_case_participants (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_case_id BIGINT NOT NULL REFERENCES app.customer_cases (id) ON DELETE CASCADE,
  customer_id BIGINT NOT NULL REFERENCES app.customers (id) ON DELETE CASCADE,
  customer_contact_id BIGINT REFERENCES app.customer_contacts (id) ON DELETE SET NULL,
  participant_role TEXT NOT NULL DEFAULT 'primary_customer',
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customer_case_participants_role CHECK (
    participant_role IN (
      'primary_customer',
      'partner',
      'invoice_recipient',
      'delivery_contact',
      'installation_contact',
      'decision_maker',
      'other'
    )
  )
);

CREATE INDEX IF NOT EXISTS customer_case_participants_case_idx
  ON app.customer_case_participants (customer_case_id, participant_role);

CREATE UNIQUE INDEX IF NOT EXISTS customer_case_participants_primary_role_key
  ON app.customer_case_participants (customer_case_id, participant_role)
  WHERE is_primary;

CREATE TABLE IF NOT EXISTS app.customer_case_project_profiles (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_case_id BIGINT NOT NULL REFERENCES app.customer_cases (id) ON DELETE CASCADE,
  kitchen_type TEXT,
  room_type TEXT,
  budget_min NUMERIC(12, 2),
  budget_max NUMERIC(12, 2),
  target_installation_date DATE,
  measurement_date DATE,
  planning_notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customer_case_project_profiles_case_key UNIQUE (customer_case_id),
  CONSTRAINT customer_case_project_profiles_budget_order CHECK (
    budget_min IS NULL
    OR budget_max IS NULL
    OR budget_max >= budget_min
  )
);

CREATE TABLE IF NOT EXISTS app.customer_case_notes (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_case_id BIGINT NOT NULL REFERENCES app.customer_cases (id) ON DELETE CASCADE,
  note_type TEXT NOT NULL DEFAULT 'general',
  body TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'manual',
  created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customer_case_notes_type CHECK (
    note_type IN (
      'general',
      'call',
      'meeting',
      'internal',
      'customer_request',
      'supplier',
      'installation'
    )
  ),
  CONSTRAINT customer_case_notes_body_not_blank CHECK (btrim(body) <> ''),
  CONSTRAINT customer_case_notes_source CHECK (
    source IN ('manual', 'email_import', 'system_import', 'scas_agent')
  )
);

CREATE INDEX IF NOT EXISTS customer_case_notes_case_idx
  ON app.customer_case_notes (customer_case_id, created_at DESC);

CREATE TABLE IF NOT EXISTS app.customer_case_documents (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_case_id BIGINT NOT NULL REFERENCES app.customer_cases (id) ON DELETE CASCADE,
  document_type TEXT NOT NULL DEFAULT 'other',
  original_filename TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  content_type TEXT NOT NULL,
  file_size_bytes BIGINT NOT NULL,
  source_system TEXT NOT NULL DEFAULT 'hetzner',
  uploaded_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customer_case_documents_type CHECK (
    document_type IN (
      'offer',
      'measurement',
      'order_confirmation',
      'delivery_note',
      'invoice',
      'plan',
      'photo',
      'contract',
      'email_attachment',
      'other'
    )
  ),
  CONSTRAINT customer_case_documents_filename_not_blank CHECK (
    btrim(original_filename) <> ''
  ),
  CONSTRAINT customer_case_documents_storage_path_not_blank CHECK (
    btrim(storage_path) <> ''
  ),
  CONSTRAINT customer_case_documents_file_size_positive CHECK (file_size_bytes > 0),
  CONSTRAINT customer_case_documents_allowed_content_type CHECK (
    content_type IN (
      'application/pdf',
      'image/jpeg',
      'image/png',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
  ),
  CONSTRAINT customer_case_documents_source_system CHECK (
    source_system IN ('hetzner', 'manual_upload', 'email_import', 'scas_agent')
  )
);

CREATE INDEX IF NOT EXISTS customer_case_documents_case_idx
  ON app.customer_case_documents (customer_case_id, created_at DESC);

CREATE TABLE IF NOT EXISTS app.customer_case_audit_events (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_case_id BIGINT NOT NULL REFERENCES app.customer_cases (id) ON DELETE CASCADE,
  actor_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  field_name TEXT,
  old_value_json JSONB,
  new_value_json JSONB,
  details TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customer_case_audit_events_action_not_blank CHECK (btrim(action) <> '')
);

CREATE INDEX IF NOT EXISTS customer_case_audit_events_case_idx
  ON app.customer_case_audit_events (customer_case_id, created_at DESC);

DO $$
DECLARE
  case_record RECORD;
  new_customer_id BIGINT;
BEGIN
  FOR case_record IN
    SELECT id, customer_display_name, owner_user_id, created_by_user_id
    FROM app.customer_cases
    WHERE customer_id IS NULL
  LOOP
    INSERT INTO app.customers (
      display_name,
      customer_type,
      source,
      owner_user_id,
      created_by_user_id
    )
    VALUES (
      case_record.customer_display_name,
      'private',
      'legacy_customer_case',
      case_record.owner_user_id,
      case_record.created_by_user_id
    )
    RETURNING id INTO new_customer_id;

    UPDATE app.customer_cases
    SET customer_id = new_customer_id
    WHERE id = case_record.id;
  END LOOP;
END;
$$;

INSERT INTO app.customer_case_participants (
  customer_case_id,
  customer_id,
  participant_role,
  is_primary
)
SELECT
  customer_cases.id,
  customer_cases.customer_id,
  'primary_customer',
  TRUE
FROM app.customer_cases
WHERE customer_cases.customer_id IS NOT NULL
ON CONFLICT DO NOTHING;

DO $$
DECLARE
  table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'customers',
    'customer_addresses',
    'customer_contacts',
    'customer_case_status_phases',
    'customer_cases',
    'customer_case_participants',
    'customer_case_project_profiles',
    'customer_case_notes'
  ]
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
  ('customers.view', 'Kunden ansehen', 'Kundendaten und Kundenmappen ansehen.'),
  ('customers.manage', 'Kunden verwalten', 'Kundendaten anlegen und bearbeiten.'),
  ('customer_cases.view', 'Vorgaenge ansehen', 'Kundenvorgaenge und Statusphasen ansehen.'),
  ('customer_cases.manage', 'Vorgaenge verwalten', 'Kundenvorgaenge anlegen und bearbeiten.'),
  ('customer_notes.manage', 'Kundennotizen verwalten', 'Notizen in Kundenmappen anlegen und bearbeiten.'),
  ('customer_documents.manage', 'Kundendokumente verwalten', 'Dokumente in Kundenmappen hochladen und verwalten.')
ON CONFLICT (code) DO UPDATE
SET
  name = EXCLUDED.name,
  description = EXCLUDED.description;

INSERT INTO app.role_permissions (role_id, permission_id)
SELECT roles.id, permissions.id
FROM app.roles
JOIN app.permissions ON permissions.code IN (
  'customers.view',
  'customers.manage',
  'customer_cases.view',
  'customer_cases.manage',
  'customer_notes.manage',
  'customer_documents.manage'
)
WHERE roles.code = 'admin'
ON CONFLICT DO NOTHING;

INSERT INTO app.role_permissions (role_id, permission_id)
SELECT roles.id, permissions.id
FROM app.roles
JOIN app.permissions ON permissions.code IN (
  'customers.view',
  'customers.manage',
  'customer_cases.view',
  'customer_cases.manage',
  'customer_notes.manage',
  'customer_documents.manage'
)
WHERE roles.code = 'sales'
ON CONFLICT DO NOTHING;

INSERT INTO app.role_permissions (role_id, permission_id)
SELECT roles.id, permissions.id
FROM app.roles
JOIN app.permissions ON permissions.code IN (
  'customers.view',
  'customer_cases.view',
  'customer_notes.manage',
  'customer_documents.manage'
)
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
