# Streamlit Business UI

Tenant-aware operations dashboard for SCAS business steering. After
authentication, the first screen loads tenant branding and role-derived
navigation from the active tenant record, then shows only the workspace tiles
enabled by the current tenant roles. Internal tenant identifiers, setup status,
hostnames, role names, data-source names, admin routes, and audit/settings
diagnostics are not rendered on the user-facing landing page.

Tenants use `ui_profile.logo_path`, `ui_profile.theme`, and
`ui_profile.workspace_areas` from their tenant registry fixture for the first
screen. The Daskuechenhaus tenant uses its tenant-local logo at
`assets/images/daskuechenhaus/logo_daskuechenhaus.png` and the corporate colors
`#fff`, `#111`, `#333`, and `#76b726`. The theme CSS also pins Streamlit's
header menu button to tenant foreground/background colors so it remains visible
in light and dark browser modes. Other tenants render their own metadata and do
not inherit tenant-specific logo, color, or copy when their fixture lacks those
UI profile fields.

When `SCAS_CONTROL_API_URL` and `SCAS_TENANT_ADMIN_TOKEN` are set, the UI loads
the tenant admin context from `GET /tenant-admin/tenants/{tenant_id}` instead of
inventing local permissions. Repository fixtures are only a local contract
verification source; production must use the Control API path and authenticated
tenant session context.

For Daskuechenhaus customer case management, set
`SCAS_CUSTOMER_CASES_API_URL` to the Daskuechenhaus case Worker base URL and
`SCAS_CUSTOMER_CASES_API_SECRET` to the matching Worker bearer token. The UI
uses `GET /tenant-cases` for the case list and `POST /tenant-cases` with
`X-Actor` derived from the tenant session when creating a new case.

The Daskuechenhaus `Übersicht` view is the status page. It uses
`Status filtern` with `Meine Ereignisse` as the default so the signed-in user
first sees the events assigned to them; `Alle Ereignisse` can be selected for a
tenant-wide status view. The page renders the 10 status phases as tiles and
uses the selected tile only as a filter over the same case database. A tile may
show only:

- phase number,
- phase name,
- case count,
- an attention marker when at least one case in that phase needs action.

Customer names, task details, appointments, budgets, responsible users, and
agent hints must not be rendered inside the phase tiles. Those details belong
to the filtered case list and later case detail views.

The Daskuechenhaus workflow uses centered dialogs for creating and editing
customer cases. The create dialog uses German labels and separates private and
company customers: `Kundentyp`, `CARAT-Auftrags-Nr.`, `Anrede`, `Nachname`,
`Vorname`, `Firma`, `Name 2`, `Name 3`, `Name 4`, `USt-ID`, `Steuernummer`,
`Telefon`, `Mobil`, `E-Mail`, `ISO Länder Code`, `PLZ`, `Ort`, `NATO`,
`Abweichende MwSt.`, `MwSt. Auswahl`, `Umkehr der Steuerschuldnerschaft`,
`Werbezusendung erlaubt`, `E-Rechnung`, and `Priorität`.

`Kunden-Nr.` and `Vorgangs-Nr.` are assigned by the system during create. The
edit dialog lets users update the Vorgang fields such as status phase,
priority, status, responsible user, CARAT order number, and attention marker.
For editing an existing case, the UI must not use a broad dropdown over all
phase cases. Users filter the selected phase by last name or CARAT order number,
mark exactly one filtered case with a checkbox, and then open
`Ausgewählten Vorgang bearbeiten`.

`SCAS_UI_ROLE_IDS` can provide comma-separated tenant role IDs for local contract
verification. Unknown role IDs are ignored and the UI falls back to the
tenant's non-admin role set. In authenticated mode, `SCAS_UI_ROLE_IDS` is ignored
for authority; visible areas and admin access derive from the validated session
role IDs.

`SCAS_UI_TENANT_ID` binds the UI to one server-controlled tenant. Production and
other authenticated deployments must set it, for example `liquisto`, so the app
loads only that tenant and does not render a tenant selector. When it is omitted,
the tenant selector is available only for local fixture-mode contract checks.

## Authentication Modes

Local fixture mode is the default:

```powershell
$env:SCAS_UI_AUTH_MODE="fixture"
$env:SCAS_UI_ROLE_IDS="liquisto-researcher"
streamlit run apps\streamlit_business_ui\app.py
```

Production-style mode is fail-closed and requires session context:

```powershell
$env:SCAS_UI_AUTH_MODE="required"
$env:SCAS_UI_TENANT_ID="liquisto"
$env:SCAS_UI_SESSION_CONTEXT_JSON='{"tenant_id":"liquisto","principal_id":"<principal-id>","membership_id":"<membership-id>","role_ids":["liquisto-owner"]}'
$env:SCAS_UI_UPSTREAM_AUTH_TRUSTED="true"
streamlit run apps\streamlit_business_ui\app.py
```

If authentication is already enforced by a trusted reverse proxy or identity
boundary, set `SCAS_UI_UPSTREAM_AUTH_TRUSTED=true` and provide the same
`SCAS_UI_SESSION_CONTEXT_JSON`. Do not set this flag on a publicly reachable
service unless the upstream layer blocks unauthenticated requests and injects
only server-controlled session context.

Local login mode renders an actual username/password form in the Streamlit UI
and validates passwords against PBKDF2 hashes stored in
`SCAS_UI_LOGIN_USERS_JSON`. The login form is a standalone unauthenticated page:
the tenant operations sidebar and navigation are not rendered until a session is
created, and the login page is hidden again until the user logs out.
After login, sidebar navigation uses Streamlit buttons and session state rather
than plain page links. The dashboard sidebar intentionally shows only
`Übersicht` plus `Admin Center` for sessions with the `tenant-admin`
capability; non-admin sessions do not see the admin entry.
When `SCAS_UI_PASSWORD_RESET_URL` is configured, the login page shows a
`Passwort vergessen?` link to the approved reset flow. Without that URL, it
shows an administrator-contact fallback instead of pretending that self-service
reset is available.

```powershell
$env:SCAS_UI_AUTH_MODE="local-login"
$env:SCAS_UI_TENANT_ID="daskuechenhaus"
$env:SCAS_UI_LOGIN_USERS_JSON='[{"username":"<login-name>","tenant_id":"daskuechenhaus","principal_id":"<principal-id>","membership_id":"tm-daskuechenhaus-admin-01","role_ids":["daskuechenhaus-admin"],"password_hash":"pbkdf2_sha256$600000$<salt>$<hash>"}]'
streamlit run apps\streamlit_business_ui\app.py
```

Optionally set `SCAS_UI_PASSWORD_RESET_URL` to an approved HTTPS reset page.

Generate a password hash locally without storing the password in repository
files:

```powershell
@'
from apps.streamlit_business_ui.app import encode_login_password_hash
print(encode_login_password_hash("replace-with-one-time-password"))
'@ | python -
```

Store `SCAS_UI_LOGIN_USERS_JSON` only in the environment-specific secret store.
Do not commit login names, password hashes, raw passwords, or provider user IDs.
Automated self-service password reset requires a trusted delivery path, usually
an identity provider or mail provider that can send one-time reset links. Manual
administrator password resets do not require SMTP access.

The `Admin Center` includes a password-change helper for local-login mode.
It generates a new PBKDF2 password hash for the selected username. The UI does
not write secrets or host environment files itself; the generated hash must be
copied into the environment-specific `SCAS_UI_LOGIN_USERS_JSON` secret and then
deployed through the tenant UI deployment workflow.

The first Admin Center slice mirrors the CentralStationCRM settings structure
for tenant operators: account metadata, users and rights, admin workflows,
data sources and integrations, security/audit state, and a trash/retention
placeholder. It is intentionally read-only except for generating local password
hashes. Tenant PostgreSQL provisioning, API keys, webhook secrets, integration
credentials, restore actions, and permanent deletions stay backend-governed and
audited outside the Streamlit UI.

When `SCAS_UI_AUTH_MODE=required` and no trusted session is available, the UI
can render a tenant-branded login entry by setting `SCAS_UI_LOGIN_URL` to the
approved upstream identity URL. Streamlit still does not authenticate users or
store credentials; successful access requires the upstream layer to inject the
validated tenant session context.

## Run

```powershell
python -m pip install -e ".[ui]"
streamlit run apps\streamlit_business_ui\app.py
```

Optional backend-backed mode:

```powershell
$env:SCAS_CONTROL_API_URL="https://<control-api-worker>"
$env:SCAS_TENANT_ADMIN_TOKEN="<tenant-admin-token>"
$env:SCAS_CUSTOMER_CASES_API_URL="https://daskuechenhaus-control-api.<account>.workers.dev"
$env:SCAS_CUSTOMER_CASES_API_SECRET="<customer-cases-api-secret>"
$env:SCAS_UI_AUTH_MODE="required"
$env:SCAS_UI_TENANT_ID="liquisto"
$env:SCAS_UI_SESSION_CONTEXT_JSON='{"tenant_id":"liquisto","principal_id":"<principal-id>","membership_id":"<membership-id>","role_ids":["liquisto-researcher"]}'
$env:SCAS_UI_UPSTREAM_AUTH_TRUSTED="true"
streamlit run apps\streamlit_business_ui\app.py
```

The repository-local Streamlit config in `.streamlit/config.toml` sets
`server.headless = false` so the browser opens automatically on local start.

## Smoke Checks

The local launch smoke path is covered by:

```powershell
python -m pytest tests/test_streamlit_business_ui.py
```

The suite verifies tenant hostname selection, tenant-bound production mode,
role-derived workspace visibility, metadata-derived branding and theme CSS,
tenant-specific navigation, hidden internal landing-page metadata, required
labels, and the authenticated session gate. It is intentionally dependency-free
until the repository adds a browser E2E or accessibility harness.

## Deployment Status

As of 2026-06-16, the repository defines a production-safe deployment path for
the Streamlit Business UI:

- container definition: `deploy/streamlit-business-ui/Dockerfile`
- manual workflow: `.github/workflows/tenant-ui-deploy.yml`
- runbook: `docs/runbooks/streamlit-business-ui-deployment.md`

The workflow defaults to build-only plan mode and does not mutate the remote
host unless `apply_deploy=true`. Production apply also requires
`confirm_production=true`, target-environment Hetzner secrets, fixed
`SCAS_UI_TENANT_ID`, a server-owned session context secret, a tenant admin token
secret, and an `upstream_auth_evidence_url` proving the approved authentication
boundary. The public hostname remains `not-production-ready` until the live
tenant launch gates in `docs/runbooks/liquisto-tenant-release-gate.md` pass.
