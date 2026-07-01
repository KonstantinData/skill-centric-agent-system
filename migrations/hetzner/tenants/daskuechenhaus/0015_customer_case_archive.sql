ALTER TABLE app.customer_cases
  ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS archived_by_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS archive_note TEXT;

CREATE INDEX IF NOT EXISTS customer_cases_archive_idx
  ON app.customer_cases (customer_id, case_status, archived_at DESC)
  WHERE is_active = TRUE;
