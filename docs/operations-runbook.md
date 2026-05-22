# Operations Runbook

## Purpose

This runbook defines the baseline operating procedures for the productive
runtime core. It covers deployment boundaries, migrations, smoke tests,
environment separation, diagnostics, and disable paths.

## Environment Separation

Supported environments:

- `dev`: live development infrastructure, manual gates, seeded test data.
- `staging`: production-like rehearsal, no user-facing traffic by default.
- `prod`: production runtime, stricter change control, explicit approvals.

Rules:

- Cloudflare Control Plane resources must use environment-suffixed names.
- Hetzner Runtime Plane databases and artifact roots must be environment
  separated before staging or production rollout.
- Runtime artifacts stay on Hetzner.
- Cloudflare receives only Control Plane data and validated memory records.
- Secrets must be injected through GitHub Actions, Worker secrets, or host
  environment variables. Secrets must not be committed.

## Migration Flow

Cloudflare Control Plane:

```bash
npx wrangler d1 migrations apply scas-control-dev --remote --config workers/control-api/wrangler.toml
python scripts/cloudflare/generate_control_plane_seed.py --output examples/control-plane/dev-seed.sql
npx wrangler d1 execute scas-control-dev --remote --file examples/control-plane/dev-seed.sql --config workers/control-api/wrangler.toml --yes
```

Hetzner Runtime Plane:

```bash
scripts/hetzner/bootstrap_runtime_plane.sh --migrations-dir /opt/scas/migrations/hetzner/postgres
```

Migration rules:

- Apply migrations before deploying runtime code that depends on them.
- Run smoke checks after every migration.
- Do not delete runtime artifacts during normal migrations.
- Use `--rebuild` only for explicitly disposable dev environments.

## Smoke Tests

Repository validation:

```bash
python -m pytest
python -m ruff check .
npm run worker:typecheck
npm run worker:test
npm run worker:check
```

Cloudflare Control API:

```bash
curl -s -X POST "$SCAS_CONTROL_API_URL/composition/context" \
  -H "content-type: application/json" \
  --data-binary @examples/control-api/composition-context-request.json

curl -s -X POST "$SCAS_CONTROL_API_URL/retrieval/context" \
  -H "content-type: application/json" \
  --data-binary @examples/control-api/retrieval-context-request.json
```

Hetzner Runtime Plane:

```bash
ssh "$HETZNER_USER@$HETZNER_HOST" \
  "test -w /opt/scas/runtime && sudo -u postgres psql -d scas_runtime -Atc 'SELECT count(*) FROM runtime.runtime_runs;'"
```

Live dev E2E gate:

```bash
python scripts/runtime/live_dev_e2e.py \
  --task-file examples/tasks/code-review-task.json
```

## Diagnostics

Composition failures:

- Check `POST /composition/context` response status and graph validation errors.
- Verify D1 seed state and policy/scope bindings.
- Verify module IDs and naming conventions.

Retrieval failures:

- Check `POST /retrieval/context` response scope IDs.
- Verify D1 scope bindings before Vectorize behavior.
- Treat Vectorize as ranking only, not policy authority.

Runtime failures:

- Inspect `runtime.runtime_runs.stop_reason`.
- Inspect `runtime.runtime_events` ordered by `event_index`.
- Inspect `runtime.runtime_checkpoints` ordered by `checkpoint_index`.
- Resolve payload URIs under the Hetzner artifact root.

Tool failures:

- Inspect `tool_invocations.status`.
- Resolve `input_uri` and `output_uri` artifacts.
- Check Tool Gateway denied access events before retrying.

Validator failures:

- Inspect `validation_results.status`.
- Resolve `findings_uri`.
- Check whether recomposition was requested or the profile failed closed.

## Disable Paths

Emergency disable options:

- Disable the Cloudflare Worker route or roll back the Worker deployment.
- Remove or deny D1 policy/scope bindings for the affected capability.
- Remove a tool from the composed Runtime Agent Profile by policy.
- Disable live runtime execution by withholding `SCAS_RUNTIME_DATABASE_URL`.
- Disable OpenAI routing by removing the Worker `OPENAI_API_KEY` secret or
  leaving AI Gateway account configuration unset.

Disable rules:

- Prefer policy denial over code deletion.
- Preserve runtime traces and artifacts for diagnosis.
- Record the disable action in Notion and repository documentation when it
  changes durable behavior.

## Recovery

Recovery steps:

1. Identify the failing plane: Cloudflare Control Plane or Hetzner Runtime Plane.
2. Confirm the latest applied migration.
3. Run the relevant smoke test.
4. Restore or reseed only the affected environment.
5. Re-run the live dev E2E gate before resuming productive runtime work.
