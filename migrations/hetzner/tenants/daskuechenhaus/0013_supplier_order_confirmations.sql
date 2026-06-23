CREATE TABLE IF NOT EXISTS app.suppliers (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  normalized_name TEXT NOT NULL,
  supplier_type TEXT NOT NULL DEFAULT 'standard',
  default_email TEXT,
  phone TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT suppliers_name_not_blank CHECK (btrim(name) <> ''),
  CONSTRAINT suppliers_normalized_name_not_blank CHECK (btrim(normalized_name) <> ''),
  CONSTRAINT suppliers_type CHECK (
    supplier_type IN ('standard', 'appliance', 'furniture', 'accessory', 'service', 'other')
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS suppliers_normalized_name_key
  ON app.suppliers (normalized_name);

CREATE TABLE IF NOT EXISTS app.supplier_contacts (
  id BIGSERIAL PRIMARY KEY,
  supplier_id BIGINT NOT NULL REFERENCES app.suppliers (id) ON DELETE CASCADE,
  display_name TEXT NOT NULL,
  email TEXT,
  phone TEXT,
  role_title TEXT,
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT supplier_contacts_display_name_not_blank CHECK (btrim(display_name) <> '')
);

CREATE INDEX IF NOT EXISTS supplier_contacts_supplier_idx
  ON app.supplier_contacts (supplier_id, is_primary DESC, id);

CREATE TABLE IF NOT EXISTS app.supplier_orders (
  id BIGSERIAL PRIMARY KEY,
  customer_case_id BIGINT NOT NULL REFERENCES app.customer_cases (id) ON DELETE CASCADE,
  supplier_id BIGINT NOT NULL REFERENCES app.suppliers (id) ON DELETE RESTRICT,
  source_carat_import_id BIGINT REFERENCES app.customer_case_carat_imports (id) ON DELETE SET NULL,
  order_number TEXT,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  ordered_position_count INTEGER NOT NULL DEFAULT 0,
  created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT supplier_orders_title_not_blank CHECK (btrim(title) <> ''),
  CONSTRAINT supplier_orders_status CHECK (
    status IN ('draft', 'ordered', 'partially_confirmed', 'confirmed', 'closed', 'canceled')
  )
);

CREATE INDEX IF NOT EXISTS supplier_orders_case_idx
  ON app.supplier_orders (customer_case_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS supplier_orders_supplier_idx
  ON app.supplier_orders (supplier_id, customer_case_id);

CREATE TABLE IF NOT EXISTS app.supplier_order_positions (
  id BIGSERIAL PRIMARY KEY,
  supplier_order_id BIGINT NOT NULL REFERENCES app.supplier_orders (id) ON DELETE CASCADE,
  source_carat_position_id BIGINT REFERENCES app.customer_case_carat_import_positions (id)
    ON DELETE SET NULL,
  position_number TEXT,
  article_code TEXT,
  title TEXT NOT NULL,
  description TEXT,
  quantity NUMERIC(12, 3),
  unit TEXT NOT NULL DEFAULT 'Stk',
  ordered_net_price NUMERIC(12, 2),
  ordered_discount_percent NUMERIC(7, 3),
  ordered_delivery_week TEXT,
  ordered_delivery_date DATE,
  raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT supplier_order_positions_title_not_blank CHECK (btrim(title) <> '')
);

CREATE INDEX IF NOT EXISTS supplier_order_positions_order_idx
  ON app.supplier_order_positions (supplier_order_id, id);

CREATE INDEX IF NOT EXISTS supplier_order_positions_article_idx
  ON app.supplier_order_positions (supplier_order_id, lower(COALESCE(article_code, '')));

CREATE TABLE IF NOT EXISTS app.supplier_confirmation_inbox_items (
  id BIGSERIAL PRIMARY KEY,
  customer_case_id BIGINT NOT NULL REFERENCES app.customer_cases (id) ON DELETE CASCADE,
  document_id BIGINT REFERENCES app.customer_case_documents (id) ON DELETE SET NULL,
  source_type TEXT NOT NULL DEFAULT 'manual_upload',
  status TEXT NOT NULL DEFAULT 'received',
  detected_document_type TEXT,
  confidence_document_type NUMERIC(5, 4),
  detected_supplier_id BIGINT REFERENCES app.suppliers (id) ON DELETE SET NULL,
  confidence_supplier NUMERIC(5, 4),
  detected_order_id BIGINT REFERENCES app.supplier_orders (id) ON DELETE SET NULL,
  confidence_order NUMERIC(5, 4),
  detected_case_id BIGINT REFERENCES app.customer_cases (id) ON DELETE SET NULL,
  confidence_case NUMERIC(5, 4),
  confirmed_supplier_id BIGINT REFERENCES app.suppliers (id) ON DELETE SET NULL,
  confirmed_order_id BIGINT REFERENCES app.supplier_orders (id) ON DELETE SET NULL,
  confirmed_case_id BIGINT REFERENCES app.customer_cases (id) ON DELETE SET NULL,
  proposal_level TEXT NOT NULL DEFAULT 'manual_assignment_required',
  review_required BOOLEAN NOT NULL DEFAULT TRUE,
  review_reason TEXT,
  detection_signals_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  correction_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  correction_reason TEXT,
  corrected_at TIMESTAMPTZ,
  created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT supplier_confirmation_inbox_items_source CHECK (
    source_type IN ('manual_upload', 'email_attachment', 'neutral_inbox', 'manual_entry')
  ),
  CONSTRAINT supplier_confirmation_inbox_items_status CHECK (
    status IN (
      'received',
      'classification_pending',
      'assignment_required',
      'context_review_required',
      'context_confirmed',
      'analysis_pending',
      'matching_in_progress',
      'matching_complete',
      'context_revision_required',
      'context_revised',
      'invalidated',
      'archived'
    )
  ),
  CONSTRAINT supplier_confirmation_inbox_items_proposal_level CHECK (
    proposal_level IN (
      'blocking_conflict',
      'strong_order_match',
      'supplier_match_order_required',
      'ambiguous_review_required',
      'manual_assignment_required'
    )
  )
);

CREATE INDEX IF NOT EXISTS supplier_confirmation_inbox_items_case_idx
  ON app.supplier_confirmation_inbox_items (customer_case_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS app.supplier_order_confirmations (
  id BIGSERIAL PRIMARY KEY,
  inbox_item_id BIGINT NOT NULL REFERENCES app.supplier_confirmation_inbox_items (id)
    ON DELETE RESTRICT,
  customer_case_id BIGINT NOT NULL REFERENCES app.customer_cases (id) ON DELETE CASCADE,
  supplier_order_id BIGINT NOT NULL REFERENCES app.supplier_orders (id) ON DELETE RESTRICT,
  supplier_id BIGINT NOT NULL REFERENCES app.suppliers (id) ON DELETE RESTRICT,
  document_id BIGINT REFERENCES app.customer_case_documents (id) ON DELETE SET NULL,
  confirmation_number TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  ordered_position_count INTEGER NOT NULL DEFAULT 0,
  confirmation_position_count INTEGER NOT NULL DEFAULT 0,
  matched_position_count INTEGER NOT NULL DEFAULT 0,
  unmatched_order_position_count INTEGER NOT NULL DEFAULT 0,
  unmatched_confirmation_position_count INTEGER NOT NULL DEFAULT 0,
  match_rate NUMERIC(7, 4) NOT NULL DEFAULT 0,
  replaces_confirmation_id BIGINT REFERENCES app.supplier_order_confirmations (id)
    ON DELETE SET NULL,
  replaced_by_confirmation_id BIGINT REFERENCES app.supplier_order_confirmations (id)
    ON DELETE SET NULL,
  revision_number INTEGER NOT NULL DEFAULT 1,
  created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  approved_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  approved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT supplier_order_confirmations_status CHECK (
    status IN (
      'draft',
      'matching_in_progress',
      'matched',
      'exceptions_open',
      'context_revision_required',
      'suspended',
      'invalidated',
      'replaced',
      'approved',
      'archived'
    )
  )
);

CREATE INDEX IF NOT EXISTS supplier_order_confirmations_case_idx
  ON app.supplier_order_confirmations (customer_case_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS supplier_order_confirmations_order_idx
  ON app.supplier_order_confirmations (supplier_order_id, created_at DESC);

CREATE TABLE IF NOT EXISTS app.supplier_order_confirmation_positions (
  id BIGSERIAL PRIMARY KEY,
  confirmation_id BIGINT NOT NULL REFERENCES app.supplier_order_confirmations (id)
    ON DELETE CASCADE,
  matched_order_position_id BIGINT REFERENCES app.supplier_order_positions (id)
    ON DELETE SET NULL,
  position_number TEXT,
  article_code TEXT,
  title TEXT NOT NULL,
  description TEXT,
  quantity NUMERIC(12, 3),
  unit TEXT NOT NULL DEFAULT 'Stk',
  confirmed_net_price NUMERIC(12, 2),
  confirmed_discount_percent NUMERIC(7, 3),
  confirmed_delivery_week TEXT,
  confirmed_delivery_date DATE,
  match_status TEXT NOT NULL DEFAULT 'manual_review_required',
  severity TEXT NOT NULL DEFAULT 'yellow',
  raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT supplier_order_confirmation_positions_title_not_blank CHECK (btrim(title) <> ''),
  CONSTRAINT supplier_order_confirmation_positions_match_status CHECK (
    match_status IN (
      'matched',
      'matched_with_warning',
      'manual_review_required',
      'context_revision_required'
    )
  ),
  CONSTRAINT supplier_order_confirmation_positions_severity CHECK (
    severity IN ('green', 'yellow', 'red')
  )
);

CREATE INDEX IF NOT EXISTS supplier_order_confirmation_positions_confirmation_idx
  ON app.supplier_order_confirmation_positions (confirmation_id, severity, id);

CREATE TABLE IF NOT EXISTS app.supplier_order_confirmation_exceptions (
  id BIGSERIAL PRIMARY KEY,
  confirmation_id BIGINT NOT NULL REFERENCES app.supplier_order_confirmations (id)
    ON DELETE CASCADE,
  confirmation_position_id BIGINT REFERENCES app.supplier_order_confirmation_positions (id)
    ON DELETE CASCADE,
  order_position_id BIGINT REFERENCES app.supplier_order_positions (id)
    ON DELETE SET NULL,
  difference_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  ordered_value TEXT,
  confirmed_value TEXT,
  difference_value NUMERIC(12, 3),
  difference_percent NUMERIC(9, 4),
  requires_confirmation BOOLEAN NOT NULL DEFAULT TRUE,
  message TEXT NOT NULL,
  resolved_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  resolved_at TIMESTAMPTZ,
  resolution_action TEXT,
  resolution_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT supplier_order_confirmation_exceptions_type CHECK (
    difference_type IN (
      'article_number',
      'quantity',
      'unit',
      'net_price',
      'discount',
      'delivery_date',
      'text',
      'extra_position',
      'missing_position',
      'unreadable_field',
      'replacement_article',
      'context'
    )
  ),
  CONSTRAINT supplier_order_confirmation_exceptions_severity CHECK (
    severity IN ('yellow', 'red')
  ),
  CONSTRAINT supplier_order_confirmation_exceptions_status CHECK (
    status IN ('open', 'accepted', 'resolved', 'waiting_for_supplier', 'rejected', 'superseded')
  ),
  CONSTRAINT supplier_order_confirmation_exceptions_message_not_blank CHECK (btrim(message) <> '')
);

CREATE INDEX IF NOT EXISTS supplier_order_confirmation_exceptions_confirmation_idx
  ON app.supplier_order_confirmation_exceptions (confirmation_id, status, severity, id);

CREATE TABLE IF NOT EXISTS app.supplier_order_confirmation_decisions (
  id BIGSERIAL PRIMARY KEY,
  confirmation_id BIGINT NOT NULL REFERENCES app.supplier_order_confirmations (id)
    ON DELETE CASCADE,
  exception_id BIGINT REFERENCES app.supplier_order_confirmation_exceptions (id)
    ON DELETE SET NULL,
  actor_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  previous_status TEXT,
  new_status TEXT,
  ordered_value TEXT,
  confirmed_value TEXT,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT supplier_order_confirmation_decisions_action_not_blank CHECK (btrim(action) <> '')
);

CREATE INDEX IF NOT EXISTS supplier_order_confirmation_decisions_confirmation_idx
  ON app.supplier_order_confirmation_decisions (confirmation_id, created_at DESC);

CREATE TABLE IF NOT EXISTS app.supplier_communications (
  id BIGSERIAL PRIMARY KEY,
  customer_case_id BIGINT NOT NULL REFERENCES app.customer_cases (id) ON DELETE CASCADE,
  supplier_id BIGINT REFERENCES app.suppliers (id) ON DELETE SET NULL,
  confirmation_id BIGINT REFERENCES app.supplier_order_confirmations (id) ON DELETE SET NULL,
  exception_id BIGINT REFERENCES app.supplier_order_confirmation_exceptions (id) ON DELETE SET NULL,
  communication_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  recipient_email TEXT,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  marked_sent_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  marked_sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT supplier_communications_type CHECK (
    communication_type IN (
      'corrected_ab_request',
      'price_clarification',
      'delivery_date_clarification',
      'alternative_article_request',
      'quantity_position_clarification',
      'accepted_deviation_confirmation',
      'general_clarification'
    )
  ),
  CONSTRAINT supplier_communications_status CHECK (
    status IN ('draft', 'prepared', 'copied', 'marked_sent', 'canceled')
  ),
  CONSTRAINT supplier_communications_subject_not_blank CHECK (btrim(subject) <> ''),
  CONSTRAINT supplier_communications_body_not_blank CHECK (btrim(body) <> '')
);

CREATE INDEX IF NOT EXISTS supplier_communications_case_idx
  ON app.supplier_communications (customer_case_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS app.supplier_follow_ups (
  id BIGSERIAL PRIMARY KEY,
  customer_case_id BIGINT NOT NULL REFERENCES app.customer_cases (id) ON DELETE CASCADE,
  supplier_id BIGINT REFERENCES app.suppliers (id) ON DELETE SET NULL,
  communication_id BIGINT REFERENCES app.supplier_communications (id) ON DELETE CASCADE,
  confirmation_id BIGINT REFERENCES app.supplier_order_confirmations (id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  due_at TIMESTAMPTZ,
  responsible_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT supplier_follow_ups_title_not_blank CHECK (btrim(title) <> ''),
  CONSTRAINT supplier_follow_ups_status CHECK (
    status IN ('open', 'waiting', 'overdue', 'resolved', 'canceled', 'superseded')
  )
);

CREATE INDEX IF NOT EXISTS supplier_follow_ups_case_idx
  ON app.supplier_follow_ups (customer_case_id, status, due_at NULLS LAST);

DO $$
DECLARE
  table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'suppliers',
    'supplier_contacts',
    'supplier_orders',
    'supplier_order_positions',
    'supplier_confirmation_inbox_items',
    'supplier_order_confirmations',
    'supplier_order_confirmation_positions',
    'supplier_order_confirmation_exceptions',
    'supplier_communications',
    'supplier_follow_ups'
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
  ('supplier_orders.manage', 'Lieferantenbestellungen verwalten', 'Lieferantenbestellungen und AB-Cockpit verwalten.'),
  ('supplier_confirmations.manage', 'AB-Pruefung verwalten', 'Lieferanten-Auftragsbestaetigungen pruefen und freigeben.')
ON CONFLICT (code) DO UPDATE
SET
  name = EXCLUDED.name,
  description = EXCLUDED.description;

INSERT INTO app.role_permissions (role_id, permission_id)
SELECT roles.id, permissions.id
FROM app.roles
JOIN app.permissions ON permissions.code IN (
  'supplier_orders.manage',
  'supplier_confirmations.manage'
)
WHERE roles.code IN ('admin', 'sales')
ON CONFLICT DO NOTHING;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_daskuechenhaus_app') THEN
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
      app.suppliers,
      app.supplier_contacts,
      app.supplier_orders,
      app.supplier_order_positions,
      app.supplier_confirmation_inbox_items,
      app.supplier_order_confirmations,
      app.supplier_order_confirmation_positions,
      app.supplier_order_confirmation_exceptions,
      app.supplier_order_confirmation_decisions,
      app.supplier_communications,
      app.supplier_follow_ups
    TO tenant_daskuechenhaus_app;

    GRANT USAGE, SELECT ON SEQUENCE
      app.suppliers_id_seq,
      app.supplier_contacts_id_seq,
      app.supplier_orders_id_seq,
      app.supplier_order_positions_id_seq,
      app.supplier_confirmation_inbox_items_id_seq,
      app.supplier_order_confirmations_id_seq,
      app.supplier_order_confirmation_positions_id_seq,
      app.supplier_order_confirmation_exceptions_id_seq,
      app.supplier_order_confirmation_decisions_id_seq,
      app.supplier_communications_id_seq,
      app.supplier_follow_ups_id_seq
    TO tenant_daskuechenhaus_app;
  END IF;
END;
$$;
