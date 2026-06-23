ALTER TABLE app.customer_case_documents
  ADD COLUMN IF NOT EXISTS storage_backend TEXT NOT NULL DEFAULT 'local',
  ADD COLUMN IF NOT EXISTS object_storage_bucket TEXT,
  ADD COLUMN IF NOT EXISTS object_storage_key TEXT,
  ADD COLUMN IF NOT EXISTS content_sha256 TEXT;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_case_documents_storage_backend'
      AND conrelid = 'app.customer_case_documents'::regclass
  ) THEN
    ALTER TABLE app.customer_case_documents
      DROP CONSTRAINT customer_case_documents_storage_backend;
  END IF;

  ALTER TABLE app.customer_case_documents
    ADD CONSTRAINT customer_case_documents_storage_backend CHECK (
      storage_backend IN ('local', 'object_storage')
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
        'complaint_service',
        'delivery_installation',
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
    WHERE conname = 'customer_case_documents_object_storage_complete'
      AND conrelid = 'app.customer_case_documents'::regclass
  ) THEN
    ALTER TABLE app.customer_case_documents
      DROP CONSTRAINT customer_case_documents_object_storage_complete;
  END IF;

  ALTER TABLE app.customer_case_documents
    ADD CONSTRAINT customer_case_documents_object_storage_complete CHECK (
      storage_backend <> 'object_storage'
      OR (
        btrim(COALESCE(object_storage_bucket, '')) <> ''
        AND btrim(COALESCE(object_storage_key, '')) <> ''
      )
    );

  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'customer_case_documents_content_sha256'
      AND conrelid = 'app.customer_case_documents'::regclass
  ) THEN
    ALTER TABLE app.customer_case_documents
      DROP CONSTRAINT customer_case_documents_content_sha256;
  END IF;

  ALTER TABLE app.customer_case_documents
    ADD CONSTRAINT customer_case_documents_content_sha256 CHECK (
      content_sha256 IS NULL OR content_sha256 ~ '^[a-f0-9]{64}$'
    );
END;
$$;

CREATE INDEX IF NOT EXISTS customer_case_documents_object_storage_idx
  ON app.customer_case_documents (object_storage_bucket, object_storage_key)
  WHERE storage_backend = 'object_storage';

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_daskuechenhaus_app') THEN
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
      app.customer_case_documents
    TO tenant_daskuechenhaus_app;
  END IF;
END;
$$;
