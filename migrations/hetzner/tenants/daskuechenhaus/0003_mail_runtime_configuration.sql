ALTER TABLE app.email_accounts
  ADD COLUMN IF NOT EXISTS assigned_user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS imap_host_secret_ref TEXT,
  ADD COLUMN IF NOT EXISTS imap_port_secret_ref TEXT,
  ADD COLUMN IF NOT EXISTS imap_username_secret_ref TEXT,
  ADD COLUMN IF NOT EXISTS imap_password_secret_ref TEXT,
  ADD COLUMN IF NOT EXISTS smtp_host_secret_ref TEXT,
  ADD COLUMN IF NOT EXISTS smtp_port_secret_ref TEXT,
  ADD COLUMN IF NOT EXISTS smtp_username_secret_ref TEXT,
  ADD COLUMN IF NOT EXISTS smtp_password_secret_ref TEXT,
  ADD COLUMN IF NOT EXISTS from_address_secret_ref TEXT;

CREATE INDEX IF NOT EXISTS email_accounts_assigned_user_idx
  ON app.email_accounts (assigned_user_id, is_active);

UPDATE app.email_accounts
SET
  assigned_user_id = NULL,
  imap_host_secret_ref = NULL,
  imap_port_secret_ref = NULL,
  imap_username_secret_ref = NULL,
  imap_password_secret_ref = NULL,
  smtp_host_secret_ref = NULL,
  smtp_port_secret_ref = NULL,
  smtp_username_secret_ref = NULL,
  smtp_password_secret_ref = NULL,
  from_address_secret_ref = NULL
WHERE email_address = 'info@schober-daskuechenhaus.de'
  AND (
    imap_username_secret_ref = 'DKH_MAIL_K_MILONAS_IMAP_USERNAME'
    OR smtp_username_secret_ref = 'DKH_MAIL_K_MILONAS_SMTP_USERNAME'
  );

INSERT INTO app.email_accounts (display_name, email_address, provider)
VALUES ('Konstantin Milonas', 'k.milonas@schober-daskuechenhaus.de', 'imap')
ON CONFLICT (email_address) DO UPDATE
SET
  display_name = EXCLUDED.display_name,
  provider = EXCLUDED.provider,
  is_active = TRUE;

UPDATE app.email_accounts account
SET
  assigned_user_id = sales_user.id,
  imap_host_secret_ref = 'DKH_EMAIL_IMAP_HOST',
  imap_port_secret_ref = 'DKH_EMAIL_IMAP_PORT',
  imap_username_secret_ref = 'DKH_MAIL_K_MILONAS_IMAP_USERNAME',
  imap_password_secret_ref = 'DKH_MAIL_K_MILONAS_IMAP_PASSWORD',
  smtp_host_secret_ref = 'DKH_EMAIL_SMTP_HOST',
  smtp_port_secret_ref = 'DKH_EMAIL_SMTP_PORT',
  smtp_username_secret_ref = 'DKH_MAIL_K_MILONAS_SMTP_USERNAME',
  smtp_password_secret_ref = 'DKH_MAIL_K_MILONAS_SMTP_PASSWORD',
  from_address_secret_ref = 'DKH_MAIL_K_MILONAS_FROM_ADDRESS'
FROM (
  SELECT u.id
  FROM app.users u
  JOIN app.user_roles ur ON ur.user_id = u.id
  JOIN app.roles r ON r.id = ur.role_id
  WHERE lower(u.email) = 'k.milonas@schober-daskuechenhaus.de'
    AND r.code = 'sales'
  ORDER BY u.id
  LIMIT 1
) sales_user
WHERE account.email_address = 'k.milonas@schober-daskuechenhaus.de';

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
