ALTER TABLE app.customers
  ADD COLUMN IF NOT EXISTS primary_phone_normalized TEXT,
  ADD COLUMN IF NOT EXISTS primary_mobile_normalized TEXT;

ALTER TABLE app.customer_contacts
  ADD COLUMN IF NOT EXISTS phone_normalized TEXT,
  ADD COLUMN IF NOT EXISTS mobile_normalized TEXT;

UPDATE app.customers
SET
  primary_phone_normalized = NULLIF(regexp_replace(COALESCE(primary_phone, ''), '[^0-9+]', '', 'g'), ''),
  primary_mobile_normalized = NULLIF(regexp_replace(COALESCE(primary_mobile, ''), '[^0-9+]', '', 'g'), '')
WHERE primary_phone_normalized IS NULL
   OR primary_mobile_normalized IS NULL;

UPDATE app.customer_contacts
SET
  phone_normalized = NULLIF(regexp_replace(COALESCE(phone, ''), '[^0-9+]', '', 'g'), ''),
  mobile_normalized = NULLIF(regexp_replace(COALESCE(mobile, ''), '[^0-9+]', '', 'g'), '')
WHERE phone_normalized IS NULL
   OR mobile_normalized IS NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customers_source'
      AND conrelid = 'app.customers'::regclass
  ) THEN
    ALTER TABLE app.customers
      ADD CONSTRAINT customers_source CHECK (
        source IS NULL
        OR source IN (
          'walk_in',
          'website',
          'recommendation',
          'b2b_network',
          'existing_customer',
          'phone',
          'email',
          'fair',
          'other',
          'legacy_customer_case'
        )
      );
  END IF;
END;
$$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_cases_case_type'
      AND conrelid = 'app.customer_cases'::regclass
  ) THEN
    ALTER TABLE app.customer_cases DROP CONSTRAINT customer_cases_case_type;
  END IF;

  ALTER TABLE app.customer_cases
    ADD CONSTRAINT customer_cases_case_type CHECK (
      case_type IN (
        'kitchen_project',
        'kitchen_project_b2b',
        'service',
        'aftersales',
        'complaint',
        'other'
      )
    );
END;
$$;

CREATE UNIQUE INDEX IF NOT EXISTS customers_primary_email_unique_idx
  ON app.customers (lower(primary_email))
  WHERE primary_email IS NOT NULL
    AND is_active = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS customers_primary_phone_normalized_unique_idx
  ON app.customers (primary_phone_normalized)
  WHERE primary_phone_normalized IS NOT NULL
    AND is_active = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS customers_primary_mobile_normalized_unique_idx
  ON app.customers (primary_mobile_normalized)
  WHERE primary_mobile_normalized IS NOT NULL
    AND is_active = TRUE;

CREATE INDEX IF NOT EXISTS customers_search_first_idx
  ON app.customers (
    lower(display_name),
    lower(COALESCE(company_name, '')),
    lower(COALESCE(primary_email, '')),
    COALESCE(primary_phone_normalized, ''),
    COALESCE(primary_mobile_normalized, '')
  );

CREATE INDEX IF NOT EXISTS customer_contacts_search_first_idx
  ON app.customer_contacts (
    lower(display_name),
    lower(COALESCE(email, '')),
    COALESCE(phone_normalized, ''),
    COALESCE(mobile_normalized, '')
  );

CREATE INDEX IF NOT EXISTS customer_addresses_search_first_idx
  ON app.customer_addresses (postal_code, lower(city));

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
