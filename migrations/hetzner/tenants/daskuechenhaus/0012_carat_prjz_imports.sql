CREATE TABLE IF NOT EXISTS app.customer_case_carat_imports (
  id BIGSERIAL PRIMARY KEY,
  customer_case_id BIGINT NOT NULL REFERENCES app.customer_cases (id) ON DELETE CASCADE,
  document_id BIGINT NOT NULL REFERENCES app.customer_case_documents (id) ON DELETE CASCADE,
  parser_version TEXT NOT NULL,
  source_filename TEXT,
  carat_version TEXT,
  project_number TEXT,
  project_name TEXT,
  customer_name TEXT,
  currency TEXT,
  supplier_count INTEGER NOT NULL DEFAULT 0,
  position_count INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'analysis_ready',
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customer_case_carat_imports_status CHECK (
    status IN ('analysis_ready', 'partially_transferred', 'transferred', 'failed')
  ),
  CONSTRAINT customer_case_carat_imports_document_unique UNIQUE (document_id)
);

CREATE INDEX IF NOT EXISTS customer_case_carat_imports_case_idx
  ON app.customer_case_carat_imports (customer_case_id, created_at DESC);

CREATE TABLE IF NOT EXISTS app.customer_case_carat_import_positions (
  id BIGSERIAL PRIMARY KEY,
  import_id BIGINT NOT NULL REFERENCES app.customer_case_carat_imports (id) ON DELETE CASCADE,
  source_line INTEGER,
  position_number TEXT,
  supplier_code TEXT,
  supplier_name TEXT,
  article_code TEXT,
  title TEXT NOT NULL,
  description TEXT,
  quantity NUMERIC(12, 3),
  dimensions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  selection_status TEXT NOT NULL DEFAULT 'candidate',
  selected_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  selected_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customer_case_carat_import_positions_status CHECK (
    selection_status IN ('candidate', 'selected', 'ignored', 'transferred')
  )
);

CREATE INDEX IF NOT EXISTS customer_case_carat_import_positions_import_idx
  ON app.customer_case_carat_import_positions (import_id, supplier_name, id);

ALTER TABLE app.customer_case_documents
  DROP CONSTRAINT IF EXISTS customer_case_documents_allowed_content_type;

ALTER TABLE app.customer_case_documents
  DROP CONSTRAINT IF EXISTS customer_case_documents_type;

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

ALTER TABLE app.customer_case_documents
  ADD CONSTRAINT customer_case_documents_allowed_content_type CHECK (
    content_type IS NULL
    OR content_type IN (
      'application/pdf',
      'image/jpeg',
      'image/png',
      'image/webp',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/zip',
      'application/x-zip-compressed',
      'application/octet-stream'
    )
  );

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_daskuechenhaus_app') THEN
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
      app.customer_case_carat_imports,
      app.customer_case_carat_import_positions
    TO tenant_daskuechenhaus_app;

    GRANT USAGE, SELECT ON SEQUENCE
      app.customer_case_carat_imports_id_seq,
      app.customer_case_carat_import_positions_id_seq
    TO tenant_daskuechenhaus_app;
  END IF;
END;
$$;
