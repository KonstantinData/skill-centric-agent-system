# Streamlit Business UI

Tenant-aware operations dashboard for SCAS business steering. The first screen
loads tenant shell metadata and role-derived UI areas, then shows only the
workspace tiles enabled by the current tenant roles. Tenant admins additionally
see users, roles, launch-critical settings, admin workflow routes, and audit
traceability status from the tenant context.

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
$env:SCAS_UI_SESSION_CONTEXT_JSON='{"tenant_id":"liquisto","principal_id":"<principal-id>","membership_id":"<membership-id>","role_ids":["liquisto-owner"]}'
$env:SCAS_UI_UPSTREAM_AUTH_TRUSTED="true"
streamlit run apps\streamlit_business_ui\app.py
```

If authentication is already enforced by a trusted reverse proxy or identity
boundary, set `SCAS_UI_UPSTREAM_AUTH_TRUSTED=true` and provide the same
`SCAS_UI_SESSION_CONTEXT_JSON`. Do not set this flag on a publicly reachable
service unless the upstream layer blocks unauthenticated requests and injects
only server-controlled session context.

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

The suite verifies tenant hostname selection, role-derived workspace visibility,
admin/non-admin separation, admin workflow routes, required labels, and the
authenticated session gate. It is intentionally dependency-free until the
repository adds a browser E2E or accessibility harness.

## Deployment Status

As of 2026-06-16, the repository defines a production-safe deployment path for
the Streamlit Business UI:

- container definition: `deploy/streamlit-business-ui/Dockerfile`
- manual workflow: `.github/workflows/tenant-ui-deploy.yml`
- runbook: `docs/runbooks/streamlit-business-ui-deployment.md`

The workflow defaults to build-only plan mode and does not mutate the remote
host unless `apply_deploy=true`. Production apply also requires
`confirm_production=true`, target-environment Hetzner secrets, a server-owned
session context secret, a tenant admin token secret, and an
`upstream_auth_evidence_url` proving the approved authentication boundary. The
public hostname remains `not-production-ready` until the live tenant launch
gates in `docs/runbooks/liquisto-tenant-release-gate.md` pass.
