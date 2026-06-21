# es-daskuechenhaus.de protected site

Cloudflare Worker serving the internal `es-daskuechenhaus.de` website.

Routes:

- `/index.php`: protected user-specific cockpit for open tasks, email inbox
  assignments, appointments, news, goals, and active delegations. Tasks can be
  created, edited, archived, or moved to the soft-delete trash. Emails can be
  manually assigned to customer cases, archived, or moved to the soft-delete
  trash.
- `/admin.php`: protected admin area for users, roles, workdays, integrations,
  and settings. The page renders live data from the Hetzner tenant runtime API.
- `/admin-api/*`: protected Worker proxy for admin form submissions. The Worker
  forwards to the Hetzner-only runtime API and stores no tenant runtime data.
- `/overview-api/*`: protected Worker proxy for cockpit form submissions such
  as task creation/editing, task lifecycle actions, manual email-to-case
  assignment, human confirmation of email assignment suggestions, and email
  lifecycle actions.

The site is intentionally not designed for public anonymous access. Production
deployment must be paired with a Cloudflare Access self-hosted application and
an Allow policy scoped to explicit Daskuechenhaus operators.

Runtime data remains in Hetzner PostgreSQL `tenant_daskuechenhaus`. The Worker
requires `DKH_ADMIN_API_TOKEN` as a secret and uses
`DKH_ADMIN_API_BASE_URL` from `wrangler.toml`.

Task and email attachment files remain on Hetzner runtime storage. PostgreSQL
stores only metadata and paths for overview attachments.

Email assignment suggestions may be produced by an agent or skill, but they are
not applied automatically. The cockpit requires a human operator to confirm the
suggested assignment. If the suggestion is not useful, the operator searches for
the correct customer case and assigns it manually.

Personalized mailbox credentials are synced by
`.github/workflows/es-daskuechenhaus-mail-runtime-sync.yml` to
`/etc/daskuechenhaus/mail.env` on Hetzner. Cloudflare receives no mail
credentials; PostgreSQL stores only secret reference names for each mailbox.

Local checks:

```powershell
npm run dkh-site:typecheck
npm run dkh-site:check
python -m pytest tests/test_cloudflare_control_api_scaffold.py tests/test_daskuechenhaus_admin_area_schema.py tests/test_daskuechenhaus_admin_runtime_api.py
```
