CREATE TABLE IF NOT EXISTS app.mobile_app_identities (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT REFERENCES app.users (id) ON DELETE SET NULL,
  apple_subject TEXT,
  expected_apple_email TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  first_seen_at TIMESTAMPTZ,
  last_login_at TIMESTAMPTZ,
  linked_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT mobile_app_identities_subject_not_blank CHECK (
    apple_subject IS NULL OR btrim(apple_subject) <> ''
  ),
  CONSTRAINT mobile_app_identities_expected_email_lowercase CHECK (
    expected_apple_email IS NULL OR expected_apple_email = lower(expected_apple_email)
  ),
  CONSTRAINT mobile_app_identities_expected_email_has_at CHECK (
    expected_apple_email IS NULL OR position('@' IN expected_apple_email) > 1
  ),
  CONSTRAINT mobile_app_identities_status_check CHECK (
    status IN ('pending', 'requested', 'active', 'revoked')
  ),
  CONSTRAINT mobile_app_identities_active_requires_user CHECK (
    status <> 'active' OR user_id IS NOT NULL
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS mobile_app_identities_apple_subject_key
  ON app.mobile_app_identities (apple_subject)
  WHERE apple_subject IS NOT NULL;

CREATE INDEX IF NOT EXISTS mobile_app_identities_expected_email_idx
  ON app.mobile_app_identities (expected_apple_email)
  WHERE expected_apple_email IS NOT NULL;

DROP TRIGGER IF EXISTS set_mobile_app_identities_updated_at
  ON app.mobile_app_identities;
CREATE TRIGGER set_mobile_app_identities_updated_at
BEFORE UPDATE ON app.mobile_app_identities
FOR EACH ROW
EXECUTE FUNCTION app.set_updated_at();

INSERT INTO app.mobile_app_identities (
  user_id,
  expected_apple_email,
  status
)
SELECT
  u.id,
  'konstantin@milonas.email',
  'pending'
FROM app.users u
WHERE u.email = 'k.milonas@schober-daskuechenhaus.de'
  AND NOT EXISTS (
    SELECT 1
    FROM app.mobile_app_identities existing
    WHERE existing.user_id = u.id
      AND existing.expected_apple_email = 'konstantin@milonas.email'
      AND existing.status <> 'revoked'
  );
