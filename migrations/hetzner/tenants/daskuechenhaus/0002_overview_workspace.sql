CREATE TABLE IF NOT EXISTS app.customer_cases (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  case_number TEXT,
  customer_display_name TEXT NOT NULL,
  status_phase SMALLINT,
  owner_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customer_cases_customer_name_not_blank CHECK (
    btrim(customer_display_name) <> ''
  ),
  CONSTRAINT customer_cases_status_phase_range CHECK (
    status_phase IS NULL OR status_phase BETWEEN 1 AND 10
  )
);

CREATE INDEX IF NOT EXISTS customer_cases_owner_idx
  ON app.customer_cases (owner_user_id, is_active);

CREATE INDEX IF NOT EXISTS customer_cases_search_idx
  ON app.customer_cases (lower(customer_display_name), lower(COALESCE(case_number, '')));

CREATE TABLE IF NOT EXISTS app.task_statuses (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  is_terminal BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT task_statuses_code_not_blank CHECK (btrim(code) <> ''),
  CONSTRAINT task_statuses_name_not_blank CHECK (btrim(name) <> ''),
  CONSTRAINT task_statuses_code_format CHECK (code ~ '^[a-z][a-z0-9_]*$')
);

CREATE UNIQUE INDEX IF NOT EXISTS task_statuses_code_key
  ON app.task_statuses (code);

CREATE TABLE IF NOT EXISTS app.tasks (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  status_id BIGINT NOT NULL REFERENCES app.task_statuses (id) ON DELETE RESTRICT,
  priority TEXT NOT NULL DEFAULT 'normal',
  due_at TIMESTAMPTZ,
  reminder_at TIMESTAMPTZ,
  reminder_email_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  reminder_overview_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  related_case_id BIGINT REFERENCES app.customer_cases (id) ON DELETE SET NULL,
  created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT tasks_title_not_blank CHECK (btrim(title) <> ''),
  CONSTRAINT tasks_priority CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
  CONSTRAINT tasks_reminder_requires_due_or_reminder_time CHECK (
    reminder_at IS NOT NULL OR NOT reminder_email_enabled
  )
);

CREATE INDEX IF NOT EXISTS tasks_status_due_idx
  ON app.tasks (status_id, due_at);

CREATE INDEX IF NOT EXISTS tasks_related_case_idx
  ON app.tasks (related_case_id);

CREATE TABLE IF NOT EXISTS app.task_assignments (
  task_id BIGINT NOT NULL REFERENCES app.tasks (id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL REFERENCES app.users (id) ON DELETE CASCADE,
  assigned_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (task_id, user_id)
);

CREATE INDEX IF NOT EXISTS task_assignments_user_idx
  ON app.task_assignments (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS app.task_attachments (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  task_id BIGINT NOT NULL REFERENCES app.tasks (id) ON DELETE CASCADE,
  original_filename TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  content_type TEXT NOT NULL,
  file_size_bytes BIGINT NOT NULL,
  uploaded_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT task_attachments_filename_not_blank CHECK (btrim(original_filename) <> ''),
  CONSTRAINT task_attachments_storage_path_not_blank CHECK (btrim(storage_path) <> ''),
  CONSTRAINT task_attachments_file_size_positive CHECK (file_size_bytes > 0),
  CONSTRAINT task_attachments_allowed_content_type CHECK (
    content_type IN (
      'application/pdf',
      'image/jpeg',
      'image/png',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
  )
);

CREATE INDEX IF NOT EXISTS task_attachments_task_idx
  ON app.task_attachments (task_id, created_at DESC);

CREATE TABLE IF NOT EXISTS app.task_reminders (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  task_id BIGINT NOT NULL REFERENCES app.tasks (id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL REFERENCES app.users (id) ON DELETE CASCADE,
  remind_at TIMESTAMPTZ NOT NULL,
  channel TEXT NOT NULL,
  sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT task_reminders_channel CHECK (channel IN ('overview', 'email')),
  CONSTRAINT task_reminders_task_user_channel_key UNIQUE (task_id, user_id, channel)
);

CREATE INDEX IF NOT EXISTS task_reminders_due_idx
  ON app.task_reminders (remind_at, sent_at);

CREATE TABLE IF NOT EXISTS app.appointments (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ,
  location TEXT,
  related_case_id BIGINT REFERENCES app.customer_cases (id) ON DELETE SET NULL,
  owner_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT appointments_title_not_blank CHECK (btrim(title) <> ''),
  CONSTRAINT appointments_time_order CHECK (ends_at IS NULL OR ends_at > starts_at)
);

CREATE INDEX IF NOT EXISTS appointments_owner_start_idx
  ON app.appointments (owner_user_id, starts_at);

CREATE TABLE IF NOT EXISTS app.news_items (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  title TEXT NOT NULL,
  body TEXT,
  category TEXT NOT NULL DEFAULT 'general',
  starts_on DATE,
  ends_on DATE,
  visibility TEXT NOT NULL DEFAULT 'team',
  created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT news_items_title_not_blank CHECK (btrim(title) <> ''),
  CONSTRAINT news_items_category CHECK (
    category IN ('general', 'fair', 'vacation', 'holiday', 'internal')
  ),
  CONSTRAINT news_items_visibility CHECK (visibility IN ('team', 'admin')),
  CONSTRAINT news_items_date_order CHECK (ends_on IS NULL OR starts_on IS NULL OR ends_on >= starts_on)
);

CREATE INDEX IF NOT EXISTS news_items_visibility_idx
  ON app.news_items (visibility, starts_on DESC);

CREATE TABLE IF NOT EXISTS app.goals (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  owner_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  target_date DATE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT goals_title_not_blank CHECK (btrim(title) <> '')
);

CREATE TABLE IF NOT EXISTS app.goal_events (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  goal_id BIGINT NOT NULL REFERENCES app.goals (id) ON DELETE CASCADE,
  achieved_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  achieved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS goal_events_user_idx
  ON app.goal_events (achieved_by_user_id, achieved_at DESC);

CREATE TABLE IF NOT EXISTS app.email_accounts (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  display_name TEXT NOT NULL,
  email_address TEXT NOT NULL,
  provider TEXT NOT NULL DEFAULT 'imap',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT email_accounts_display_name_not_blank CHECK (btrim(display_name) <> ''),
  CONSTRAINT email_accounts_email_not_blank CHECK (btrim(email_address) <> ''),
  CONSTRAINT email_accounts_email_lowercase CHECK (email_address = lower(email_address))
);

CREATE UNIQUE INDEX IF NOT EXISTS email_accounts_email_key
  ON app.email_accounts (email_address);

CREATE TABLE IF NOT EXISTS app.email_messages (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email_account_id BIGINT REFERENCES app.email_accounts (id) ON DELETE SET NULL,
  external_message_id TEXT,
  direction TEXT NOT NULL,
  subject TEXT NOT NULL,
  snippet TEXT,
  received_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  assigned_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  is_unassigned BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT email_messages_subject_not_blank CHECK (btrim(subject) <> ''),
  CONSTRAINT email_messages_direction CHECK (direction IN ('inbound', 'outbound', 'internal'))
);

CREATE INDEX IF NOT EXISTS email_messages_unassigned_idx
  ON app.email_messages (is_unassigned, received_at DESC);

CREATE INDEX IF NOT EXISTS email_messages_assigned_user_idx
  ON app.email_messages (assigned_user_id, received_at DESC);

CREATE TABLE IF NOT EXISTS app.email_participants (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email_message_id BIGINT NOT NULL REFERENCES app.email_messages (id) ON DELETE CASCADE,
  participant_type TEXT NOT NULL,
  display_name TEXT,
  email_address TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT email_participants_type CHECK (
    participant_type IN ('from', 'to', 'cc', 'bcc', 'reply_to')
  ),
  CONSTRAINT email_participants_email_not_blank CHECK (btrim(email_address) <> '')
);

CREATE INDEX IF NOT EXISTS email_participants_message_idx
  ON app.email_participants (email_message_id);

CREATE TABLE IF NOT EXISTS app.email_attachments (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email_message_id BIGINT NOT NULL REFERENCES app.email_messages (id) ON DELETE CASCADE,
  original_filename TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  content_type TEXT NOT NULL,
  file_size_bytes BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT email_attachments_filename_not_blank CHECK (btrim(original_filename) <> ''),
  CONSTRAINT email_attachments_storage_path_not_blank CHECK (btrim(storage_path) <> ''),
  CONSTRAINT email_attachments_file_size_positive CHECK (file_size_bytes > 0)
);

CREATE INDEX IF NOT EXISTS email_attachments_message_idx
  ON app.email_attachments (email_message_id);

CREATE TABLE IF NOT EXISTS app.email_case_links (
  email_message_id BIGINT NOT NULL REFERENCES app.email_messages (id) ON DELETE CASCADE,
  customer_case_id BIGINT NOT NULL REFERENCES app.customer_cases (id) ON DELETE CASCADE,
  assigned_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (email_message_id, customer_case_id)
);

CREATE INDEX IF NOT EXISTS email_case_links_case_idx
  ON app.email_case_links (customer_case_id, assigned_at DESC);

CREATE TABLE IF NOT EXISTS app.email_assignment_suggestions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email_message_id BIGINT NOT NULL REFERENCES app.email_messages (id) ON DELETE CASCADE,
  suggested_case_id BIGINT REFERENCES app.customer_cases (id) ON DELETE SET NULL,
  suggested_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  confidence NUMERIC(5, 4) NOT NULL,
  reason TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  decided_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  decided_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT email_assignment_suggestions_confidence_range CHECK (
    confidence >= 0 AND confidence <= 1
  ),
  CONSTRAINT email_assignment_suggestions_status CHECK (
    status IN ('pending', 'accepted', 'rejected')
  )
);

CREATE INDEX IF NOT EXISTS email_assignment_suggestions_pending_idx
  ON app.email_assignment_suggestions (status, created_at DESC);

CREATE TABLE IF NOT EXISTS app.communication_events (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_type TEXT NOT NULL,
  customer_case_id BIGINT REFERENCES app.customer_cases (id) ON DELETE SET NULL,
  task_id BIGINT REFERENCES app.tasks (id) ON DELETE SET NULL,
  email_message_id BIGINT REFERENCES app.email_messages (id) ON DELETE SET NULL,
  actor_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  body TEXT,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT communication_events_type_not_blank CHECK (btrim(event_type) <> ''),
  CONSTRAINT communication_events_title_not_blank CHECK (btrim(title) <> '')
);

CREATE INDEX IF NOT EXISTS communication_events_case_idx
  ON app.communication_events (customer_case_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS communication_events_actor_idx
  ON app.communication_events (actor_user_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS app.absences (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES app.users (id) ON DELETE CASCADE,
  absence_type TEXT NOT NULL DEFAULT 'vacation',
  starts_on DATE NOT NULL,
  ends_on DATE NOT NULL,
  note TEXT,
  created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT absences_type CHECK (absence_type IN ('vacation', 'sick_leave', 'other')),
  CONSTRAINT absences_date_order CHECK (ends_on >= starts_on)
);

CREATE INDEX IF NOT EXISTS absences_user_date_idx
  ON app.absences (user_id, starts_on, ends_on);

CREATE TABLE IF NOT EXISTS app.user_delegations (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  delegator_user_id BIGINT NOT NULL REFERENCES app.users (id) ON DELETE CASCADE,
  delegate_user_id BIGINT NOT NULL REFERENCES app.users (id) ON DELETE CASCADE,
  absence_id BIGINT REFERENCES app.absences (id) ON DELETE SET NULL,
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ NOT NULL,
  scope TEXT NOT NULL DEFAULT 'overview',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT user_delegations_scope CHECK (scope IN ('overview', 'tasks', 'case_work')),
  CONSTRAINT user_delegations_time_order CHECK (ends_at > starts_at),
  CONSTRAINT user_delegations_not_self CHECK (delegator_user_id <> delegate_user_id)
);

CREATE INDEX IF NOT EXISTS user_delegations_delegate_active_idx
  ON app.user_delegations (delegate_user_id, is_active, starts_at, ends_at);

CREATE TABLE IF NOT EXISTS audit.delegated_actions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  acting_user_id BIGINT NOT NULL REFERENCES app.users (id) ON DELETE CASCADE,
  represented_user_id BIGINT NOT NULL REFERENCES app.users (id) ON DELETE CASCADE,
  delegation_id BIGINT REFERENCES app.user_delegations (id) ON DELETE SET NULL,
  entity_schema TEXT NOT NULL,
  entity_table TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT delegated_actions_entity_schema_not_blank CHECK (btrim(entity_schema) <> ''),
  CONSTRAINT delegated_actions_entity_table_not_blank CHECK (btrim(entity_table) <> ''),
  CONSTRAINT delegated_actions_entity_id_not_blank CHECK (btrim(entity_id) <> ''),
  CONSTRAINT delegated_actions_action_not_blank CHECK (btrim(action) <> '')
);

CREATE INDEX IF NOT EXISTS delegated_actions_actor_idx
  ON audit.delegated_actions (acting_user_id, created_at DESC);

DO $$
DECLARE
  table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'customer_cases',
    'task_statuses',
    'tasks',
    'appointments',
    'news_items',
    'goals',
    'email_accounts',
    'email_messages',
    'absences',
    'user_delegations'
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

INSERT INTO app.task_statuses (code, name, sort_order, is_terminal)
VALUES
  ('new', 'Neu', 10, FALSE),
  ('planned', 'Geplant', 20, FALSE),
  ('in_progress', 'In Arbeit', 30, FALSE),
  ('waiting', 'Wartet auf Rueckmeldung', 40, FALSE),
  ('done', 'Erledigt', 50, TRUE),
  ('cancelled', 'Abgebrochen', 60, TRUE)
ON CONFLICT (code) DO UPDATE
SET
  name = EXCLUDED.name,
  sort_order = EXCLUDED.sort_order,
  is_terminal = EXCLUDED.is_terminal;

INSERT INTO app.permissions (code, name, description)
VALUES
  ('overview.view', 'Uebersicht ansehen', 'Erlaubt den Zugriff auf die nutzerbezogene Uebersicht.'),
  ('tasks.manage', 'Aufgaben verwalten', 'Aufgaben anlegen und bearbeiten.'),
  ('emails.assign', 'E-Mails zuordnen', 'Nicht zugeordnete E-Mails einem Vorgang zuordnen.'),
  ('delegations.manage', 'Vertretungen verwalten', 'Urlaubsvertretungen anlegen und bearbeiten.')
ON CONFLICT (code) DO UPDATE
SET
  name = EXCLUDED.name,
  description = EXCLUDED.description;

INSERT INTO app.role_permissions (role_id, permission_id)
SELECT roles.id, permissions.id
FROM app.roles
JOIN app.permissions ON permissions.code IN (
  'overview.view',
  'tasks.manage',
  'emails.assign',
  'delegations.manage'
)
WHERE roles.code = 'admin'
ON CONFLICT DO NOTHING;

INSERT INTO app.role_permissions (role_id, permission_id)
SELECT roles.id, permissions.id
FROM app.roles
JOIN app.permissions ON permissions.code IN (
  'overview.view',
  'tasks.manage',
  'emails.assign'
)
WHERE roles.code IN ('employee', 'sales')
ON CONFLICT DO NOTHING;

INSERT INTO app.email_accounts (display_name, email_address, provider)
VALUES ('das kuechenhaus Eingang', 'info@schober-daskuechenhaus.de', 'imap')
ON CONFLICT (email_address) DO UPDATE
SET
  display_name = EXCLUDED.display_name,
  provider = EXCLUDED.provider,
  is_active = TRUE;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tenant_daskuechenhaus_app') THEN
    GRANT USAGE ON SCHEMA app TO tenant_daskuechenhaus_app;
    GRANT USAGE ON SCHEMA audit TO tenant_daskuechenhaus_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app
      TO tenant_daskuechenhaus_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA audit
      TO tenant_daskuechenhaus_app;
    GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA app
      TO tenant_daskuechenhaus_app;
    GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA audit
      TO tenant_daskuechenhaus_app;
  END IF;
END;
$$;
