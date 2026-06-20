# es-daskuechenhaus.de Protected Site

This runbook describes the protected Cloudflare Worker site for
`es-daskuechenhaus.de` and `www.es-daskuechenhaus.de`.

The Worker serves `/index.php` as the protected user-specific overview and
`/admin.php` as the protected admin area. Both paths rely on the same
Cloudflare Access protection at the hostname level.

The overview and admin area read and write runtime data through a Hetzner-local API:

```text
Browser -> Cloudflare Access -> es-daskuechenhaus-site Worker
Worker /admin-api/* and /overview-api/* proxy
  -> daskuechenhaus.condata.io/_daskuechenhaus-admin-api/*
Hetzner Nginx -> 127.0.0.1:8715 -> tenant_daskuechenhaus PostgreSQL
```

Cloudflare stores no Daskuechenhaus runtime, admin, task, email, or attachment
data. The Worker only renders pages and forwards authenticated requests to
Hetzner.

## Security Model

- `es-daskuechenhaus.de` and `www.es-daskuechenhaus.de` are not public websites.
- Cloudflare Access must protect the hostname before the Worker is deployed.
- The Access application uses an allow policy for explicit email identities.
- Admin form requests require the Worker secret `DKH_ADMIN_API_TOKEN`.
- The Hetzner API additionally checks the forwarded Access email against the
  tenant admin allow list.
- `app.users.email` is not unique. The admin UI treats each row as a separate
  employee or role entry identified by `app.users.id`, so the same person and
  email can appear more than once with different roles.
- `/index.php` is loaded through the authenticated user's scope. The Hetzner API
  calculates visible user IDs from the Access email, active delegations, and
  independent admin rights; UI filtering is not the source of authorization.
- Task attachments are accepted only for PDF, JPG, PNG, and XLSX and are stored
  under `/var/lib/daskuechenhaus/uploads` on Hetzner. PostgreSQL stores
  attachment metadata and the storage path.
- The deploy workflow refuses production mutation when no allowed email is
  provided.
- The deploy workflow performs an anonymous HTTP check after deploy and fails if
  the site returns `200` without Access.

## Required GitHub Secrets

The protected site deploy workflow reads these repository or environment
secrets:

- `DKH_CLOUDFLARE_ACCOUNT_ID`
- `DKH_CLOUDFLARE_ZONE_ID`
- `DKH_CLOUDFLARE_API_TOKEN`
- `DKH_ADMIN_API_TOKEN`

The token must be scoped to the `es-daskuechenhaus.de` zone and must allow
Cloudflare Access app/policy management, DNS record management, and Worker
deployment for the account.

`DKH_ADMIN_API_TOKEN` must match `/etc/daskuechenhaus/admin-api-token` on the
Hetzner host. Set it with:

```powershell
ssh root@178.105.62.169 'cat /etc/daskuechenhaus/admin-api-token' | npx wrangler secret put DKH_ADMIN_API_TOKEN --config workers/es-daskuechenhaus-site/wrangler.toml
```

The mail runtime sync workflow reads these GitHub secrets and writes their
values only to Hetzner, not to Cloudflare:

- `DKH_EMAIL_IMAP_HOST`
- `DKH_EMAIL_IMAP_PORT`
- `DKH_EMAIL_SMTP_HOST`
- `DKH_EMAIL_SMTP_PORT`
- `DKH_MAIL_K_MILONAS_IMAP_USERNAME`
- `DKH_MAIL_K_MILONAS_IMAP_PASSWORD`
- `DKH_MAIL_K_MILONAS_SMTP_USERNAME`
- `DKH_MAIL_K_MILONAS_SMTP_PASSWORD`
- `DKH_MAIL_K_MILONAS_FROM_ADDRESS`

The workflow also needs the existing Hetzner SSH secrets. It resolves the
production-scoped names first and falls back to the legacy unscoped names:

- `SCAS_PROD_HETZNER_HOST` or `HETZNER_HOST`
- `SCAS_PROD_HETZNER_USER` or `HETZNER_USER`
- `SCAS_PROD_HETZNER_SSH_KEY` or `HETZNER_SSH_KEY`

The mail sync target is `/etc/daskuechenhaus/mail.env`, owned by `root` and
readable by the `tenant_daskuechenhaus_app` group. PostgreSQL stores only
secret reference names on `app.email_accounts`, never the credential values.

## Hetzner Runtime API

The API service is versioned in:

- `scripts/hetzner/daskuechenhaus_admin_api.py`
- `scripts/hetzner/daskuechenhaus-admin-api.service`

The service runs as `tenant_daskuechenhaus_app`, binds only
`127.0.0.1:8715`, and uses PostgreSQL peer authentication against
`tenant_daskuechenhaus`. Nginx exposes only the HTTPS proxy path
`/_daskuechenhaus-admin-api/`.

The API exposes:

- `GET /admin/state`
- `POST /admin/users`
- `POST /admin/users/{id}`
- `POST /admin/users/{id}/roles`
- `POST /admin/users/{id}/workdays`
- `POST /admin/company-settings`
- `POST /admin/integrations`
- `GET /overview/state`
- `POST /overview/tasks`
- `POST /overview/emails/assign`

The overview data model is created by
`migrations/hetzner/tenants/daskuechenhaus/0002_overview_workspace.sql`.
It adds operational tables for customer case references, tasks, assignments,
attachments, reminders, appointments, news, goals, email messages, email-case
links, assignment suggestions, communication events, absences, delegations, and
delegated action audit records.

The first mailbox runtime mapping is created by
`migrations/hetzner/tenants/daskuechenhaus/0003_mail_runtime_configuration.sql`.
It adds secret-reference columns to `app.email_accounts` and maps the
`k.milonas@schober-daskuechenhaus.de` mailbox configuration to the operative
`sales` user row. Admin-only user rows do not receive customer-case mailbox
ownership.

Smoke checks:

```bash
systemctl is-active daskuechenhaus-admin-api.service
curl -i https://daskuechenhaus.condata.io/_daskuechenhaus-admin-api/admin/state
TOKEN=$(cat /etc/daskuechenhaus/admin-api-token)
curl -fsS \
  -H "x-dkh-admin-api-token: $TOKEN" \
  -H "x-access-user-email: k.milonas@schober-daskuechenhaus.de" \
  https://daskuechenhaus.condata.io/_daskuechenhaus-admin-api/admin/state
curl -fsS \
  -H "x-dkh-admin-api-token: $TOKEN" \
  -H "x-access-user-email: k.milonas@schober-daskuechenhaus.de" \
  https://daskuechenhaus.condata.io/_daskuechenhaus-admin-api/overview/state
```

The unauthenticated request must return `401`. The authenticated request must
return PostgreSQL-backed admin and overview data.

## Mail Importer (Hetzner-only)

Inbound mail appears on `index.php` only after it is imported into PostgreSQL.
The importer is Hetzner-local and never touches Cloudflare:

```text
IMAP mailbox -> daskuechenhaus_mail_importer.py (on Hetzner)
  -> app.email_messages / app.email_participants / app.email_attachments
  -> /var/lib/daskuechenhaus/uploads/emails/<message_id>/ (attachments)
```

The importer is versioned in:

- `scripts/hetzner/daskuechenhaus_mail_importer.py`
- `scripts/hetzner/daskuechenhaus-mail-importer.service`
- `scripts/hetzner/daskuechenhaus-mail-importer.timer`

It reads credential values only from `/etc/daskuechenhaus/mail.env`. PostgreSQL
stores secret reference names on `app.email_accounts`; the importer resolves each
reference (`imap_host_secret_ref`, `imap_port_secret_ref`,
`imap_username_secret_ref`, `imap_password_secret_ref`) against the env file. No
credential value is ever written to PostgreSQL or logged.

Import behaviour:

- Connects per active mailbox (IMAP4 over SSL on 993, STARTTLS on 143).
- Selects the folder read-only, so server-side `\Seen` flags are not changed.
- Fetches incrementally with `UID n:*` from `last_imported_uid + 1` and resets to
  UID 1 when the IMAP `UIDVALIDITY` changes.
- Deduplicates on `(email_account_id, external_message_id)`; the Message-ID is
  used, or a stable synthetic id when the header is missing.
- Stores attachments under `/var/lib/daskuechenhaus/uploads/emails/<message_id>/`
  and writes metadata into `app.email_attachments`.
- Imported mail stays `is_unassigned = TRUE`; case assignment remains a manual
  (`POST /overview/emails/assign`) or later automatic step.

The import-state columns and the dedup index are created by
`migrations/hetzner/tenants/daskuechenhaus/0004_mail_import_state.sql`.

Install (run after `/etc/daskuechenhaus/mail.env` and migration `0003` exist):

```bash
sudo install -d -o tenant_daskuechenhaus_app -g tenant_daskuechenhaus_app \
  /opt/daskuechenhaus/mail-importer
sudo install -o root -g root -m 0644 \
  daskuechenhaus_mail_importer.py /opt/daskuechenhaus/mail-importer/app.py
sudo -u postgres psql -d tenant_daskuechenhaus -v ON_ERROR_STOP=1 \
  -f 0004_mail_import_state.sql
sudo install -o root -g root -m 0644 \
  daskuechenhaus-mail-importer.service /etc/systemd/system/
sudo install -o root -g root -m 0644 \
  daskuechenhaus-mail-importer.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now daskuechenhaus-mail-importer.timer
```

Smoke checks:

```bash
# One manual pass without writing (connect + report only):
sudo -u tenant_daskuechenhaus_app \
  DKH_MAIL_ENV_FILE=/etc/daskuechenhaus/mail.env \
  python3 /opt/daskuechenhaus/mail-importer/app.py --once --dry-run --verbose

# Trigger a real run and inspect import state:
sudo systemctl start daskuechenhaus-mail-importer.service
journalctl -u daskuechenhaus-mail-importer.service --no-pager -n 50
sudo -u postgres psql -d tenant_daskuechenhaus -c \
  "SELECT email_address, last_imported_uid, last_import_status, last_imported_at \
   FROM app.email_accounts WHERE imap_username_secret_ref IS NOT NULL;"
```

After a successful run, `/overview/state` returns the imported messages and they
appear in the E-Mail-Eingänge panel on `index.php`.

## Local Checks

Run the focused checks before creating a pull request:

```powershell
npm run dkh-site:typecheck
npm run dkh-site:check
python -m pytest tests/test_github_actions_workflows.py tests/test_cloudflare_control_api_scaffold.py tests/test_daskuechenhaus_admin_area_schema.py tests/test_daskuechenhaus_admin_runtime_api.py tests/test_daskuechenhaus_mail_importer.py
```

## Plan-Only Workflow Run

Use the manual workflow with `apply_deploy=false` to validate secrets and build
the Worker without mutating Cloudflare.

Required input:

- `allowed_emails`: comma-separated list of users who may access the site after
  production apply.

Use the manual `es-daskuechenhaus.de Mail Runtime Sync` workflow with
`apply_sync=false` to validate mail and Hetzner secrets without writing runtime
configuration.

## Production Apply

Only run with production mutation after the allowed user list has been reviewed:

- `allowed_emails`: one or more allowed identities
- `apply_deploy`: `true`
- `confirm_production`: `true`

The workflow configures Cloudflare Access and DNS for both hostnames first,
deploys the Worker second, and then verifies that anonymous access is blocked
on both hostnames.

Run the mail runtime sync workflow with:

- `apply_sync`: `true`
- `confirm_production`: `true`

This writes `/etc/daskuechenhaus/mail.env` on Hetzner and applies the
mailbox-reference migration to `tenant_daskuechenhaus`.

## Rollback

If the Worker deployment must be removed, delete the Worker route or Worker
deployment in Cloudflare. Keep the Access application in place until the route
is verified as unreachable.
