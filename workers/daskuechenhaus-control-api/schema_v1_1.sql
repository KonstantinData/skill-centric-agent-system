PRAGMA foreign_keys = ON;

INSERT INTO ref_phases (phase, label, category) VALUES
  (1, 'Neuer Kontakt', 'qualification'),
  (2, 'Erstberatung geplant', 'qualification'),
  (3, 'Beratung abgeschlossen', 'qualification'),
  (4, 'Aufmass / Planung', 'planning'),
  (5, 'Angebot erstellt', 'offer'),
  (6, 'Auftrag erteilt', 'order'),
  (7, 'Bestellung / Produktion', 'fulfillment'),
  (8, 'Lieferung / Montage', 'fulfillment'),
  (9, 'Abnahme / Rechnung', 'billing'),
  (10, 'Aftersales / Abgeschlossen', 'aftersales')
ON CONFLICT(phase) DO UPDATE SET
  label = excluded.label,
  category = excluded.category;

ALTER TABLE customers ADD COLUMN customer_number TEXT;
ALTER TABLE customers ADD COLUMN customer_type TEXT NOT NULL DEFAULT 'private'
  CHECK (customer_type IN ('private', 'company'));
ALTER TABLE customers ADD COLUMN salutation TEXT;
ALTER TABLE customers ADD COLUMN first_name TEXT;
ALTER TABLE customers ADD COLUMN last_name TEXT;
ALTER TABLE customers ADD COLUMN company_name TEXT;
ALTER TABLE customers ADD COLUMN company_name_2 TEXT;
ALTER TABLE customers ADD COLUMN vat_id TEXT;
ALTER TABLE customers ADD COLUMN mobile TEXT;
ALTER TABLE customers ADD COLUMN country TEXT;
ALTER TABLE customers ADD COLUMN postal_code TEXT;
ALTER TABLE customers ADD COLUMN city TEXT;

ALTER TABLE customer_cases ADD COLUMN carat_order_number TEXT;
ALTER TABLE customer_cases ADD COLUMN created_by_user_id TEXT;
ALTER TABLE customer_cases ADD COLUMN responsible_user_id TEXT;
ALTER TABLE customer_cases ADD COLUMN needs_attention INTEGER NOT NULL DEFAULT 0
  CHECK (needs_attention IN (0, 1));

CREATE TABLE IF NOT EXISTS customer_participants (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  customer_id TEXT NOT NULL,
  participant_index INTEGER NOT NULL,
  participant_type TEXT NOT NULL DEFAULT 'private'
    CHECK (participant_type IN ('private', 'company')),
  role TEXT NOT NULL DEFAULT 'hauptkunde',
  salutation TEXT,
  first_name TEXT,
  last_name TEXT,
  company_name TEXT,
  company_name_2 TEXT,
  vat_id TEXT,
  phone TEXT,
  mobile TEXT,
  email TEXT,
  country TEXT,
  postal_code TEXT,
  city TEXT,
  use_for_offer INTEGER NOT NULL DEFAULT 1 CHECK (use_for_offer IN (0, 1)),
  use_for_order INTEGER NOT NULL DEFAULT 1 CHECK (use_for_order IN (0, 1)),
  use_for_delivery_note INTEGER NOT NULL DEFAULT 1 CHECK (use_for_delivery_note IN (0, 1)),
  use_for_invoice INTEGER NOT NULL DEFAULT 1 CHECK (use_for_invoice IN (0, 1)),
  use_for_graphics_print INTEGER NOT NULL DEFAULT 1 CHECK (use_for_graphics_print IN (0, 1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (customer_id) REFERENCES customers (id),
  UNIQUE (tenant_id, customer_id, participant_index)
);

CREATE INDEX IF NOT EXISTS idx_customer_participants_customer
  ON customer_participants (tenant_id, customer_id, participant_index);

ALTER TABLE case_communications ADD COLUMN subject TEXT;
ALTER TABLE case_communications ADD COLUMN from_address TEXT;
ALTER TABLE case_communications ADD COLUMN to_address TEXT;
ALTER TABLE case_communications ADD COLUMN cc_address TEXT;
ALTER TABLE case_communications ADD COLUMN message_id TEXT;
ALTER TABLE case_communications ADD COLUMN thread_id TEXT;
ALTER TABLE case_communications ADD COLUMN mailbox TEXT;
ALTER TABLE case_communications ADD COLUMN folder TEXT;
ALTER TABLE case_communications ADD COLUMN sent_at TEXT;
ALTER TABLE case_communications ADD COLUMN received_at TEXT;
ALTER TABLE case_communications ADD COLUMN linked_by_user_id TEXT;
ALTER TABLE case_communications ADD COLUMN linked_by_agent_id TEXT;

ALTER TABLE case_appointments ADD COLUMN title TEXT;
ALTER TABLE case_appointments ADD COLUMN assigned_to_user_id TEXT;
ALTER TABLE case_appointments ADD COLUMN external_calendar_system TEXT;
ALTER TABLE case_appointments ADD COLUMN external_calendar_id TEXT;
ALTER TABLE case_appointments ADD COLUMN external_event_id TEXT;
ALTER TABLE case_appointments ADD COLUMN sync_status TEXT NOT NULL DEFAULT 'not_synced'
  CHECK (sync_status IN ('not_synced', 'sync_pending', 'synced', 'sync_failed'));
ALTER TABLE case_appointments ADD COLUMN last_synced_at TEXT;
