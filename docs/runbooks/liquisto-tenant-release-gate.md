# Liquisto Tenant Release Gate

Last updated: 2026-06-16 12:18 Europe/Berlin

This gate records what is required before the Liquisto tenant can be marked
ready beyond local fixture-backed development.

## Current Status

Status: `not-production-ready`

The repository now contains a setup-state Liquisto tenant fixture, hostname
authority evidence, tenant admin context API coverage, a tenant-aware operations
UI shell with role-derived workspace areas, authenticated session gating,
read-only admin UI for users, roles, settings, admin workflow routes and audit
traceability, role-based task intake, tenant data-source connector coverage,
tenant isolation tests, and a repository-owned Streamlit Business UI container
and manual deployment workflow.

Production readiness is intentionally blocked until the authoritative live
infrastructure checks below pass. The dev tenant runtime gate has passed on
`main`, but this does not prove the production Streamlit UI deployment behind
`liquisto.condata.io`.

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
- tenant UI surfaces derive visible workspace areas from tenant roles and do not
  expose demo-only KPI paths,
- production-style UI mode fails closed without `SCAS_UI_SESSION_CONTEXT_JSON`
  and derives admin access from session role IDs instead of `SCAS_UI_ROLE_IDS`,
- UI smoke coverage checks tenant hostname, required labels, workspace routes,
  admin/non-admin separation, and admin workflow traceability without adding a
  browser E2E dependency yet,
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

Latest recorded evidence:

| Date | GitHub run | Ref | Result | Evidence |
| --- | --- | --- | --- | --- |
| 2026-06-15 22:20 Europe/Berlin | `27573865364` | `main` / `61917d37af90cb1e99cbe1ab7e0a36bd65cbaee9` | passed | `task_suite=tenant`, `case_count=6`, `handler_binding_status=passed` |

This verifies the tenant runtime path on the dev Hetzner runtime with the dev
Control Plane seeded from the `main` repository snapshot.

## Live UI Runtime Inventory

If `https://liquisto.condata.io/` appears to load an old Streamlit UI, collect a
read-only production inventory before changing the service:

```bash
gh workflow run tenant-ui-runtime-inventory.yml \
  -f target_environment=prod \
  -f hostname=liquisto.condata.io
```

The workflow records candidate Streamlit processes, systemd units, container
runtime metadata, compose/Dockerfile references, reverse-proxy references, Git
repositories, and app paths from the target Hetzner environment. It must not
mutate the runtime host. Use the inventory artifact to identify the actual
service, image, code path, and deployed Git revision before any deployment or
restart action.

## Streamlit Business UI Deployment

The repository-owned deployment path is documented in
`docs/runbooks/streamlit-business-ui-deployment.md` and implemented by
`.github/workflows/tenant-ui-deploy.yml`.

Build-only plan mode:

```bash
gh workflow run tenant-ui-deploy.yml \
  -f target_environment=staging \
  -f tenant_id=liquisto \
  -f hostname=liquisto.condata.io \
  -f control_api_url=https://<staging-control-api-url> \
  -f apply_deploy=false \
  -f confirm_production=false
```

Apply mode is manual-only and requires target-environment Hetzner secrets,
`SCAS_<ENV>_UI_SESSION_CONTEXT_JSON`, `SCAS_<ENV>_TENANT_ADMIN_TOKEN`, and an
`upstream_auth_evidence_url`. Production apply also requires
`confirm_production=true`. The workflow writes a complete SCAS-managed Compose
file and intentionally does not read legacy host Compose files or host `.env`
files. It writes sanitized deployment evidence and rolls back to the previous
Compose service image if the post-deploy Streamlit health check fails.

## Tenant Admin Bootstrap

The non-secret bootstrap procedure for the initial Liquisto tenant owner lives
in `docs/runbooks/liquisto-tenant-admin-bootstrap.md`. The actual owner identity
must stay in the approved operational source. Repository fixtures must not
contain private owner data, tokens, or provider IDs.

## Rollback And Deprovisioning

The rollback and deprovisioning dry-run path lives in
`docs/runbooks/liquisto-tenant-rollback-deprovisioning.md`. Production launch
readiness requires a dry-run record showing that Liquisto can be suspended or
rolled back without changing any other tenant.

## Production Blockers

Do not mark the Liquisto tenant `production-ready` until all of these are
resolved:

- Cloudflare dashboard or authorized API confirms the hidden origin record for
  `liquisto.condata.io`.
- TLS mode and Worker route binding are confirmed for the tenant hostname.
- Initial owner identity is bootstrapped and no longer `null`.
- Production legal, register, contact, and owner data is verified in the
  approved operational source. Public fixtures may contain only non-secret
  sentinel values that clearly state the real data is not stored there.
- Repository-owned deployment for `apps/streamlit_business_ui` to the service
  behind `https://liquisto.condata.io/` is executed and verified with
  `.github/workflows/tenant-ui-deploy.yml`, or the external deployment
  owner/runbook is recorded.
- The production service runs `SCAS_UI_AUTH_MODE=required` with a server-owned
  tenant session context from the approved upstream authentication layer.
  Fixture mode must not be used on the public hostname.
- Staging gate passes with the same tenant authority and isolation invariants.
- Production gate passes against production Cloudflare and Hetzner resources.
- Rollback/deprovisioning dry-run evidence is linked before the production
  release decision.

## Release Decision Rule

The release decision must remain fail-closed:

- local dry run passing is required but not sufficient,
- DNS proxy evidence is required but not sufficient,
- UI visibility is required but not sufficient,
- only a current live gate artifact from the target environment may upgrade the
  status from `not-production-ready`.
