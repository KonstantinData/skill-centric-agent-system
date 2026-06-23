DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_case_status_phases_range'
      AND conrelid = 'app.customer_case_status_phases'::regclass
  ) THEN
    ALTER TABLE app.customer_case_status_phases
      DROP CONSTRAINT customer_case_status_phases_range;
  END IF;

  ALTER TABLE app.customer_case_status_phases
    ADD CONSTRAINT customer_case_status_phases_range CHECK (phase BETWEEN 1 AND 11);

  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_cases_status_phase_range'
      AND conrelid = 'app.customer_cases'::regclass
  ) THEN
    ALTER TABLE app.customer_cases
      DROP CONSTRAINT customer_cases_status_phase_range;
  END IF;

  ALTER TABLE app.customer_cases
    ADD CONSTRAINT customer_cases_status_phase_range CHECK (
      status_phase IS NULL OR status_phase BETWEEN 1 AND 11
    );
END;
$$;

INSERT INTO app.customer_case_status_phases (
  phase,
  code,
  name,
  category,
  sort_order,
  is_terminal
)
VALUES
  (1, 'inquiry', 'Anfrage', 'qualification', 10, FALSE),
  (2, 'consultation', 'Beratung', 'qualification', 20, FALSE),
  (3, 'planning', 'Planung', 'planning', 30, FALSE),
  (4, 'offer', 'Angebot', 'offer', 40, FALSE),
  (5, 'order', 'Auftrag', 'order', 50, FALSE),
  (6, 'order_processing', 'Bestellabwicklung', 'fulfillment', 60, FALSE),
  (7, 'order_confirmation_check', 'AB-Kontrolle', 'fulfillment', 70, FALSE),
  (8, 'delivery_installation', 'Lieferung und Montage', 'fulfillment', 80, FALSE),
  (9, 'invoice', 'Rechnung', 'billing', 90, FALSE),
  (10, 'service_complaint', 'Kundendienst/Reklamation', 'aftersales', 100, FALSE),
  (11, 'closed', 'Abgeschlossen', 'closed', 110, TRUE)
ON CONFLICT (phase) DO UPDATE
SET
  code = EXCLUDED.code,
  name = EXCLUDED.name,
  category = EXCLUDED.category,
  sort_order = EXCLUDED.sort_order,
  is_terminal = EXCLUDED.is_terminal;

CREATE TABLE IF NOT EXISTS app.customer_file_sections (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_id BIGINT NOT NULL REFERENCES app.customers (id) ON DELETE CASCADE,
  section_code TEXT NOT NULL,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customer_file_sections_code_format CHECK (
    section_code ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT customer_file_sections_payload_object CHECK (
    jsonb_typeof(payload_json) = 'object'
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS customer_file_sections_customer_code_key
  ON app.customer_file_sections (customer_id, section_code);

CREATE TABLE IF NOT EXISTS app.customer_case_sections (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_case_id BIGINT NOT NULL REFERENCES app.customer_cases (id) ON DELETE CASCADE,
  section_code TEXT NOT NULL,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customer_case_sections_code_format CHECK (
    section_code ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT customer_case_sections_payload_object CHECK (
    jsonb_typeof(payload_json) = 'object'
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS customer_case_sections_case_code_key
  ON app.customer_case_sections (customer_case_id, section_code);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_file_sections_code'
      AND conrelid = 'app.customer_file_sections'::regclass
  ) THEN
    ALTER TABLE app.customer_file_sections
      DROP CONSTRAINT customer_file_sections_code;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_file_sections_code_format'
      AND conrelid = 'app.customer_file_sections'::regclass
  ) THEN
    ALTER TABLE app.customer_file_sections
      DROP CONSTRAINT customer_file_sections_code_format;
  END IF;

  ALTER TABLE app.customer_file_sections
    ADD CONSTRAINT customer_file_sections_code_format CHECK (
      section_code ~ '^[a-z][a-z0-9_]*$'
    );

  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_case_sections_code'
      AND conrelid = 'app.customer_case_sections'::regclass
  ) THEN
    ALTER TABLE app.customer_case_sections
      DROP CONSTRAINT customer_case_sections_code;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_case_sections_code_format'
      AND conrelid = 'app.customer_case_sections'::regclass
  ) THEN
    ALTER TABLE app.customer_case_sections
      DROP CONSTRAINT customer_case_sections_code_format;
  END IF;

  ALTER TABLE app.customer_case_sections
    ADD CONSTRAINT customer_case_sections_code_format CHECK (
      section_code ~ '^[a-z][a-z0-9_]*$'
    );
END;
$$;

ALTER TABLE app.customer_file_sections
  ADD COLUMN IF NOT EXISTS payload_json JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE app.customer_case_sections
  ADD COLUMN IF NOT EXISTS payload_json JSONB NOT NULL DEFAULT '{}'::jsonb;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'app'
      AND table_name = 'customer_file_sections'
      AND column_name = 'payload'
  ) THEN
    UPDATE app.customer_file_sections
    SET payload_json = payload
    WHERE payload_json = '{}'::jsonb
      AND payload IS NOT NULL;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'app'
      AND table_name = 'customer_case_sections'
      AND column_name = 'payload'
  ) THEN
    UPDATE app.customer_case_sections
    SET payload_json = payload
    WHERE payload_json = '{}'::jsonb
      AND payload IS NOT NULL;
  END IF;
END;
$$;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_daskuechenhaus_app') THEN
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
      app.customer_file_sections,
      app.customer_case_sections
    TO tenant_daskuechenhaus_app;

    GRANT USAGE, SELECT, UPDATE ON SEQUENCE
      app.customer_file_sections_id_seq,
      app.customer_case_sections_id_seq
    TO tenant_daskuechenhaus_app;
  END IF;
END;
$$;
