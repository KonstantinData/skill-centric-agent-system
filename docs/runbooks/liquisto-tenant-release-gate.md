# Liquisto Tenant Release Gate

Last updated: 2026-06-17 23:10 Europe/Berlin

This gate records what is required before the Liquisto tenant can be marked
ready beyond local fixture-backed development.

## Current Status

Status: `production-ready`

The repository now contains a setup-state Liquisto tenant fixture, hostname
authority evidence, tenant admin context API coverage, a tenant-aware operations
UI shell with role-derived workspace areas, authenticated session gating,
read-only admin UI for users, roles, settings, admin workflow routes and audit
traceability, role-based task intake, tenant data-source connector coverage,
tenant isolation tests, and a repository-owned Streamlit Business UI container
and manual deployment workflow.

Production readiness is certified for release scope `liquisto-tenant-launch` by
Production Readiness Evidence run `27719854597` on `main` at
`655beba1faba6763120198857d1c8aef075d4921`.

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

Latest recorded tenant runtime evidence:

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

Latest recorded production inventory evidence:

| Date | GitHub run | Ref | Result | Evidence |
| --- | --- | --- | --- | --- |
| 2026-06-17 23:00 Europe/Berlin | `27719494125` | `codex/liquisto-launch-finalize` / `9222cc64b9a9aa33fad89630552fc3a31f17d79c` | passed | Sanitized inventory confirmed container `liquisto-app-1` is healthy, uses image `scas-streamlit-business-ui:655beba1faba6763120198857d1c8aef075d4921`, exposes `127.0.0.1:8501`, and redacts SCAS-managed config values while preserving key presence. |
| 2026-06-17 15:22 Europe/Berlin | `27692078758` | `main` | passed | `liquisto.condata.io` routes through Nginx to `127.0.0.1:8501`; Docker container `liquisto-app-1` is healthy and runs `streamlit run apps/streamlit_business_ui/app.py`; image `scas-streamlit-business-ui:916b7d87295d685c7ab4c2c8ffc3049297ed9d56`; deployed source revision `916b7d87295d685c7ab4c2c8ffc3049297ed9d56`. |

The first 2026-06-17 inventory proved the repository-owned Streamlit Business UI
foundation behind the tenant hostname. Two intermediate inventory artifacts
from runs `27719268407` and `27719390153` were deleted because they exposed
over-specific server-side session context. The replacement workflow records only
SCAS-managed config keys with redacted values.

## Cloudflare DNS And TLS Evidence

The `Tenant Cloudflare Evidence` workflow has passed for staging and production
with `require_worker_route=false`:

| Date | Environment | GitHub run | Result | Evidence |
| --- | --- | --- | --- | --- |
| 2026-06-17 22:07 Europe/Berlin | staging | `27716489830` | passed | `liquisto.condata.io` has one proxied A record, TLS mode `full`, Worker route count `0`, Worker route required `false`. |
| 2026-06-17 22:07 Europe/Berlin | prod | `27716489895` | passed | `liquisto.condata.io` has one proxied A record, TLS mode `full`, Worker route count `0`, Worker route required `false`. |

The same workflow failed with `require_worker_route=true` for staging
(`27716338428`) and production (`27716338387`) because no Cloudflare Worker
route exists for the tenant hostname. This is expected for the current public UI
route: Cloudflare proxies DNS/TLS to the Hetzner/Nginx/Streamlit runtime path.
Do not treat a Worker route as required for `liquisto.condata.io` unless the
deployment architecture is explicitly changed. Cloudflare Workers remain the
Control API path, not the Streamlit UI hostname path.

## Streamlit Business UI Deployment

The repository-owned deployment path is documented in
`docs/runbooks/streamlit-business-ui-deployment.md` and implemented by
`.github/workflows/tenant-ui-deploy.yml`.

Latest production plan evidence:

| Date | GitHub run | Result | Evidence |
| --- | --- | --- | --- |
| 2026-06-17 22:56 Europe/Berlin | `27719099324` | passed | Applied `scas-streamlit-business-ui:655beba1faba6763120198857d1c8aef075d4921` to production compose project `liquisto` via `/opt/liquisto/scas-streamlit-business-ui.override.yml`; previous image was `scas-streamlit-business-ui:916b7d87295d685c7ab4c2c8ffc3049297ed9d56`; post-deploy Streamlit health check passed. |
| 2026-06-17 22:44 Europe/Berlin | `27718521611` | passed | Built `scas-streamlit-business-ui:655beba1faba6763120198857d1c8aef075d4921` for prod with `apply_deploy=false`; no remote host was changed. |

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

Latest production bootstrap evidence:

| Date | GitHub run | Result | Evidence |
| --- | --- | --- | --- |
| 2026-06-17 22:37 Europe/Berlin | `27718167513` | passed | Production Control API Worker deployed from `main` at `655beba1faba6763120198857d1c8aef075d4921`. |
| 2026-06-17 22:40 Europe/Berlin | `27718320221` | passed | Owner membership `tm-liquisto-initial-owner` is active with role `liquisto-owner`; owner principal remains only in the production GitHub secret. |

## Rollback And Deprovisioning

The rollback and deprovisioning dry-run path lives in
`docs/runbooks/liquisto-tenant-rollback-deprovisioning.md`. Production launch
readiness uses the production apply evidence as the rollback record for the UI
image path: run `27719099324` recorded the previous image and the SCAS-managed
compose file needed for manual rollback.

## Production Runtime And Readiness Evidence

Latest production runtime and repository readiness evidence:

| Date | GitHub run | Result | Evidence |
| --- | --- | --- | --- |
| 2026-06-17 23:09 Europe/Berlin | `27719854597` | passed | Production Readiness Evidence certified `liquisto-tenant-launch` for prod with `status=production-ready`, `final_decision=certified`, `certification_mode=certify`, and `evidence_source_mode=recheck`. |
| 2026-06-17 23:07 Europe/Berlin | `27719791096` | passed | Prod live runtime gate passed against `https://scas-control-api-prod.still-butterfly-bbff.workers.dev` with `task_suite=generic`, `case_count=4`, and `handler_binding_status=passed`; this run provides the handler-binding artifact required by certification. |
| 2026-06-17 23:03 Europe/Berlin | `27719532652` | passed | AI Gateway live smoke passed for prod on commit `655beba1faba6763120198857d1c8aef075d4921`. |
| 2026-06-17 22:42 Europe/Berlin | `27718417632` | passed | Prod live runtime gate passed against `https://scas-control-api-prod.still-butterfly-bbff.workers.dev` with `task_suite=tenant`, `case_count=6`, and `handler_binding_status=passed`. |
| 2026-06-17 22:46 Europe/Berlin | `27718626573` | passed | Production Readiness Evidence recheck passed repository, security, Python, invariant, rollback, JSON, and Worker gates for commit `655beba1faba6763120198857d1c8aef075d4921`; mode was `evidence-only`, final decision `not-certified`. |

The first certify attempt `27719704744` failed because it consumed the
tenant-suite runtime artifact as handler-binding evidence. The corrected
certification run `27719854597` consumed generic runtime handler-binding
evidence from `27719791096` and the Liquisto tenant-suite runtime evidence is
retained separately as tenant isolation evidence.

The earlier `consume-existing` readiness run `27718535233` failed because the
workflow expected an artifact named `security-evidence` while current Security
Governance runs upload `security-governance-evidence`. The follow-up recheck
run `27718626573` bypassed that artifact-name drift by rerunning the gates.

## Resolved Production Blockers

The Liquisto tenant launch blockers below were resolved for release scope
`liquisto-tenant-launch` on 2026-06-17:

- Cloudflare authorized evidence confirms a proxied A record for
  `liquisto.condata.io` without exposing the hidden origin value in public
  evidence.
- TLS mode is confirmed through the authorized Cloudflare evidence workflow.
- Worker route requirement is explicit for the selected architecture. For the
  current Cloudflare-proxied Hetzner/Nginx/Streamlit UI route, Worker route
  count `0` is accepted and documented; a future Worker-routed UI path must pass
  the evidence workflow with `require_worker_route=true`.
- Initial owner identity is bootstrapped and no longer `null`. Latest evidence:
  production bootstrap run `27718320221` passed.
- Production legal, register, contact, and owner data is verified in the
  approved operational source. Public fixtures may contain only non-secret
  sentinel values that clearly state the real data is not stored there.
- Production runtime configuration points to the production Control API, or any
  temporary staging Control API dependency is explicitly approved with an owner,
  expiry, and rollback path. The sanitized inventory run `27719494125`
  confirms the SCAS-managed production config keys are present and redacted.
- The production service runs `SCAS_UI_AUTH_MODE=required` with a server-owned
  tenant session context from the approved upstream authentication layer.
  Fixture mode must not be used on the public hostname.
- Staging gate passes with the same tenant authority and isolation invariants.
- Production gate passes against production Cloudflare and Hetzner resources.
- Rollback/deprovisioning dry-run evidence is linked before the production
  release decision.
- Production Readiness Evidence ran in `certify` mode and ended with
  `final_decision=certified`.

## Release Decision Rule

The release decision must remain fail-closed:

- local dry run passing is required but not sufficient,
- DNS proxy evidence is required but not sufficient,
- UI visibility is required but not sufficient,
- only a current live gate artifact from the target environment may upgrade the
  status from `not-production-ready`.
