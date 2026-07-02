# Runtime Live E2E Gate

## Purpose

This gate proves the first productive runtime path and generic task strategies
against live development infrastructure:

```text
Task Intake
-> Task Analyzer
-> Cloudflare Composition Context
-> Runtime Profile
-> Hetzner PostgreSQL Run
-> Hetzner Artifact Events and Checkpoints
-> Control API Retrieval Context
-> Tool Gateway
-> Validator Framework
-> Runtime Result
```

It is intentionally manual because it requires live Cloudflare and Hetzner
credentials and should not run on every pull request.
The generic task suite covers `code-review`, `research`, `task-execution`, and
`general-task` without turning those task classes into separate agents.
Tenant-scoped backend E2E coverage is validated in CI with the neutral
`tenant-under-test` fixture before live tenant infrastructure is used. That
coverage proves:

- task auth produces `tenant_context`,
- the runtime entrypoint requests composition context through the Control API
  client,
- the Composer seals `tenant_authority` into the profile,
- the Runtime Profile Enforcer and tenant validators run before execution,
- invalid tenant authority, missing membership, and tampered scopes fail closed.

## Required Environment

Set these variables on the machine that runs the gate:

```bash
export SCAS_CONTROL_API_URL="https://scas-control-api-dev.still-butterfly-bbff.workers.dev"
export SCAS_CONTROL_API_TOKEN="..."
export SCAS_RUNTIME_DATABASE_URL="postgresql://..."
export SCAS_RUNTIME_ARTIFACT_ROOT="/opt/scas/runtime/dev"
export SCAS_REPOSITORY_ROOT="/path/to/skill-centric-agent-system"
export TARGET_ENVIRONMENT="dev"
```

`SCAS_CONTROL_API_TOKEN` must authorize both composition and retrieval, either
through the admin token or the endpoint-scoped composition and retrieval
tokens. `SCAS_RUNTIME_DATABASE_URL` must point to the Hetzner runtime
PostgreSQL database. Productive runtime artifacts must be written under the
Hetzner artifact root.

## Command

Preferred manual GitHub Actions gate:

```bash
gh workflow run live-runtime-gates.yml \
  -f target_environment=dev \
  -f run_live_dev_e2e=true \
  -f run_postgres_concurrency_smoke=false \
  -f run_live_retrieval_vectorize_smoke=false \
  -f seed_control_plane_dev=true \
  -f live_task_suite=tenant \
  -f confirm_production=false
```

For `staging` and `prod`, set `target_environment` accordingly and pass
`control_api_url` explicitly.
For `prod`, also set `confirm_production=true`; the job enters the protected
`production` GitHub environment before it can run against production secrets
or hosts. `seed_control_plane_dev=true` is not allowed for `prod`; production
D1 migrations and seeding must use a dedicated production migration control
path with separate review and evidence.
The workflow resolves environment-specific secrets (`SCAS_DEV_*`,
`SCAS_STAGING_*`, `SCAS_PROD_*`), uploads the checked-out commit to the
Hetzner host, installs the runtime dependencies there, connects to PostgreSQL
over the local Unix socket as the `postgres` system user, and writes gate
artifacts under `/opt/scas/runtime/<target_environment>/live-gates/<github-run-id>`.
If the dev host does not yet have Python venv support, the workflow installs
`python3-venv` and `python3.12-venv` before creating the gate environment.
With `seed_control_plane_dev=true`, the workflow applies D1 migrations, reseeds
the dev registry from `registry/modules/**/module.json` and neutral tenant
authority records under `registry/tenants/`, legacy fixtures under
`examples/tenants/`, and deploys the dev Control API Worker from
the checked-out commit before running the gate. Tenant fixtures generate
tenant-owned knowledge/data scope modules and scope bindings for the seeded
principal, so the Control Plane can return tenant-local scopes instead of
falling back to global memory or data grants. The same workflow can run the
live Postgres concurrency smoke by setting
`run_live_dev_e2e=false` and `run_postgres_concurrency_smoke=true`, or the live
retrieval/Vectorize smoke by setting `run_live_retrieval_vectorize_smoke=true`.
Before packaging and uploading the Hetzner runtime snapshot, the workflow
validates the target Control Plane token against `POST /composition/context`.
When Control Plane seeding is enabled, it also validates the Cloudflare API
token with `wrangler whoami` before applying D1 migrations. A 401/403 from the
Control Plane or an authentication error from Wrangler means the GitHub Actions
secret for the target environment must be rotated or updated before the live
gate can produce certification evidence.

Local or direct host command:

```bash
python scripts/runtime/live_dev_e2e.py \
  --environment dev \
  --task-suite tenant
```

The script uses the Cloudflare Control API for both composition and retrieval,
opens the Hetzner PostgreSQL runtime store, writes JSON artifacts to the
configured artifact root, runs the minimal runtime loop, and prints a JSON
summary. Use `--task-suite single --task-file ...` to run one task fixture.
Use `--task-suite generic` to run the non-tenant task classes. Use
`--task-suite tenant` to run the neutral `tenant-under-test` positive case and
fail-closed tenant isolation cases without unrelated tenant data.
Use the workflow's target-tenant suite choices to run a single
target-environment tenant positive case against the tenant authority seeded for
non-production gates. These target tenant suites use the seeded
`repository-maintainer` role principal and the tenant-local default membership;
they do not generate private task files or require tenant owner principal
secrets. The `tenant_kinderhaus` suite uses only the
`tenant_kinderhaus-public-researcher` role, which grants read access to the
public website data source and does not include minimal-operations data.
For every case, the summary includes the planner checkpoint URI and sanitized
`skill_handlers` bindings (`name`, `version`, and `handler_id`) so release
evidence can prove which executable handler ran without copying raw traces.

Live retrieval and Vectorize post-validation smoke:

```bash
python scripts/runtime/live_retrieval_vectorize_smoke.py \
  --control-plane-url "$SCAS_CONTROL_API_URL"
```

## Passing Criteria

The gate passes when the output includes:

- `status: "passed"`
- each case has `composition_status: "ready"`
- each case has `run_status: "succeeded"`
- each case has `stop_reason: "completed"`
- each case has `event_count` greater than zero
- each case has `checkpoint_count` greater than zero
- each case has `runtime_output_task_type` equal to the profile task type
- each case has `handler_binding_status: "passed"`
- each case has at least one `skill_handlers` binding where
  `handler_id` equals `name@version`

For `--task-suite tenant`, the positive `tenant-positive` case must satisfy the
same runtime criteria. The negative cases must report `status: "passed"` while
failing before tenant-boundary execution:

- `tenant-unknown-tenant`
- `tenant-missing-membership`
- `tenant-foreign-data-source`
- `tenant-tampered-authority`

For target-tenant suites, the single positive case must satisfy the same
runtime criteria with `task_suite` equal to the selected suite and
`case_count: 1`.

Any failed composition, retrieval scope expansion, profile enforcement denial,
tool failure, validator failure, or PostgreSQL persistence error fails the gate.
When run through GitHub Actions, the live E2E gate uploads
`live-runtime-handler-binding-evidence` with `live-dev-e2e.json`. Production
certification downloads and validates that artifact before accepting the live
runtime gate.
