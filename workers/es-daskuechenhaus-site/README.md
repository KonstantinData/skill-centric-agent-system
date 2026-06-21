# es-daskuechenhaus.de protected site

Cloudflare Worker serving the internal `es-daskuechenhaus.de` website.

Routes:

- `/index.php`: protected user-specific CRM steering surface. It surfaces the
  decision queue, customer progress, SCAS approval queue, operational workload,
  and audit trail before lower-priority context. The page includes the tenant
  command center with global customer/case search entry points, quick actions,
  and the visible SCAS human-confirmation status.
- `/aufgaben.php`: protected task and email work surface. Tasks can be created,
  edited, archived, or moved to the soft-delete trash. Emails can be manually
  assigned to customer cases, archived, or moved to the soft-delete trash.
- `/kunden.php`: protected customer work surface. Customers can be created and
  edited against Hetzner PostgreSQL. Duplicate names and duplicate email
  addresses are allowed; only a non-null customer number is unique. A first
  customer case can be created together with the customer. The command center
  search can filter the customer list via `/kunden.php?q=...`.
- `/admin.php`: protected admin area for users, roles, workdays, integrations,
  and settings. The page renders live data from the Hetzner tenant runtime API.
- `/admin-api/*`: protected Worker proxy for admin form submissions. The Worker
  forwards to the Hetzner-only runtime API and stores no tenant runtime data.
- `/overview-api/*`: protected Worker proxy for CRM form submissions such
  as task creation/editing, task lifecycle actions, manual email-to-case
  assignment, human confirmation of email assignment suggestions, and email
  lifecycle actions.
- `/customers-api/*`: protected Worker proxy for customer creation and editing.
  The Worker forwards to the Hetzner-only runtime API and stores no tenant
  runtime data.

The site is intentionally not designed for public anonymous access. Production
deployment must be paired with a Cloudflare Access self-hosted application and
an Allow policy scoped to explicit Daskuechenhaus operators.

Tenant UI assets and theme tokens are loaded from the Daskuechenhaus tenant UI
profile embedded in the Worker. The protected app serves the tenant-owned logo
only from `/tenant-assets/daskuechenhaus/logo.svg`; the tenant registry still
points at the canonical source asset
`assets/images/daskuechenhaus/logo_daskuechenhaus.png`. Unknown
`/tenant-assets/*` paths return `404`, and the Worker does not fall back to
assets from another tenant.

Runtime data remains in Hetzner PostgreSQL `tenant_daskuechenhaus`. The Worker
requires `DKH_ADMIN_API_TOKEN` as a secret and uses
`DKH_ADMIN_API_BASE_URL` from `wrangler.toml`.

Task and email attachment files remain on Hetzner runtime storage. PostgreSQL
stores only metadata and paths for overview attachments.

Email assignment suggestions may be produced by an agent or skill, but they are
not applied automatically. The CRM surface requires a human operator to confirm
the suggested assignment. If the suggestion is not useful, the operator searches
for the correct customer case and assigns it manually.

SCAS-supported CRM actions write audit evidence to Hetzner runtime storage via
`app.communication_events`. For confirmed email-assignment suggestions this
includes tenant ID, principal context, role/scope context, skill-pack ID,
selected module IDs, validator results, confirmation status, and action result.

Personalized mailbox credentials are synced by
`.github/workflows/es-daskuechenhaus-mail-runtime-sync.yml` to
`/etc/daskuechenhaus/mail.env` on Hetzner. Cloudflare receives no mail
credentials; PostgreSQL stores only secret reference names for each mailbox.

Local checks:

```powershell
npm run dkh-site:typecheck
npm run dkh-site:check
python -m pytest tests/test_cloudflare_control_api_scaffold.py tests/test_daskuechenhaus_admin_area_schema.py tests/test_daskuechenhaus_admin_runtime_api.py
python -m pytest tests/test_daskuechenhaus_crm_ui_quality_gate.py tests/test_daskuechenhaus_overview_actions_schema.py
```
