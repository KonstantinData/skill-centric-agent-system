PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ref_phases (
  phase INTEGER PRIMARY KEY CHECK (phase BETWEEN 1 AND 10),
  label TEXT NOT NULL,
  category TEXT NOT NULL
);

INSERT OR IGNORE INTO ref_phases (phase, label, category) VALUES
  (1, 'Neuer Kontakt', 'qualification'),
  (2, 'Erstberatung geplant', 'qualification'),
  (3, 'Bedarf geklaert', 'planning'),
  (4, 'Aufmass geplant', 'planning'),
  (5, 'Planung in Arbeit', 'planning'),
  (6, 'Angebot erstellt', 'offer'),
  (7, 'Auftrag bestaetigt', 'order'),
  (8, 'Lieferung und Montage', 'fulfillment'),
  (9, 'Abnahme und Rechnung', 'billing'),
  (10, 'Aftersales', 'aftersales');

CREATE TABLE IF NOT EXISTS customers (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  full_name TEXT NOT NULL,
  email TEXT,
  phone TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_customers_tenant_name
  ON customers (tenant_id, full_name);

CREATE TABLE IF NOT EXISTS customer_cases (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  customer_id TEXT NOT NULL,
  case_number TEXT NOT NULL,
  phase INTEGER NOT NULL DEFAULT 1 CHECK (phase BETWEEN 1 AND 10),
  priority TEXT NOT NULL DEFAULT 'normal'
    CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'paused', 'won', 'lost', 'closed')),
  assigned_to TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (customer_id) REFERENCES customers (id),
  FOREIGN KEY (phase) REFERENCES ref_phases (phase),
  UNIQUE (tenant_id, case_number)
);

CREATE INDEX IF NOT EXISTS idx_cases_tenant_updated
  ON customer_cases (tenant_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_cases_tenant_phase
  ON customer_cases (tenant_id, phase);

CREATE INDEX IF NOT EXISTS idx_cases_tenant_assigned
  ON customer_cases (tenant_id, assigned_to);

CREATE TABLE IF NOT EXISTS case_project_profiles (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  case_id TEXT NOT NULL UNIQUE,
  kitchen_type TEXT,
  room_type TEXT,
  budget_min INTEGER,
  budget_max INTEGER,
  target_installation_date TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (case_id) REFERENCES customer_cases (id)
);

CREATE TABLE IF NOT EXISTS case_notes (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  case_id TEXT NOT NULL,
  note_type TEXT NOT NULL DEFAULT 'manual',
  content TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'manual'
    CHECK (source IN ('manual', 'skill_suggestion', 'system_import')),
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (case_id) REFERENCES customer_cases (id)
);

CREATE INDEX IF NOT EXISTS idx_notes_case_created
  ON case_notes (tenant_id, case_id, created_at DESC);

CREATE TRIGGER IF NOT EXISTS trg_case_notes_no_update
BEFORE UPDATE ON case_notes
BEGIN
  SELECT RAISE(FAIL, 'case_notes are immutable');
END;

CREATE TRIGGER IF NOT EXISTS trg_case_notes_no_delete
BEFORE DELETE ON case_notes
BEGIN
  SELECT RAISE(FAIL, 'case_notes are immutable');
END;

CREATE TABLE IF NOT EXISTS case_tasks (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  case_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'in_progress', 'done', 'cancelled')),
  due_date TEXT,
  assigned_to TEXT,
  source TEXT NOT NULL DEFAULT 'manual'
    CHECK (source IN ('manual', 'skill_suggestion', 'system_import')),
  confirmed_by TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (case_id) REFERENCES customer_cases (id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_due
  ON case_tasks (tenant_id, status, due_date);

CREATE INDEX IF NOT EXISTS idx_tasks_case
  ON case_tasks (tenant_id, case_id);

CREATE TABLE IF NOT EXISTS case_communications (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  case_id TEXT NOT NULL,
  channel TEXT NOT NULL
    CHECK (channel IN ('phone', 'email', 'in_person', 'video', 'other')),
  direction TEXT NOT NULL
    CHECK (direction IN ('inbound', 'outbound', 'internal')),
  summary TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'manual'
    CHECK (source IN ('manual', 'skill_suggestion', 'system_import')),
  confirmed_by TEXT,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (case_id) REFERENCES customer_cases (id)
);

CREATE INDEX IF NOT EXISTS idx_communications_case_created
  ON case_communications (tenant_id, case_id, created_at DESC);

CREATE TABLE IF NOT EXISTS case_appointments (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  case_id TEXT NOT NULL,
  appointment_type TEXT NOT NULL,
  starts_at TEXT NOT NULL,
  ends_at TEXT,
  location TEXT,
  status TEXT NOT NULL DEFAULT 'planned'
    CHECK (status IN ('planned', 'done', 'cancelled')),
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (case_id) REFERENCES customer_cases (id)
);

CREATE INDEX IF NOT EXISTS idx_appointments_tenant_starts
  ON case_appointments (tenant_id, starts_at);

CREATE TABLE IF NOT EXISTS case_documents (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  case_id TEXT NOT NULL,
  document_type TEXT NOT NULL
    CHECK (
      document_type IN (
        'angebot',
        'aufmass_skizze',
        'auftragsbestaetigung',
        'lieferschein',
        'rechnung',
        'other'
      )
    ),
  source_system TEXT NOT NULL
    CHECK (source_system IN ('R2', 'SharePoint', 'manual_upload')),
  storage_url TEXT NOT NULL,
  file_name TEXT,
  mime_type TEXT,
  uploaded_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (case_id) REFERENCES customer_cases (id)
);

CREATE INDEX IF NOT EXISTS idx_documents_case_created
  ON case_documents (tenant_id, case_id, created_at DESC);

CREATE TABLE IF NOT EXISTS case_audit_events (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  case_id TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  field_name TEXT,
  old_value TEXT,
  new_value TEXT,
  details TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (case_id) REFERENCES customer_cases (id)
);

CREATE INDEX IF NOT EXISTS idx_audit_case_created
  ON case_audit_events (tenant_id, case_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_tenant_actor
  ON case_audit_events (tenant_id, actor, created_at DESC);
