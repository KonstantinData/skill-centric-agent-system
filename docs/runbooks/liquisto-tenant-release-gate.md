# Liquisto Tenant Release Gate

Last updated: 2026-06-25 21:12 Europe/Berlin

This gate records what is required before the Liquisto tenant can be marked
ready beyond local fixture-backed development.

## Current Status

Status: `migration-validation-required`

The repository now contains a setup-state Liquisto tenant fixture, hostname
authority evidence, tenant admin context API coverage, a tenant-aware operations
UI shell with role-derived workspace areas, authenticated session gating,
read-only admin UI for users, roles, settings, admin workflow routes and audit
traceability, role-based task intake, tenant data-source connector coverage,
tenant isolation tests, and a repository-owned Streamlit Business UI container
and manual deployment workflow.

Previous production readiness evidence does not certify the `liquisto.cloud`
authority after cutover. The Liquisto launch gate must be revalidated against
the `liquisto.cloud` Cloudflare zone, DNS/TLS route, and runtime hostname before
the status can return to `production-ready`.

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

- `liquisto.cloud` resolves to exactly one setup-state tenant authority,
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

If `https://liquisto.cloud/` appears to load an old Streamlit UI, collect a
read-only production inventory before changing the service:

```bash
gh workflow run tenant-ui-runtime-inventory.yml \
  -f target_environment=prod \
  -f hostname=liquisto.cloud
```

The workflow records candidate Streamlit processes, systemd units, container
runtime metadata, compose/Dockerfile references, reverse-proxy references, Git
repositories, and app paths from the target Hetzner environment. It must not
mutate the runtime host. Use the inventory artifact to identify the actual
service, image, code path, and deployed Git revision before any deployment or
restart action.

Latest recorded production inventory evidence for the current
`liquisto.cloud` authority:

| Date | GitHub run | Ref | Result | Evidence |
| --- | --- | --- | --- | --- |
| pending | pending | pending | pending | Re-run `tenant-ui-runtime-inventory.yml` with `hostname=liquisto.cloud` after DNS/TLS cutover. |

The inventory workflow records only SCAS-managed config keys with redacted
values. Use a fresh inventory artifact for the `liquisto.cloud` authority before
making a production release decision.

## Cloudflare DNS And TLS Evidence

The `Tenant Cloudflare Evidence` workflow must pass for `liquisto.cloud` with
`require_worker_route=false` unless the UI is intentionally moved behind a
Cloudflare Worker route:

| Date | Environment | GitHub run | Result | Evidence |
| --- | --- | --- | --- | --- |
| 2026-06-25 21:55 Europe/Berlin | liquisto | `28196655630` | passed | DNS cutover applied; `liquisto.cloud` has one proxied A record, TLS mode `full`, Worker route count `0`, Worker route required `false`; origin content was not printed. |

Do not treat a Worker route as required for `liquisto.cloud` unless the
deployment architecture is explicitly changed. Cloudflare Workers remain the
Control API path, not the Streamlit UI hostname path.

## Liquisto Workbench Deployment

The repository-owned deployment path is documented in
`docs/runbooks/liquisto-workbench-deployment.md` and implemented by
`.github/workflows/tenant-ui-deploy.yml`.

Latest production apply evidence for the current `liquisto.cloud` authority:

| Date | GitHub run | Result | Evidence |
| --- | --- | --- | --- |
| 2026-06-26 07:19 Europe/Berlin | `28218809860` | passed | Deployed `liquisto-workbench` image `scas-liquisto-workbench:6ceb8e91385f95e35496c0e149767ea770a4ff91`; Nginx route managed at `127.0.0.1:3027` for `liquisto.cloud www.liquisto.cloud`; Cloudflare DNS synced to the deployment host; public `Command Center` marker verified for apex and `www`. |
| 2026-06-25 22:56 Europe/Berlin | `28199866868` | passed | Deployed `liquisto-workbench` image `scas-liquisto-workbench:f2572484724b3886c4cd3de08cc3945464e9348b`; Nginx route managed at `127.0.0.1:3027`; Cloudflare DNS synced to the deployment host; public `Command Center` marker verified. |

Build-only plan mode:

```bash
gh workflow run tenant-ui-deploy.yml \
  -f target_environment=staging \
  -f tenant_id=liquisto \
  -f hostname=liquisto.cloud \
  -f control_api_url=https://<staging-control-api-url> \
  -f ui_app=liquisto-workbench \
  -f apply_deploy=false \
  -f confirm_production=false
```

Apply mode is manual-only and requires target-environment Hetzner secrets,
`SCAS_<ENV>_UI_SESSION_CONTEXT_JSON`, `SCAS_<ENV>_TENANT_ADMIN_TOKEN`, and an
`upstream_auth_evidence_url`. Production apply also requires
`confirm_production=true`. The workflow writes a complete SCAS-managed Compose
file, sets `SCAS_UI_TENANT_ID=liquisto`, and intentionally does not read legacy
host Compose files or host `.env` files. The fixed tenant binding means
`liquisto.cloud` cannot expose a tenant selector or switch to another
tenant through UI state. The workflow writes sanitized deployment evidence and
rolls back to the previous Compose service image if the post-deploy health or
Workbench content check fails. For `liquisto-workbench`, the workflow also
verifies the public Cloudflare routes for both `liquisto.cloud` and
`www.liquisto.cloud` before the deploy can pass.

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

Latest production runtime and repository readiness evidence for the current
`liquisto.cloud` authority:

| Date | GitHub run | Result | Evidence |
| --- | --- | --- | --- |
| pending | pending | pending | Re-run production readiness after Cloudflare evidence and runtime inventory for `liquisto.cloud` pass. |

## Resolved Production Blockers

The Liquisto tenant launch blockers below must be resolved for the
`liquisto.cloud` authority:

- Cloudflare authorized evidence confirms a proxied A record for
  `liquisto.cloud` without exposing the hidden origin value in public
  evidence.
- TLS mode is confirmed through the authorized Cloudflare evidence workflow.
- Worker route requirement is explicit for the selected architecture. For the
  current Cloudflare-proxied Hetzner/Nginx/Streamlit UI route, Worker route
  count `0` is accepted and documented; a future Worker-routed UI path must pass
  the evidence workflow with `require_worker_route=true`.
- Initial owner identity is bootstrapped and no longer `null`.
- Production legal, register, contact, and owner data is verified in the
  approved operational source. Public fixtures may contain only non-secret
  sentinel values that clearly state the real data is not stored there.
- Production runtime configuration points to the production Control API, or any
  temporary staging Control API dependency is explicitly approved with an owner,
  expiry, and rollback path.
- The production service runs `SCAS_UI_AUTH_MODE=required` with a server-owned
  tenant session context from the approved upstream authentication layer.
  Fixture mode must not be used on the public hostname.
- Staging gate passes with the same tenant authority and isolation invariants.
- Production gate passes against production Cloudflare and Hetzner resources.
- Rollback/deprovisioning dry-run evidence is linked before the production
  release decision.
- Production Readiness Evidence must run in `certify` mode and end with
  `final_decision=certified` after the `liquisto.cloud` evidence is current.

## Release Decision Rule

The release decision must remain fail-closed:

- local dry run passing is required but not sufficient,
- DNS proxy evidence is required but not sufficient,
- UI visibility is required but not sufficient,
- only a current live gate artifact from the target environment may upgrade the
  status from `not-production-ready`.
