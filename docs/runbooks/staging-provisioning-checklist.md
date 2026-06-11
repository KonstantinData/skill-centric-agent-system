# Staging Provisioning Checklist

## Purpose

This checklist turns the open infrastructure item in
`docs/roadmap/infrastructure-implementation-status.md` into an executable
staging work plan.

Use it to provision and validate the `staging` Cloudflare Control Plane and
Hetzner Runtime Plane before claiming `staging-ready` or using staging evidence
for production certification.

## Scope

Target environment:

```text
staging
```

This checklist covers:

- Cloudflare Control Plane resources.
- Hetzner Runtime Plane resources.
- environment-specific GitHub Actions secrets and Worker secrets.
- migrations, seed state, live gates, smoke checks, and release evidence.

This checklist does not cover `prod` provisioning. Repeat the same pattern for
`prod` only after staging passes without cross-environment dependencies.

## Source Of Truth

Use these files as the authoritative inputs:

- `examples/infrastructure/environment-manifest.json`
- `docs/policies/environment-separation.md`
- `docs/policies/infrastructure-boundary.md`
- `docs/policies/production-readiness.md`
- `docs/runbooks/operations-runbook.md`
- `docs/runbooks/runtime-live-dev-e2e.md`
- `workers/control-api/wrangler.toml`

Do not copy secret values into repository files, Notion notes, workflow logs,
or release evidence.

## Exit Criteria

Staging provisioning is complete only when all of the following are true:

- Cloudflare resources exist with the staging names from the environment
  manifest.
- `workers/control-api/wrangler.toml` points to the actual staging D1 and KV
  resource IDs.
- Staging GitHub Actions secrets exist with the `SCAS_STAGING_` prefix.
- Staging Worker secrets are set without using dev or legacy unprefixed
  secrets.
- Cloudflare D1 migrations have been applied to `scas-control-staging`.
- The staging Control Plane has been seeded intentionally.
- Hetzner staging database, owner role, schema, and artifact root exist.
- Live runtime gates pass against staging Cloudflare and staging Hetzner.
- Live retrieval/Vectorize smoke passes against staging.
- Postgres concurrency smoke passes against staging.
- Retention dry-run evidence is recorded for staging.
- Production-readiness evidence has been generated in `evidence-only` mode for
  `target_environment=staging`.

## Preflight

Confirm the working tree and local repository gates before provisioning:

```bash
git status --short --branch
python -m pytest
python -m ruff check .
npm run worker:typecheck
npm run worker:test
npm run worker:check
```

Confirm the staging resource plan:

```bash
python - <<'PY'
import json
from pathlib import Path

manifest = json.loads(Path("examples/infrastructure/environment-manifest.json").read_text())
staging = next(env for env in manifest["environments"] if env["name"] == "staging")
print(json.dumps(staging, indent=2))
PY
```

Expected staging names:

| Surface | Expected value |
| --- | --- |
| Worker | `scas-control-api-staging` |
| D1 database | `scas-control-staging` |
| Knowledge R2 bucket | `scas-knowledge-staging` |
| Memory R2 bucket | `scas-memory-staging` |
| Knowledge Vectorize index | `scas-knowledge-staging` |
| Memory Vectorize index | `scas-memory-staging` |
| KV namespace | `scas-config-staging` |
| Ingest queue | `scas-ingest-staging` |
| Dead-letter queue | `scas-ingest-staging-dlq` |
| AI Gateway | `scas-ai-gateway-staging-run` |
| Runtime database | `scas_runtime_staging` |
| Runtime schema | `runtime` |
| Runtime owner role | `scas_runtime_staging_app` |
| Artifact root | `/opt/scas/runtime/staging` |

## Cloudflare Control Plane

### Create Or Confirm Resources

Use the provisioning helper for staging:

```bash
scripts/cloudflare/bootstrap_control_api_environment.sh staging
```

If the resources already exist, confirm them manually instead of recreating
them:

```bash
npx wrangler d1 list --config workers/control-api/wrangler.toml
npx wrangler r2 bucket list --config workers/control-api/wrangler.toml
npx wrangler kv namespace list --config workers/control-api/wrangler.toml
npx wrangler queues list --config workers/control-api/wrangler.toml
npx wrangler vectorize list --config workers/control-api/wrangler.toml
```

Record the created resource IDs outside the repository until they are ready to
be committed as non-secret configuration. D1 and KV IDs are not secrets, but
they must match the actual staging resources.

### Reconcile Wrangler Configuration

Check the staging section:

```bash
rg -n "env.staging|scas-control-staging|scas-config-staging" workers/control-api/wrangler.toml
```

Required checks:

- `[env.staging]` uses `name = "scas-control-api-staging"`.
- `ENVIRONMENT = "staging"`.
- D1 binding points to `scas-control-staging`.
- R2 bindings point to `scas-knowledge-staging` and `scas-memory-staging`.
- KV binding points to the staging KV namespace ID.
- Queue producer and consumer use `scas-ingest-staging`.
- Dead-letter queue uses `scas-ingest-staging-dlq`.
- Vectorize bindings use the staging indexes.
- `AI_GATEWAY_ID = "scas-ai-gateway-staging-run"`.
- `AI_GATEWAY_ACCOUNT_ID` is intentionally configured for the staging deploy
  path before live AI Gateway smoke.

Generate Worker types and confirm the generated file is unchanged after the
configuration is reconciled:

```bash
npm run worker:types
git diff --exit-code workers/control-api/src/worker-configuration.d.ts
```

### Apply Migrations And Seed Staging

Apply D1 migrations to staging:

```bash
npx wrangler d1 migrations apply scas-control-staging \
  --remote \
  --env staging \
  --config workers/control-api/wrangler.toml
```

Generate and apply a staging seed:

```bash
python scripts/cloudflare/generate_control_plane_seed.py \
  --output examples/control-plane/staging-seed.sql

npx wrangler d1 execute scas-control-staging \
  --remote \
  --env staging \
  --file examples/control-plane/staging-seed.sql \
  --config workers/control-api/wrangler.toml \
  --yes
```

If `examples/control-plane/staging-seed.sql` is temporary evidence rather than
durable fixture data, do not commit it.

### Configure Secrets

Create environment-specific GitHub Actions secrets:

```text
SCAS_STAGING_CLOUDFLARE_ACCOUNT_ID
SCAS_STAGING_CLOUDFLARE_API_TOKEN
SCAS_STAGING_HETZNER_HOST
SCAS_STAGING_HETZNER_SSH_KEY
SCAS_STAGING_HETZNER_USER
SCAS_STAGING_OPENAI_API_KEY
SCAS_STAGING_CONTROL_API_TOKEN
```

Set Worker secrets through Wrangler for the staging environment:

```bash
npx wrangler secret put CONTROL_API_TOKEN \
  --env staging \
  --config workers/control-api/wrangler.toml

npx wrangler secret put CONTROL_API_COMPOSITION_TOKEN \
  --env staging \
  --config workers/control-api/wrangler.toml

npx wrangler secret put CONTROL_API_INGESTION_TOKEN \
  --env staging \
  --config workers/control-api/wrangler.toml

npx wrangler secret put CONTROL_API_RETRIEVAL_TOKEN \
  --env staging \
  --config workers/control-api/wrangler.toml

npx wrangler secret put CONTROL_API_AI_GATEWAY_TOKEN \
  --env staging \
  --config workers/control-api/wrangler.toml

npx wrangler secret put OPENAI_API_KEY \
  --env staging \
  --config workers/control-api/wrangler.toml
```

Or sync the existing GitHub Actions secrets to the staging Worker without
printing secret values:

```bash
gh workflow run control-api-worker-secrets.yml \
  -f target_environment=staging \
  -f include_ai_gateway_auth_token=false
```

The workflow writes a temporary runner-local JSON file, runs
`wrangler secret bulk`, lists only Worker secret names for verification, and
removes the temporary file in an `always()` cleanup step. It maps
`SCAS_STAGING_CONTROL_API_TOKEN` to the all-scope `CONTROL_API_TOKEN` and to the
endpoint-specific Worker secret names until separate endpoint-scoped GitHub
secrets are introduced.

Set `AI_GATEWAY_AUTH_TOKEN` only when Cloudflare Authenticated Gateway is
enabled for staging.

### Deploy And Validate Control API

Run the dry-run first:

```bash
npm run worker:check
```

Deploy staging explicitly:

```bash
npx wrangler deploy \
  --env staging \
  --config workers/control-api/wrangler.toml
```

Set the staging URL for checks:

```bash
export SCAS_CONTROL_API_URL="https://<staging-worker-url>"
```

Validate health and fail-closed auth:

```bash
curl -s -o /dev/null -w "%{http_code}" "$SCAS_CONTROL_API_URL/health"

curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$SCAS_CONTROL_API_URL/composition/context" \
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
- protected route with valid staging token: `200`

## Hetzner Runtime Plane

### Prepare Host

Confirm the target host is the staging host and not the dev or prod host:

```bash
ssh "$SCAS_STAGING_HETZNER_USER@$SCAS_STAGING_HETZNER_HOST" "hostname; pwd"
```

The staging artifact root must be:

```text
/opt/scas/runtime/staging
```

### Bootstrap Staging Runtime Storage

When staging Hetzner credentials are available only as GitHub Actions secrets,
use the manual bootstrap workflow:

```bash
gh workflow run staging-runtime-bootstrap.yml \
  -f target_environment=staging
```

The workflow uploads the repository PostgreSQL migrations to
`/opt/scas/migrations/hetzner/postgres`, runs the existing bootstrap script with
the staging database, owner, and artifact root, and verifies the runtime table
is queryable.

For direct host access, upload or make the repository migrations available on
the staging host. Then run:

```bash
SCAS_RUNTIME_DB=scas_runtime_staging \
SCAS_RUNTIME_DB_OWNER=scas_runtime_staging_app \
SCAS_RUNTIME_ROOT=/opt/scas/runtime/staging \
scripts/hetzner/bootstrap_runtime_plane.sh \
  --migrations-dir /opt/scas/migrations/hetzner/postgres
```

Do not use `--rebuild` unless the staging environment has been explicitly
declared disposable for that run.

Confirm PostgreSQL and artifact root readiness:

```bash
ssh "$SCAS_STAGING_HETZNER_USER@$SCAS_STAGING_HETZNER_HOST" \
  "test -w /opt/scas/runtime/staging && sudo -u postgres psql -d scas_runtime_staging -Atc 'SELECT count(*) FROM runtime.runtime_runs;'"
```

### Runtime Environment

The live runtime gates need a usable staging database connection on the Hetzner
host. Prefer a host-local connection managed by the live runtime workflow
instead of copying database URLs into local shells.

Required runtime values:

```text
TARGET_ENVIRONMENT=staging
SCAS_CONTROL_API_URL=https://<staging-worker-url>
SCAS_RUNTIME_ARTIFACT_ROOT=/opt/scas/runtime/staging
SCAS_REPOSITORY_ROOT=<uploaded repository path on the staging host>
```

## Live Gates

Run the staging live runtime gate through GitHub Actions:

```bash
gh workflow run live-runtime-gates.yml \
  -f target_environment=staging \
  -f control_api_url=https://<staging-worker-url> \
  -f run_live_dev_e2e=true \
  -f run_postgres_concurrency_smoke=false \
  -f run_live_retrieval_vectorize_smoke=false \
  -f seed_control_plane_dev=true \
  -f live_task_suite=generic
```

Then run Postgres concurrency smoke:

```bash
gh workflow run live-runtime-gates.yml \
  -f target_environment=staging \
  -f control_api_url=https://<staging-worker-url> \
  -f run_live_dev_e2e=false \
  -f run_postgres_concurrency_smoke=true \
  -f run_live_retrieval_vectorize_smoke=false \
  -f seed_control_plane_dev=false \
  -f live_task_suite=generic
```

Then run retrieval and Vectorize smoke:

```bash
gh workflow run live-runtime-gates.yml \
  -f target_environment=staging \
  -f control_api_url=https://<staging-worker-url> \
  -f run_live_dev_e2e=false \
  -f run_postgres_concurrency_smoke=false \
  -f run_live_retrieval_vectorize_smoke=true \
  -f seed_control_plane_dev=false \
  -f live_task_suite=generic
```

Run AI Gateway live smoke through the CI workflow after staging Worker secrets
and AI Gateway config are set:

```bash
gh workflow run ci.yml \
  -f deploy_control_api_dev=false \
  -f run_ai_gateway_live_smoke=true \
  -f run_infra_smoke=false
```

If the CI workflow only targets the dev Worker for this smoke, record that as a
blocking staging certification gap before claiming `staging-ready`.

## Retention Evidence

Run retention cleanup in dry-run mode for staging:

```bash
gh workflow run runtime-retention-cleanup.yml \
  -f target_environment=staging \
  -f cleanup_mode=dry-run \
  -f strict_missing=false
```

The evidence must not include raw runtime artifacts or secret values. It may
include report paths, counts, status, commit SHA, workflow URL, and target
environment.

## Production-Readiness Evidence

After the live gates pass, run evidence-only production-readiness for staging:

```bash
gh workflow run production-readiness.yml \
  -f target_environment=staging \
  -f release_scope=initial-productive-core \
  -f certification_mode=evidence-only
```

Do not run `certify` mode until the matching live runtime and AI Gateway smoke
workflow run URLs exist for the same commit and target environment.

## Staging Completion Record

Record the following in the SCAS tracking issue or release handoff:

- repository commit SHA,
- staging Worker URL,
- Cloudflare resource names and non-secret resource IDs,
- Hetzner host identifier, database name, owner role, and artifact root,
- D1 migration status,
- seed status,
- live runtime gates workflow URL,
- Postgres concurrency workflow URL,
- retrieval/Vectorize smoke workflow URL,
- AI Gateway smoke workflow URL or blocking gap,
- retention dry-run evidence URL,
- production-readiness evidence URL,
- unresolved gaps and owner-approved waivers.

## Failure Handling

If any staging gate fails:

1. Keep staging status below `staging-ready`.
2. Do not reuse dev evidence as staging evidence.
3. Identify whether the failure is in Cloudflare, Hetzner, secrets, migrations,
   seed state, Worker deployment, retrieval, AI Gateway, or runtime storage.
4. Use `docs/runbooks/operations-runbook.md` diagnostics for the affected
   plane.
5. Record the failure and next action in the SCAS tracking issue.
