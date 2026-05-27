# Streamlit Business UI

Professional executive dashboard for SCAS business steering.

## Run

```powershell
python -m pip install -e ".[ui]"
streamlit run apps\streamlit_business_ui\app.py
```

The repository-local Streamlit config in `.streamlit/config.toml` sets
`server.headless = false` so the browser opens automatically on local start.
