-- 0004_mail_import_state.sql
-- What: Add incremental IMAP import bookkeeping and message deduplication.
-- Why: The Hetzner-only mail importer needs per-account UID tracking and a
--      stable dedup key so re-runs never insert the same message twice.
-- Where: tenant_daskuechenhaus PostgreSQL, schema app.

ALTER TABLE app.email_accounts
  ADD COLUMN IF NOT EXISTS import_folder TEXT NOT NULL DEFAULT 'INBOX',
  ADD COLUMN IF NOT EXISTS import_uidvalidity BIGINT,
  ADD COLUMN IF NOT EXISTS last_imported_uid BIGINT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_imported_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_import_status TEXT,
  ADD COLUMN IF NOT EXISTS last_import_error TEXT;

ALTER TABLE app.email_messages
  ADD COLUMN IF NOT EXISTS imap_uid BIGINT,
  ADD COLUMN IF NOT EXISTS body_text TEXT;

-- Deduplicate inbound mail per mailbox on the IMAP Message-ID. The importer
-- always sets external_message_id (synthesizing a stable id when the header is
-- missing), so this partial unique index guards every imported row.
CREATE UNIQUE INDEX IF NOT EXISTS email_messages_account_external_id_key
  ON app.email_messages (email_account_id, external_message_id)
  WHERE external_message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS email_messages_imap_uid_idx
  ON app.email_messages (email_account_id, imap_uid);

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
