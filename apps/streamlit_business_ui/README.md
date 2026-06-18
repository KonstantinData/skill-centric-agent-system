# Streamlit Business UI

Tenant-aware operations dashboard for SCAS business steering. The first screen
loads tenant shell metadata, branding, landing configuration, role-derived
navigation, and launch dashboard cards from the active tenant record. It then
shows only the workspace tiles enabled by the current tenant roles. Tenant
admins additionally see users, roles, launch-critical settings, admin workflow
routes, and audit traceability status from the tenant context.

Tenants use `ui_profile.logo_path`, `ui_profile.landing`,
`ui_profile.theme`, and `ui_profile.workspace_areas` from their tenant registry
fixture for the first screen. The Daskuechenhaus tenant uses its tenant-local
logo at `assets/images/daskuechenhaus/logo_daskuechenhaus.png` and the
corporate colors `#fff`, `#111`, `#333`, and `#76b726`. Other tenants render
their own metadata and do not inherit tenant-specific logo, color, or copy when
their fixture lacks those UI profile fields.
The landing dashboard summarizes tenant authority, visible workspace routes,
tenant-scoped data sources, and admin governance state without exposing private
owner data or legal/tax details.

When `SCAS_CONTROL_API_URL` and `SCAS_TENANT_ADMIN_TOKEN` are set, the UI loads
the tenant admin context from `GET /tenant-admin/tenants/{tenant_id}` instead of
inventing local permissions. Repository fixtures are only a local contract
verification source; production must use the Control API path and authenticated
tenant session context.

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
tenant-specific navigation, landing dashboard states, admin/non-admin
separation, admin workflow routes, required labels, and the authenticated
session gate. It is intentionally dependency-free until the repository adds a
browser E2E or accessibility harness.

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
