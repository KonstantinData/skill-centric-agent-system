ALTER TABLE app.customer_case_documents
  ADD COLUMN IF NOT EXISTS register_code TEXT NOT NULL DEFAULT 'anfrage',
  ADD COLUMN IF NOT EXISTS document_category TEXT NOT NULL DEFAULT 'customer_document',
  ADD COLUMN IF NOT EXISTS document_status TEXT NOT NULL DEFAULT 'received',
  ADD COLUMN IF NOT EXISTS title TEXT,
  ADD COLUMN IF NOT EXISTS note TEXT,
  ADD COLUMN IF NOT EXISTS version_label TEXT NOT NULL DEFAULT '1',
  ADD COLUMN IF NOT EXISTS is_current_version BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS replaces_document_id BIGINT REFERENCES app.customer_case_documents (id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS archived_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE app.customer_case_documents
  ALTER COLUMN original_filename DROP NOT NULL,
  ALTER COLUMN storage_path DROP NOT NULL,
  ALTER COLUMN content_type DROP NOT NULL,
  ALTER COLUMN file_size_bytes DROP NOT NULL;

UPDATE app.customer_case_documents
SET title = COALESCE(NULLIF(title, ''), original_filename, 'Dokument'),
    register_code = COALESCE(NULLIF(register_code, ''), 'anfrage'),
    document_category = COALESCE(NULLIF(document_category, ''), 'customer_document'),
    document_status = COALESCE(NULLIF(document_status, ''), 'received'),
    version_label = COALESCE(NULLIF(version_label, ''), '1')
WHERE title IS NULL
   OR register_code IS NULL
   OR document_category IS NULL
   OR document_status IS NULL
   OR version_label IS NULL;

UPDATE app.customer_case_documents
SET document_category = CASE
      WHEN document_category IN (
        'from_customer',
        'measurement',
        'planning',
        'offer',
        'order',
        'order_processing',
        'delivery_installation',
        'complaint_service',
        'invoice',
        'customer_document',
        'drawing_plan',
        'offer_order',
        'invoice_closure'
      ) THEN document_category
      ELSE 'customer_document'
    END,
    document_type = CASE
      WHEN document_type IN (
        'offer',
        'measurement',
        'order_confirmation',
        'delivery_note',
        'invoice',
        'plan',
        'photo',
        'contract',
        'email_attachment',
        'customer_document',
        'drawing_plan',
        'offer_order',
        'invoice_closure',
        'carat_project',
        'other'
      ) THEN document_type
      ELSE 'other'
    END;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_case_documents_type'
      AND conrelid = 'app.customer_case_documents'::regclass
  ) THEN
    ALTER TABLE app.customer_case_documents
      DROP CONSTRAINT customer_case_documents_type;
  END IF;

  ALTER TABLE app.customer_case_documents
    ADD CONSTRAINT customer_case_documents_type CHECK (
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
        'customer_document',
        'drawing_plan',
        'offer_order',
        'invoice_closure',
        'carat_project',
        'other'
      )
    );

  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_case_documents_register_code'
      AND conrelid = 'app.customer_case_documents'::regclass
  ) THEN
    ALTER TABLE app.customer_case_documents
      DROP CONSTRAINT customer_case_documents_register_code;
  END IF;

  ALTER TABLE app.customer_case_documents
    ADD CONSTRAINT customer_case_documents_register_code CHECK (
      register_code IN (
        'anfrage',
        'beratung',
        'planung',
        'angebot_auftrag',
        'abwicklung',
        'rechnung_abschluss',
        'kommunikation'
      )
    );

  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_case_documents_category'
      AND conrelid = 'app.customer_case_documents'::regclass
  ) THEN
    ALTER TABLE app.customer_case_documents
      DROP CONSTRAINT customer_case_documents_category;
  END IF;

  ALTER TABLE app.customer_case_documents
    ADD CONSTRAINT customer_case_documents_category CHECK (
      document_category IN (
        'from_customer',
        'measurement',
        'planning',
        'offer',
        'order',
        'order_processing',
        'delivery_installation',
        'complaint_service',
        'invoice',
        'customer_document',
        'drawing_plan',
        'offer_order',
        'invoice_closure'
      )
    );

  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_case_documents_status'
      AND conrelid = 'app.customer_case_documents'::regclass
  ) THEN
    ALTER TABLE app.customer_case_documents
      DROP CONSTRAINT customer_case_documents_status;
  END IF;

  ALTER TABLE app.customer_case_documents
    ADD CONSTRAINT customer_case_documents_status CHECK (
      document_status IN (
        'draft',
        'received',
        'in_review',
        'approved',
        'sent_to_customer',
        'confirmed_by_customer',
        'replaced',
        'archived'
      )
    );

  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_case_documents_title_not_blank'
      AND conrelid = 'app.customer_case_documents'::regclass
  ) THEN
    ALTER TABLE app.customer_case_documents
      DROP CONSTRAINT customer_case_documents_title_not_blank;
  END IF;

  ALTER TABLE app.customer_case_documents
    ADD CONSTRAINT customer_case_documents_title_not_blank CHECK (
      btrim(COALESCE(title, original_filename, '')) <> ''
    );

  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_case_documents_file_size_positive'
      AND conrelid = 'app.customer_case_documents'::regclass
  ) THEN
    ALTER TABLE app.customer_case_documents
      DROP CONSTRAINT customer_case_documents_file_size_positive;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_case_documents_file_size_non_negative'
      AND conrelid = 'app.customer_case_documents'::regclass
  ) THEN
    ALTER TABLE app.customer_case_documents
      DROP CONSTRAINT customer_case_documents_file_size_non_negative;
  END IF;

  ALTER TABLE app.customer_case_documents
    ADD CONSTRAINT customer_case_documents_file_size_non_negative CHECK (
      file_size_bytes IS NULL OR file_size_bytes >= 0
    );
END;
$$;

CREATE INDEX IF NOT EXISTS customer_case_documents_case_register_idx
  ON app.customer_case_documents (
    customer_case_id,
    register_code,
    document_status,
    created_at DESC
  );

CREATE INDEX IF NOT EXISTS customer_case_documents_current_idx
  ON app.customer_case_documents (customer_case_id, is_current_version)
  WHERE is_current_version = TRUE;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_daskuechenhaus_app') THEN
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
      app.customer_case_documents
    TO tenant_daskuechenhaus_app;

    GRANT USAGE, SELECT, UPDATE ON SEQUENCE
      app.customer_case_documents_id_seq
    TO tenant_daskuechenhaus_app;
  END IF;
END;
$$;
