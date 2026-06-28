WITH target_user AS (
  SELECT id
  FROM app.users
  WHERE email = 'k.milonas@schober-daskuechenhaus.de'
    AND is_active = TRUE
  LIMIT 1
),
ensure_pending_invite AS (
  INSERT INTO app.mobile_app_identities (
    user_id,
    expected_apple_email,
    status
  )
  SELECT
    target_user.id,
    'konstantin@milonas.email',
    'pending'
  FROM target_user
  WHERE NOT EXISTS (
    SELECT 1
    FROM app.mobile_app_identities existing
    WHERE existing.user_id = target_user.id
      AND existing.expected_apple_email = 'konstantin@milonas.email'
      AND existing.status <> 'revoked'
  )
  RETURNING id
),
activate_requested_identity AS (
  UPDATE app.mobile_app_identities identity
  SET
    user_id = target_user.id,
    status = 'active',
    linked_at = COALESCE(identity.linked_at, now()),
    last_login_at = COALESCE(identity.last_login_at, now()),
    revoked_at = NULL
  FROM target_user
  WHERE identity.status = 'requested'
    AND identity.expected_apple_email = 'konstantin@milonas.email'
    AND identity.apple_subject IS NOT NULL
    AND NOT EXISTS (
      SELECT 1
      FROM app.mobile_app_identities active_identity
      WHERE active_identity.apple_subject = identity.apple_subject
        AND active_identity.status = 'active'
        AND active_identity.id <> identity.id
    )
  RETURNING identity.id
)
SELECT
  (SELECT count(*) FROM ensure_pending_invite) AS pending_invites_created,
  (SELECT count(*) FROM activate_requested_identity) AS requested_identities_activated;
