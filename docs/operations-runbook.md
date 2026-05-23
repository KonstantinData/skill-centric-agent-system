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
- Control API tokens must be scoped by endpoint where possible. Use
  `CONTROL_API_TOKEN` only for trusted automation that needs all protected
  endpoints.

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

## Live Preflight

Run this preflight before the live dev E2E and live Postgres concurrency gates.
It verifies readiness without printing secret values.

Local repository gates:

```bash
python -m pytest
python -m ruff check .
npm run worker:types
npm run worker:typecheck
npm run worker:test
npm run worker:check
```

GitHub and local secret presence:

```bash
gh secret list --repo KonstantinData/skill-centric-agent-system
```

Required GitHub secrets for the live gates are:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ZONE_ID`
- `HETZNER_HOST`
- `HETZNER_SSH_KEY`
- `HETZNER_USER`
- `OPENAI_API_KEY`
- `AI_GATEWAY_AUTH_TOKEN` when Cloudflare Authenticated Gateway is enabled
- `CONTROL_API_TOKEN`

`CLOUDFLARE_API_TOKEN` must be scoped to the Cloudflare account and must allow
Worker script writes. The manual Control API rollout deploys Worker code and
uploads Worker secrets through Wrangler; a token that only supports read-only
connectivity checks will fail before the live LLM smoke runs.

Cloudflare readiness:

```bash
npx wrangler whoami
npx wrangler secret list --config workers/control-api/wrangler.toml
npx wrangler d1 migrations list scas-control-dev --remote --config workers/control-api/wrangler.toml
npx wrangler d1 execute scas-control-dev --remote --command "SELECT id, name, kind, current_version_id FROM modules ORDER BY id;" --config workers/control-api/wrangler.toml
npx wrangler r2 bucket list --config workers/control-api/wrangler.toml
npx wrangler vectorize list --config workers/control-api/wrangler.toml
npx wrangler queues list --config workers/control-api/wrangler.toml
```

Control API auth readiness:

```bash
curl -s -o /dev/null -w "%{http_code}" "$SCAS_CONTROL_API_URL/health"
curl -s -o /dev/null -w "%{http_code}" -X POST "$SCAS_CONTROL_API_URL/composition/context" \
  -H "content-type: application/json" \
  --data-binary @examples/control-api/composition-context-request.json
curl -s -X POST "$SCAS_CONTROL_API_URL/composition/context" \
  -H "content-type: application/json" \
  -H "authorization: Bearer $SCAS_CONTROL_API_TOKEN" \
  --data-binary @examples/control-api/composition-context-request.json
```

Expected status codes:

- `/health` without authentication: `200`
- protected route without authentication: `401`
- protected route with a valid bearer token: `200`

If the unauthenticated protected route returns `200`, the dev Worker is stale
or missing Worker secrets. Configure `CONTROL_API_TOKEN`, deploy the dev Worker,
and repeat the preflight before running live runtime gates.

Hetzner readiness:

```bash
ssh "$HETZNER_USER@$HETZNER_HOST" \
  "test -w /opt/scas/runtime && sudo -u postgres psql -d scas_runtime -Atc 'SELECT count(*) FROM runtime.runtime_runs;'"
```

The live E2E gate also needs a usable `SCAS_RUNTIME_DATABASE_URL` on the
machine that runs the gate. If the database URL is not available locally, run
the E2E script from the Hetzner host or provide an agreed local connection
string.

When the Control API token is available only as a GitHub Actions secret, use
the manual live runtime workflow instead of copying the token to a local shell:

```bash
gh workflow run live-runtime-gates.yml -f run_live_dev_e2e=true
```

That workflow executes the live dev E2E gate on the Hetzner host, connects to
PostgreSQL over the local Unix socket, and stores artifacts below
`/opt/scas/runtime/live-dev-gates/<github-run-id>`.

Use the same workflow for the live Postgres concurrency smoke:

```bash
gh workflow run live-runtime-gates.yml \
  -f run_live_dev_e2e=false \
  -f run_postgres_concurrency_smoke=true
```

Run the AI Gateway dev deployment and live LLM smoke through GitHub Actions
when the Worker needs `OPENAI_API_KEY`, `AI_GATEWAY_AUTH_TOKEN`,
`CONTROL_API_TOKEN`, and AI Gateway account configuration:

```bash
gh workflow run ci.yml \
  -f deploy_control_api_dev=false \
  -f run_ai_gateway_live_smoke=true \
  -f run_infra_smoke=false
```

The workflow passes Worker secrets through a temporary runner-local JSON file
and `wrangler deploy --secrets-file`. The file is deleted after the deploy
step; the secret values must still originate from GitHub Actions secrets.
`OPENAI_API_KEY` is sent to the OpenAI provider through the standard
`Authorization` header. `AI_GATEWAY_AUTH_TOKEN` is sent separately as
`cf-aig-authorization` when Authenticated Gateway is enabled on Cloudflare AI
Gateway. For `run_ai_gateway_live_smoke=true`, `AI_GATEWAY_AUTH_TOKEN` must be
set as a GitHub Actions secret; setting it only on the Worker is not enough for
the workflow's fresh deployment.

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
  -H "authorization: Bearer $SCAS_CONTROL_API_TOKEN" \
  --data-binary @examples/control-api/composition-context-request.json

curl -s -X POST "$SCAS_CONTROL_API_URL/retrieval/context" \
  -H "content-type: application/json" \
  -H "authorization: Bearer $SCAS_CONTROL_API_TOKEN" \
  --data-binary @examples/control-api/retrieval-context-request.json

python scripts/cloudflare/ai_gateway_live_smoke.py \
  --control-api-url "$SCAS_CONTROL_API_URL"
```

Cloudflare ingestion and async indexing:

```bash
curl -s -X POST "$SCAS_CONTROL_API_URL/knowledge/ingest" \
  -H "content-type: application/json" \
  -H "authorization: Bearer $SCAS_CONTROL_API_TOKEN" \
  --data-binary @examples/control-api/knowledge-ingest-request.json

curl -s -X POST "$SCAS_CONTROL_API_URL/memory/ingest" \
  -H "content-type: application/json" \
  -H "authorization: Bearer $SCAS_CONTROL_API_TOKEN" \
  --data-binary @examples/control-api/memory-ingest-request.json

npx wrangler d1 execute scas-control-dev --remote \
  --command "SELECT id, job_type, status, attempts FROM ingestion_jobs WHERE job_type = 'embedding_update' ORDER BY updated_at DESC LIMIT 10;" \
  --config workers/control-api/wrangler.toml
```

Ingestion responses must include `vector_status: "embedding_update_queued"`
and an `embedding_job_id`. Failed embedding updates remain visible in
`ingestion_jobs` and `audit_events`; D1/R2 ingestion is still authoritative.

Hetzner Runtime Plane:

```bash
ssh "$HETZNER_USER@$HETZNER_HOST" \
  "test -w /opt/scas/runtime && sudo -u postgres psql -d scas_runtime -Atc 'SELECT count(*) FROM runtime.runtime_runs;'"
```

Live dev E2E gate:

```bash
gh workflow run live-runtime-gates.yml -f run_live_dev_e2e=true

python scripts/runtime/live_dev_e2e.py \
  --task-file examples/tasks/code-review-task.json
```

Postgres concurrency smoke:

```bash
gh workflow run live-runtime-gates.yml \
  -f run_live_dev_e2e=false \
  -f run_postgres_concurrency_smoke=true

python scripts/runtime/postgres_concurrency_smoke.py --events 20
```

This smoke test requires `SCAS_RUNTIME_DATABASE_URL` and verifies that
concurrent Flight Recorder writes persist a contiguous per-run `event_index`
sequence.

## Diagnostics

Composition failures:

- Check `POST /composition/context` response status and graph validation errors.
- Confirm the request used a bearer token with composition scope.
- Verify D1 seed state and policy/scope bindings.
- Verify module IDs and naming conventions.

Retrieval failures:

- Check `POST /retrieval/context` response scope IDs.
- Confirm the request used a bearer token with retrieval scope.
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
- Rotate or remove the affected Control API endpoint token.
- Remove or deny D1 policy/scope bindings for the affected capability.
- Remove a tool from the composed Runtime Agent Profile by policy.
- Disable live runtime execution by withholding `SCAS_RUNTIME_DATABASE_URL`.
- Disable OpenAI routing by removing the Worker `OPENAI_API_KEY` secret,
  removing the Worker `AI_GATEWAY_AUTH_TOKEN` secret when Authenticated Gateway
  is required, or leaving AI Gateway account configuration unset.
- Pause embedding population by removing `OPENAI_API_KEY`; ingestion can still
  persist D1/R2 records, but queued embedding jobs will fail closed and retry
  according to the queue policy.

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
