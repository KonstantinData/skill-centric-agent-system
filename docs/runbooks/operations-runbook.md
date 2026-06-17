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
  environment-specific tokens (`SCAS_DEV_CONTROL_API_TOKEN`,
  `SCAS_STAGING_CONTROL_API_TOKEN`, `SCAS_PROD_CONTROL_API_TOKEN`) for trusted
  automation that needs all protected endpoints.
- The environment resource manifest lives in
  `examples/infrastructure/environment-manifest.json`; update it before adding
  staging or production workflows.

## Production Release Gate

The production release gate is defined in `docs/policies/production-readiness.md`.
Do not mark the repository or any deployment as production-ready until that
gate passes for the target environment.

After a successful staging certification, bounded productive staging operation
is governed by `docs/runbooks/first-productive-agent-operation.md`. That mode
allows supervised work against certified staging infrastructure, but it is not a
production launch and must not process production customer data.

Required release evidence includes:

- repository integrity checks,
- contract and documentation consistency,
- staging and production environment separation,
- Control Plane readiness,
- Runtime Plane readiness,
- live runtime gates,
- executable skill runtime coverage,
- write-capable execution coverage when writes are in scope,
- operational telemetry,
- security closure,
- owner-approved release decision.

The release evidence must record command or workflow references without
including secret values or raw runtime artifacts.

Run the evidence-only workflow while production resources are still being
prepared:

```bash
gh workflow run production-readiness.yml \
  -f target_environment=dev \
  -f release_scope=initial-productive-core \
  -f certification_mode=evidence-only
```

Run certification mode only after the matching live runtime and AI Gateway
smoke workflow runs have passed on the same repository commit:

```bash
gh workflow run production-readiness.yml \
  -f target_environment=prod \
  -f release_scope=production-runtime \
  -f certification_mode=certify \
  -f live_runtime_gates_run_url=https://github.com/OWNER/REPO/actions/runs/RUN_ID \
  -f ai_gateway_smoke_run_url=https://github.com/OWNER/REPO/actions/runs/RUN_ID
```

Certification mode validates the referenced GitHub Actions run metadata before
writing `production-readiness-evidence.json`. The run URLs must be canonical,
same-repository URLs, the runs must have completed successfully, and their
`headSha` must match the release commit being evaluated.

## Security Closure

The current production threat model is:

```text
docs/policies/threat-model.md
```

The machine-readable security closure and token-scope review is:

```text
policies/security/production-security-closure.json
```

Validate security closure with:

```bash
python scripts/security/validate_security_closure.py
```

The validator fails closed when:

- the threat model is missing or not marked current,
- required security gates lack evidence,
- required token scope reviews are missing,
- open critical or high remediation remains,
- accepted findings lack owner, expiry, or compensating control,
- waiver policy permits committed secrets, unaudited production claims, or
  unbounded data movement, or
- secret-like values appear in the closure policy.

Token rotation and ownership must be rechecked before production
certification, after any suspected exposure, and when a workflow or runtime
boundary starts using a new secret.

## Telemetry Alerts

Production telemetry uses aggregate signals only. Raw runtime traces, tool
outputs, provider payloads, and artifact contents stay on the Hetzner Runtime
Plane and must not be copied into alert payloads, GitHub summaries, Notion
notes, or release evidence.

The alert policy and clean snapshot fixture live in:

```text
examples/operations/production-telemetry-policy.json
examples/operations/production-telemetry-snapshot.json
```

The schema contracts are:

```text
schemas/production-telemetry-policy.schema.json
schemas/production-telemetry-snapshot.schema.json
```

Evaluate a telemetry snapshot with:

```bash
python scripts/operations/evaluate_telemetry_alerts.py \
  --policy examples/operations/production-telemetry-policy.json \
  --snapshot examples/operations/production-telemetry-snapshot.json \
  --fail-on-critical
```

The initial policy covers:

- Runtime failure rate.
- Runtime policy denial rate.
- Runtime validation failure rate.
- Control Plane retrieval error rate.
- AI Gateway error rate.
- Embedding queue failure count.
- Retention cleanup error count.
- Retention cleanup missing-artifact count.

## Memory Operations Evidence

Memory taxonomy operations evidence is separate from raw runtime telemetry. It
uses aggregate, secret-free metadata only and is evaluated by
`evaluate_memory_operations_evidence`.

The clean fixture and schema live in:

```text
examples/operations/memory-operations-evidence.json
schemas/memory-operations-evidence.schema.json
```

The evidence gate covers:

- a live smoke that creates one procedural lesson and one knowledge proposal
  from the same Hetzner run evidence,
- candidate class counts and rejection reason counts,
- contrastive false-negative and false-positive counts,
- abstention/review rate,
- post-planning invariant violation count,
- Top-K memory load and retrieval cache hit rate,
- retention separation between Runtime Evidence cleanup and Cloudflare
  Knowledge/Memory retention,
- renderer behavior proving memory remains non-authoritative, and
- denial-ledger and lesson-relationship graph authority-delta counts.

Validate the clean memory operations evidence with:

```bash
python -m pytest tests/test_memory_operations_evidence.py
```

Alert response:

- `critical`: stop certification or rollout, inspect the referenced runbook
  area, and keep the release `not-production-ready` until the cause is fixed
  or explicitly waived.
- `warning`: keep the release non-certified unless the owner accepts the
  operational risk and records the waiver in release evidence.
- missing required telemetry fails closed according to each rule's
  `missing_data_severity`.

Alert evidence may include rule IDs, signal names, aggregate numeric values,
time windows, source names, workflow URLs, and runbook links. It must not
include secrets, raw trace payloads, raw tool outputs, private keys, provider
credentials, or customer content.

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
python -m pytest tests/test_runtime_efficiency_baselines.py
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

Required GitHub secrets for the live gates are environment-prefixed:

- `SCAS_DEV_CLOUDFLARE_ACCOUNT_ID`, `SCAS_STAGING_CLOUDFLARE_ACCOUNT_ID`, `SCAS_PROD_CLOUDFLARE_ACCOUNT_ID`
- `SCAS_DEV_CLOUDFLARE_DEPLOY_TOKEN`, `SCAS_STAGING_CLOUDFLARE_DEPLOY_TOKEN`, `SCAS_PROD_CLOUDFLARE_DEPLOY_TOKEN`
- `CLOUDFLARE_ZONE_ID`, `SCAS_STAGING_CLOUDFLARE_EVIDENCE_TOKEN`, `SCAS_PROD_CLOUDFLARE_EVIDENCE_TOKEN`
- `SCAS_DEV_HETZNER_HOST`, `SCAS_STAGING_HETZNER_HOST`, `SCAS_PROD_HETZNER_HOST`
- `SCAS_DEV_HETZNER_SSH_KEY`, `SCAS_STAGING_HETZNER_SSH_KEY`, `SCAS_PROD_HETZNER_SSH_KEY`
- `SCAS_DEV_HETZNER_USER`, `SCAS_STAGING_HETZNER_USER`, `SCAS_PROD_HETZNER_USER`
- `SCAS_DEV_OPENAI_API_KEY`, `SCAS_STAGING_OPENAI_API_KEY`, `SCAS_PROD_OPENAI_API_KEY`
- `SCAS_DEV_CONTROL_API_TOKEN`, `SCAS_STAGING_CONTROL_API_TOKEN`, `SCAS_PROD_CONTROL_API_TOKEN`
- `AI_GATEWAY_AUTH_TOKEN` when Cloudflare Authenticated Gateway is enabled

`SCAS_{ENV}_CLOUDFLARE_DEPLOY_TOKEN` must be scoped to the Cloudflare account
and must allow only the Worker, Worker secret, D1, and provisioning mutations
used by that environment's workflows. The manual Control API rollout deploys
Worker code and uploads Worker secrets through Wrangler; a read-only evidence
token will fail before the live LLM smoke runs. Tenant DNS, TLS, and Worker
route evidence uses `SCAS_{STAGING,PROD}_CLOUDFLARE_EVIDENCE_TOKEN`, which is
read-only on the `condata.io` zone. Legacy unprefixed `CLOUDFLARE_API_TOKEN` is
not an accepted fallback for SCAS deploy, secret sync, live gate, or tenant
evidence workflows.

The durable Cloudflare token matrix is maintained in
`docs/runbooks/scas-cloudflare-token-structure.md`.

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
the manual live runtime workflow instead of copying the token to a local shell.
The canonical live E2E command and passing criteria live in
`docs/runbooks/runtime-live-dev-e2e.md`.

For `staging` and `prod`, set `target_environment` accordingly and provide
`-f control_api_url=https://<worker-url>`.

That workflow executes the live dev E2E gate on the Hetzner host, connects to
PostgreSQL over the local Unix socket, and stores artifacts below
`/opt/scas/runtime/dev/live-gates/<github-run-id>`. With
`live_task_suite=generic`, it runs `code-review`, `research`,
`task-execution`, and `general-task` cases against the live Control Plane and
Hetzner Runtime Plane.

The same workflow also runs the live Postgres concurrency smoke and live
retrieval/Vectorize smoke. Use the mode-specific commands in
`docs/runbooks/runtime-live-dev-e2e.md`.

Run the AI Gateway dev deployment and live LLM smoke through GitHub Actions
when the Worker needs `SCAS_DEV_OPENAI_API_KEY`, `AI_GATEWAY_AUTH_TOKEN`,
`SCAS_DEV_CONTROL_API_TOKEN`, and AI Gateway account configuration:

```bash
gh workflow run ci.yml \
  -f target_environment=dev \
  -f deploy_control_api_dev=false \
  -f run_ai_gateway_live_smoke=true \
  -f run_infra_smoke=false \
  -f confirm_production=false
```

The workflow passes Worker secrets through a temporary runner-local JSON file
and `wrangler deploy --secrets-file`. The file is deleted after the deploy
step; the secret values must still originate from GitHub Actions secrets. The
dev deployment prefers `SCAS_DEV_*` secrets and falls back to legacy unprefixed
secrets only for compatibility.
`OPENAI_API_KEY` is sent to the OpenAI provider through the standard
`Authorization` header. `AI_GATEWAY_AUTH_TOKEN` is sent separately as
`cf-aig-authorization` when Authenticated Gateway is enabled on Cloudflare AI
Gateway. For `run_ai_gateway_live_smoke=true`, `AI_GATEWAY_AUTH_TOKEN` must be
set as a GitHub Actions secret; setting it only on the Worker is not enough for
the workflow's fresh deployment.
For `target_environment=prod`, the workflow also requires
`confirm_production=true` and enters the protected `production` GitHub
environment before deploying the Worker or running the live smoke.

## Smoke Tests

Repository validation:

```bash
python -m pytest
python -m pytest tests/test_runtime_efficiency_baselines.py
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

Use `docs/runbooks/runtime-live-dev-e2e.md` for the canonical manual GitHub
Actions command, required environment, and passing criteria. For local or
direct host checks, run:

```bash
python scripts/runtime/live_dev_e2e.py \
  --task-suite generic
```

Live retrieval and Vectorize smoke:

Use `docs/runbooks/runtime-live-dev-e2e.md` for the workflow-dispatch mode.
For local or direct host checks, run:

```bash
python scripts/runtime/live_retrieval_vectorize_smoke.py \
  --control-plane-url "$SCAS_CONTROL_API_URL"
```

Postgres concurrency smoke:

Use `docs/runbooks/runtime-live-dev-e2e.md` for the workflow-dispatch mode.
For local or direct host checks, run:

```bash
python scripts/runtime/postgres_concurrency_smoke.py --events 20
```

This smoke test requires `SCAS_RUNTIME_DATABASE_URL` and verifies that
concurrent Flight Recorder writes persist a contiguous per-run `event_index`
sequence.

Runtime retention cleanup:

```bash
scas-runtime retention plan \
  --storage-mode postgres \
  --database-url "$SCAS_RUNTIME_DATABASE_URL" \
  --artifact-root /opt/scas/runtime
```

The retention planner reads the Hetzner PostgreSQL runtime tables and separates
expired artifact URIs from retained runs. It does not delete anything.

Apply cleanup in dry-run mode before any destructive run:

```bash
scas-runtime retention apply \
  --storage-mode postgres \
  --database-url "$SCAS_RUNTIME_DATABASE_URL" \
  --artifact-root /opt/scas/runtime
```

Dry-run apply resolves artifact URIs, reports missing and unsafe paths, writes a
cleanup report artifact, and keeps all files in place.

Delete expired artifacts only after reviewing the plan and dry-run report:

```bash
scas-runtime retention apply \
  --storage-mode postgres \
  --database-url "$SCAS_RUNTIME_DATABASE_URL" \
  --artifact-root /opt/scas/runtime \
  --confirm
```

Cleanup rules:

- Only `hetzner://runtime/...` artifact URIs under the configured artifact root
  are eligible for deletion.
- Unknown URI schemes, parent traversal, absolute paths, and directories fail
  closed as unsafe entries.
- Missing expired artifacts are deterministic warnings by default: they are
  reported as `missing` and skipped while cleanup continues.
- Use `--strict-missing` when a missing expired artifact should make cleanup
  return an error.
- Runtime metadata rows, including runs, steps, events, checkpoints, tool
  invocations, validation results, and memory candidates, are retained in the
  first cleanup slice.
- Cleanup reports carry their own retention policy through
  `cleanup_report_artifact_days`, defaulting to 180 days.

Scheduled retention cleanup:

```bash
gh workflow run runtime-retention-cleanup.yml \
  -f target_environment=dev \
  -f cleanup_mode=dry-run \
  -f strict_missing=false \
  -f confirm_production=false
```

The scheduled workflow runs daily from `main` in dry-run mode against the dev
Hetzner artifact root. It packages the repository commit, executes
`scas-runtime retention apply` on the Hetzner host as the PostgreSQL runtime
user, persists the cleanup report under the configured artifact root, downloads
the non-secret report plus exit status, and uploads
`runtime-retention-cleanup-evidence`.

Manual confirmed deletion is allowed only through `workflow_dispatch` after the
dry-run report is reviewed:

```bash
gh workflow run runtime-retention-cleanup.yml \
  -f target_environment=prod \
  -f cleanup_mode=confirmed-delete \
  -f strict_missing=true \
  -f confirm_production=true
```

Scheduled runs must never set `cleanup_mode=confirmed-delete`; the workflow
fails closed if a non-manual event attempts destructive cleanup. Any production
retention cleanup, including dry-run, also requires `confirm_production=true`
and the protected `production` GitHub environment.

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
## Error Classification Gates

Evaluate F1/F2/R8 class thresholds before release gating:

```powershell
python scripts/operations/evaluate_error_classification_gates.py `
  --policy examples/operations/error-classification-gate-policy.json `
  --snapshot examples/operations/error-classification-gate-snapshot.json `
  --fail-on-failed
```

Generate trend reports by task type, module version, and environment:

```powershell
python scripts/operations/error_classification_report.py `
  --snapshot examples/operations/error-classification-report-snapshot.json `
  --output security-evidence/error-classification-report.json
```

