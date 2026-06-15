# Streamlit Business UI

Tenant-aware executive dashboard for SCAS business steering. The first screen
loads tenant shell metadata from `examples/tenants/*.json` and shows hostname,
status, admin routes, roles, data sources, and isolation posture before the KPI
views.

## Run

```powershell
python -m pip install -e ".[ui]"
streamlit run apps\streamlit_business_ui\app.py
```

The repository-local Streamlit config in `.streamlit/config.toml` sets
`server.headless = false` so the browser opens automatically on local start.
