# Runtime Live Dev E2E Gate

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

## Required Environment

Set these variables on the machine that runs the gate:

```bash
export SCAS_CONTROL_API_URL="https://scas-control-api-dev.still-butterfly-bbff.workers.dev"
export SCAS_CONTROL_API_TOKEN="..."
export SCAS_RUNTIME_DATABASE_URL="postgresql://..."
export SCAS_RUNTIME_ARTIFACT_ROOT="/opt/scas/runtime"
export SCAS_REPOSITORY_ROOT="/path/to/skill-centric-agent-system"
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
  -f run_live_dev_e2e=true \
  -f run_postgres_concurrency_smoke=false \
  -f run_live_retrieval_vectorize_smoke=false \
  -f seed_control_plane_dev=true \
  -f live_task_suite=generic
```

The workflow uses GitHub `CONTROL_API_TOKEN` and Hetzner SSH secrets, uploads
the checked-out commit to the Hetzner host, installs the runtime dependencies
there, connects to PostgreSQL over the local Unix socket as the `postgres`
system user, and writes gate artifacts under
`/opt/scas/runtime/dev/live-gates/<github-run-id>`.
If the dev host does not yet have Python venv support, the workflow installs
`python3-venv` and `python3.12-venv` before creating the gate environment.
With `seed_control_plane_dev=true`, the workflow applies D1 migrations and
reseeds the dev registry from `examples/modules/*.json` before running the
gate. The same workflow can run the live Postgres concurrency smoke by setting
`run_live_dev_e2e=false` and `run_postgres_concurrency_smoke=true`, or the live
retrieval/Vectorize smoke by setting `run_live_retrieval_vectorize_smoke=true`.

Local or direct host command:

```bash
python scripts/runtime/live_dev_e2e.py \
  --task-suite generic
```

The script uses the Cloudflare Control API for both composition and retrieval,
opens the Hetzner PostgreSQL runtime store, writes JSON artifacts to the
configured artifact root, runs the minimal runtime loop, and prints a JSON
summary. Use `--task-suite single --task-file ...` to run one task fixture.

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

Any failed composition, retrieval scope expansion, profile enforcement denial,
tool failure, validator failure, or PostgreSQL persistence error fails the gate.
