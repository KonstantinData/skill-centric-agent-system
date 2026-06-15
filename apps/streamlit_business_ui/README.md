# Streamlit Business UI

Tenant-aware operations dashboard for SCAS business steering. The first screen
loads tenant shell metadata and role-derived UI areas, then shows only the
workspace tiles enabled by the current tenant roles.

When `SCAS_CONTROL_API_URL` and `SCAS_TENANT_ADMIN_TOKEN` are set, the UI loads
the tenant admin context from `GET /tenant-admin/tenants/{tenant_id}` instead of
inventing local permissions. Repository fixtures are only a local contract
verification source; production must use the Control API path.

`SCAS_UI_ROLE_IDS` can provide comma-separated tenant role IDs for local contract
verification. Unknown role IDs are ignored and the UI falls back to the
tenant's non-admin role set; users cannot grant themselves admin access through
the UI.

## Run

```powershell
python -m pip install -e ".[ui]"
streamlit run apps\streamlit_business_ui\app.py
```

Optional backend-backed mode:

```powershell
$env:SCAS_CONTROL_API_URL="https://<control-api-worker>"
$env:SCAS_TENANT_ADMIN_TOKEN="<tenant-admin-token>"
$env:SCAS_UI_ROLE_IDS="liquisto-researcher"
streamlit run apps\streamlit_business_ui\app.py
```

The repository-local Streamlit config in `.streamlit/config.toml` sets
`server.headless = false` so the browser opens automatically on local start.
