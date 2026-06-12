# SCAS Task Intake UI

Minimal Streamlit interface for submitting task envelopes to the SCAS runtime.

The app is intentionally a thin intake surface. It does not choose skills,
tools, policies, scopes, validators, or runtime profiles directly. It captures
the user request, creates the same task envelope shape used by the runtime CLI,
and can start a local fixture-backed runtime run for development.

## Run

```powershell
python -m pip install -e ".[ui]"
streamlit run apps\streamlit_task_intake_ui\app.py
```

Generated task envelopes are written to `.scas-runtime/intake/` by default.
