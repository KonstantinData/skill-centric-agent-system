# Liquisto Tenant Release Gate

Last updated: 2026-06-15 12:51 Europe/Berlin

This gate records what is required before the Liquisto tenant can be marked
ready beyond local fixture-backed development.

## Current Status

Status: `not-production-ready`

The repository now contains a setup-state Liquisto tenant fixture, hostname
authority evidence, tenant admin context API coverage, a tenant-aware UI shell,
read-only admin UI, role-based task intake, tenant data-source connector
coverage, and tenant isolation tests.

Production readiness is intentionally blocked until the authoritative live
infrastructure checks below pass.

## Local Dry Run

Run these checks before opening a release PR:

```powershell
python -m pytest tests/test_tenant_hostname_resolution.py tests/test_control_plane_seed.py tests/test_tenant_isolation_matrix.py
python -m pytest tests/test_tenant_runtime_e2e.py tests/test_tenant_data_source_connector.py
python -m pytest tests/test_streamlit_business_ui.py tests/test_streamlit_task_intake_ui.py
python -m ruff check .
npm run worker:typecheck
npm run worker:test
npm run worker:check
```

The local dry run proves:

- `liquisto.condata.io` resolves to exactly one setup-state tenant authority,
- disabled tenant hostnames fail closed,
- Liquisto and demo tenant scope modules remain disjoint,
- memberships and data-source grants do not cross tenant boundaries,
- the Runtime Profile Composer and Runtime Enforcer reject invalid tenant
  authority before execution,
- tenant data-source access is mediated through role grants,
- tenant UI surfaces are read-only and fixture-backed,
- the Control API Worker compiles, tests, and dry-runs.

## Live Dev Gate

Run the tenant suite against live dev infrastructure:

```bash
gh workflow run live-runtime-gates.yml \
  -f target_environment=dev \
  -f run_live_dev_e2e=true \
  -f run_postgres_concurrency_smoke=false \
  -f run_live_retrieval_vectorize_smoke=false \
  -f seed_control_plane_dev=true \
  -f live_task_suite=tenant
```

Passing criteria are defined in `docs/runbooks/runtime-live-dev-e2e.md`.

## Production Blockers

Do not mark the Liquisto tenant `production-ready` until all of these are
resolved:

- Cloudflare dashboard or authorized API confirms the hidden origin record for
  `liquisto.condata.io`.
- TLS mode and Worker route binding are confirmed for the tenant hostname.
- Initial owner identity is bootstrapped and no longer `null`.
- Legal profile placeholders in `examples/tenants/liquisto.json` are replaced
  with verified allowed business data or moved to a non-public source of truth.
- Live dev tenant suite passes and produces attached workflow evidence.
- Staging gate passes with the same tenant authority and isolation invariants.
- Production gate passes against production Cloudflare and Hetzner resources.

## Release Decision Rule

The release decision must remain fail-closed:

- local dry run passing is required but not sufficient,
- DNS proxy evidence is required but not sufficient,
- UI visibility is required but not sufficient,
- only a current live gate artifact from the target environment may upgrade the
  status from `not-production-ready`.
