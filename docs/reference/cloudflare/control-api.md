# Cloudflare Control API

## Purpose

The Control API is the Cloudflare Worker entrypoint for composition-time
metadata. It sits on the Control Plane side of the infrastructure boundary and
serves registry, policy, scope, knowledge, and memory context to the Composer.

The first implemented endpoint is:

```text
POST /composition/context
```

The endpoint contract is defined in
`schemas/composition-context.schema.json`. The Worker validates the request
shape, reads active registry metadata from D1, scores candidates against task
signals, applies policy bindings, checks principal scope bindings, and returns a
graph-validation summary for the selected context.

D1 remains authoritative for registry and policy-sensitive reads. KV is used
only for the optional `registry:version` value returned in the response.

Additional ingestion endpoints are now available:

```text
POST /knowledge/ingest
POST /memory/ingest
POST /retrieval/context
POST /ai-gateway/openai/chat/completions
```

`POST /knowledge/ingest` accepts normalized knowledge source/document content,
writes normalized objects, chunks, and a manifest to R2, then records
`knowledge_sources`, `knowledge_documents`, `knowledge_chunks`,
`ingestion_jobs`, and `audit_events` in D1. It also creates an
`embedding_update` job and publishes a message to `SCAS_INGEST_QUEUE`.
Knowledge records that originate from task-subject runtime facts may include a
`proposal` object produced by the Runtime Plane `KnowledgeRecordProposal` path.
When present, the Worker fails closed unless the proposal includes source run,
profile, and step provenance, Hetzner Runtime evidence URIs, freshness review
days, confidence tier, validation rules, and retention policy. The approved
proposal metadata is copied into the R2 manifest for auditability.

`POST /memory/ingest` accepts only validated consolidated memory records. It
writes memory content and a manifest to R2, then records `memory_records`,
`ingestion_jobs`, and `audit_events` in D1. It also creates an
`embedding_update` job and publishes a message to `SCAS_INGEST_QUEUE`. Raw
runtime traces and tool outputs are explicitly rejected by the endpoint.

The Worker has a Cloudflare Queues consumer for `scas-ingest-dev`. The consumer
processes `embedding_update` jobs, calls OpenAI embeddings through Cloudflare AI
Gateway with `text-embedding-3-small` and 1536 dimensions, and upserts vectors
into `SCAS_KNOWLEDGE_INDEX` or `SCAS_MEMORY_INDEX`. D1 `ingestion_jobs` remains
the retry/idempotency ledger: queued jobs move to `running`, then `succeeded` or
`failed`, and every terminal indexing result writes an `audit_events` row.

`POST /retrieval/context` accepts a principal, query text, allowed candidate
knowledge and memory scope IDs, and an optional `query_embedding`. D1 computes
the allowed IDs first. When an embedding is provided, the Worker queries the
bound Vectorize indexes and post-validates the matches against the D1-allowed
knowledge chunks and memory records before returning them.

`POST /ai-gateway/openai/chat/completions` is a narrow pass-through route to
Cloudflare AI Gateway's OpenAI chat completions endpoint. It fails closed with
`503 ai_gateway_not_configured` unless `AI_GATEWAY_ACCOUNT_ID` and the
`OPENAI_API_KEY` Worker secret are configured. When the Cloudflare AI Gateway
has Authenticated Gateway enabled, the optional `AI_GATEWAY_AUTH_TOKEN` Worker
secret is forwarded as `cf-aig-authorization`; `Authorization` remains reserved
for the OpenAI provider key.

## Authentication And Authorization

`GET /health` is public. Every other Control API endpoint requires a bearer
token and fails closed when no token binding is configured.

Supported Worker secret bindings:

| Secret | Scope |
| --- | --- |
| `CONTROL_API_TOKEN` | All protected endpoints |
| `CONTROL_API_COMPOSITION_TOKEN` | `POST /composition/context` |
| `CONTROL_API_INGESTION_TOKEN` | `POST /knowledge/ingest`, `POST /memory/ingest` |
| `CONTROL_API_RETRIEVAL_TOKEN` | `POST /retrieval/context` |
| `CONTROL_API_AI_GATEWAY_TOKEN` | `POST /ai-gateway/openai/chat/completions` |

Use endpoint-scoped tokens where practical. `CONTROL_API_TOKEN` is an admin
fallback for trusted automation.

Configure secrets with Wrangler:

```bash
npx wrangler secret put CONTROL_API_COMPOSITION_TOKEN --config workers/control-api/wrangler.toml
npx wrangler secret put CONTROL_API_INGESTION_TOKEN --config workers/control-api/wrangler.toml
npx wrangler secret put CONTROL_API_RETRIEVAL_TOKEN --config workers/control-api/wrangler.toml
npx wrangler secret put CONTROL_API_AI_GATEWAY_TOKEN --config workers/control-api/wrangler.toml
```

Runtime clients use `SCAS_CONTROL_API_TOKEN` or the CLI
`--control-plane-token` flag to send `Authorization: Bearer ...`. Python
runtime clients also send `User-Agent: skill-centric-agent-system/0.1` so
Cloudflare does not classify the request as the default Python urllib client.

## Dev Resource Names

| Resource | Name |
| --- | --- |
| Worker | `scas-control-api-dev` |
| D1 database | `scas-control-dev` |
| Knowledge R2 bucket | `scas-knowledge-dev` |
| Memory R2 bucket | `scas-memory-dev` |
| Knowledge Vectorize index | `scas-knowledge-dev` |
| Memory Vectorize index | `scas-memory-dev` |
| Ingestion queue | `scas-ingest-dev` |
| Ingestion dead-letter queue | `scas-ingest-dev-dlq` |
| KV namespace binding | `SCAS_CONFIG` |

The dev Worker is deployed at:

```text
https://scas-control-api-dev.still-butterfly-bbff.workers.dev
```

The dev D1 and KV resource IDs are committed in
`workers/control-api/wrangler.toml`. Re-run the bootstrap sequence only when the
Cloudflare dev resources need to be recreated.

## Bootstrap Sequence

Run these commands from the repository root after `npm install`.

Create the D1 database:

```bash
npx wrangler d1 create scas-control-dev --config workers/control-api/wrangler.toml
```

Copy the returned `database_id` into
`workers/control-api/wrangler.toml`.

Create R2 buckets:

```bash
npx wrangler r2 bucket create scas-knowledge-dev --config workers/control-api/wrangler.toml
npx wrangler r2 bucket create scas-memory-dev --config workers/control-api/wrangler.toml
```

Create the KV namespace:

```bash
npx wrangler kv namespace create SCAS_CONFIG --config workers/control-api/wrangler.toml
```

Copy the returned KV namespace `id` into
`workers/control-api/wrangler.toml`.

Create ingestion queues:

```bash
npx wrangler queues create scas-ingest-dev --config workers/control-api/wrangler.toml
npx wrangler queues create scas-ingest-dev-dlq --config workers/control-api/wrangler.toml
```

Create Vectorize indexes:

```bash
npx wrangler vectorize create scas-knowledge-dev --dimensions=1536 --metric=cosine --config workers/control-api/wrangler.toml
npx wrangler vectorize create scas-memory-dev --dimensions=1536 --metric=cosine --config workers/control-api/wrangler.toml
npx wrangler vectorize create-metadata-index scas-knowledge-dev --property-name=scope_id --type=string --config workers/control-api/wrangler.toml
npx wrangler vectorize create-metadata-index scas-memory-dev --property-name=memory_scope_id --type=string --config workers/control-api/wrangler.toml
```

The committed `wrangler.toml` binds these indexes as `SCAS_KNOWLEDGE_INDEX`
and `SCAS_MEMORY_INDEX`. If the embedding model changes, create replacement
indexes instead of mutating dimensions in place. The metadata indexes support
the retrieval endpoint's Vectorize filters, but D1 prefiltering and
post-validation remain the policy boundary.

Configure AI Gateway routing:

```bash
npx wrangler secret put OPENAI_API_KEY --config workers/control-api/wrangler.toml
npx wrangler secret put AI_GATEWAY_AUTH_TOKEN --config workers/control-api/wrangler.toml
npx wrangler secret put CONTROL_API_AI_GATEWAY_TOKEN --config workers/control-api/wrangler.toml
```

Set `AI_GATEWAY_ACCOUNT_ID` to the Cloudflare account ID and `AI_GATEWAY_ID`
to the intended AI Gateway name in the deployment environment. The committed
dev default keeps `AI_GATEWAY_ACCOUNT_ID = "unset"` so local and unconfigured
deployments fail closed.

For the dev Worker, the manual GitHub Actions deployment can perform the
rollout without committing secrets or account-specific config:

```bash
gh workflow run ci.yml \
  -f deploy_control_api_dev=false \
  -f run_ai_gateway_live_smoke=true \
  -f run_infra_smoke=false
```

The workflow writes `SCAS_DEV_OPENAI_API_KEY`, optional
`AI_GATEWAY_AUTH_TOKEN`, and `SCAS_DEV_CONTROL_API_TOKEN` to a temporary
runner-local JSON secrets file, deploys `scas-control-api-dev` with
`wrangler deploy --secrets-file`, rewrites `AI_GATEWAY_ACCOUNT_ID` from the
GitHub `SCAS_DEV_CLOUDFLARE_ACCOUNT_ID` secret only in the deployment
workspace, and runs
`scripts/cloudflare/ai_gateway_live_smoke.py`.

The GitHub `SCAS_DEV_CLOUDFLARE_API_TOKEN` used by this workflow must allow
Worker script writes on the target Cloudflare account. The rollout uploads
Worker code and Worker secrets; a token that only passes read-only readiness
checks will fail before the AI Gateway smoke request is sent. Legacy unprefixed
secrets remain compatibility fallbacks, but production-readiness evidence should
use the environment-prefixed secrets that the live gates also consume.

When `run_ai_gateway_live_smoke=true`, the workflow requires
`AI_GATEWAY_AUTH_TOKEN` as a GitHub Actions secret and fails before deployment
if it is missing. Setting the secret only on the already-deployed Worker is not
enough because the workflow performs a fresh deployment with a temporary
secrets file.

Apply D1 migrations locally:

```bash
npx wrangler d1 migrations apply scas-control-dev --local --config workers/control-api/wrangler.toml
```

Apply D1 migrations to Cloudflare:

```bash
npx wrangler d1 migrations apply scas-control-dev --remote --config workers/control-api/wrangler.toml
```

Generate the dev registry seed from the module contracts:

```bash
python scripts/cloudflare/generate_control_plane_seed.py --output examples/control-plane/dev-seed.sql
```

By default, the generator also reads neutral tenant fixtures from
`examples/tenants/*.json`. Use `--tenants-dir` only when intentionally pointing
at another non-secret fixture directory. Customer-specific onboarding data must
not be copied into reusable examples.

Seed the local D1 database:

```bash
npx wrangler d1 execute scas-control-dev --local --file examples/control-plane/dev-seed.sql --config workers/control-api/wrangler.toml --yes
```

Seed the Cloudflare dev D1 database:

```bash
npx wrangler d1 execute scas-control-dev --remote --file examples/control-plane/dev-seed.sql --config workers/control-api/wrangler.toml --yes
```

Regenerate Worker binding types after updating resource IDs:

```bash
npm run worker:types
```

Validate the Worker locally:

```bash
npm run worker:typecheck
npm run worker:test
npm run worker:check
```

Deploy the dev Worker:

```bash
npm run worker:deploy:dev
```

Smoke-test the deployed dev Worker against seeded D1 data:

```bash
curl -s -X POST https://scas-control-api-dev.still-butterfly-bbff.workers.dev/composition/context \
  -H "content-type: application/json" \
  -H "authorization: Bearer $SCAS_CONTROL_API_TOKEN" \
  --data-binary @examples/control-api/composition-context-request.json
```

The response must include `composition_status: "ready"` and a scored
`git-diff-analysis` candidate.

The generated dev seed also includes task-class modules for:

- `research-context-synthesis`,
- `task-execution-planning`,
- `general-task-summary`.

The Worker scoring path requires task-type compatibility before selecting a
candidate module, so a broad domain or capability-class match cannot select a
specialized module for the wrong task class.

`/composition/context` fails closed with `composition_status: "denied"` when
required policies are missing, graph validation fails, or no module candidate
matches the task signals.

Smoke-test knowledge ingestion:

```bash
curl -s -X POST https://scas-control-api-dev.still-butterfly-bbff.workers.dev/knowledge/ingest \
  -H "content-type: application/json" \
  -H "authorization: Bearer $SCAS_CONTROL_API_TOKEN" \
  --data-binary @examples/control-api/knowledge-ingest-request.json
```

The response includes `vector_status: "embedding_update_queued"` and an
`embedding_job_id`. The queue consumer processes that job asynchronously.

Smoke-test memory ingestion:

```bash
curl -s -X POST https://scas-control-api-dev.still-butterfly-bbff.workers.dev/memory/ingest \
  -H "content-type: application/json" \
  -H "authorization: Bearer $SCAS_CONTROL_API_TOKEN" \
  --data-binary @examples/control-api/memory-ingest-request.json
```

The response includes `vector_status: "embedding_update_queued"` and an
`embedding_job_id`. Failed embedding updates remain visible in
`ingestion_jobs.status` and `audit_events`.

Smoke-test retrieval after ingesting knowledge and memory:

```bash
curl -s -X POST https://scas-control-api-dev.still-butterfly-bbff.workers.dev/retrieval/context \
  -H "content-type: application/json" \
  -H "authorization: Bearer $SCAS_CONTROL_API_TOKEN" \
  --data-binary @examples/control-api/retrieval-context-request.json
```

The response must include `retrieval_status: "ready"` and only D1-allowed
knowledge chunks and memory records. Without `query_embedding`, the route
returns `vectorize.status: "d1_prefilter_ready"` and no semantic matches.

Smoke-test live retrieval with a deterministic query embedding and Vectorize
post-validation:

```bash
python scripts/runtime/live_retrieval_vectorize_smoke.py \
  --control-plane-url https://scas-control-api-dev.still-butterfly-bbff.workers.dev
```

Smoke-test AI Gateway fail-closed behavior before secrets are configured:

```bash
curl -s -X POST https://scas-control-api-dev.still-butterfly-bbff.workers.dev/ai-gateway/openai/chat/completions \
  -H "content-type: application/json" \
  -H "authorization: Bearer $SCAS_CONTROL_API_TOKEN" \
  --data-binary @examples/control-api/ai-gateway-chat-request.json
```

Smoke-test the configured live route without printing model output:

```bash
python scripts/cloudflare/ai_gateway_live_smoke.py \
  --control-api-url https://scas-control-api-dev.still-butterfly-bbff.workers.dev
```

## Seed Scope

`examples/control-plane/dev-seed.sql` is generated from
`registry/modules/**/module.json` and neutral tenant fixtures in
`examples/tenants/*.json`. It is the operational dev registry and tenant
control-plane seed. Referenced tools, scopes, policies, and validators are
emitted as generated stub modules until they have first-class module metadata
files.

Tenant seed records populate the D1 tenant projection tables:

- `tenants`
- `tenant_hostnames`
- `tenant_memberships`
- `tenant_role_bundles`
- `tenant_data_sources`
- `tenant_role_capability_grants`
- `tenant_role_data_source_grants`

Those records model the production authority chain. Users receive tenant roles
only; capabilities, runtime modules, and data-source grants are derived from
tenant role bundles.

`examples/control-plane/cloudflare-control-plane.json` is a broader storage
contract fixture. It exercises knowledge and memory record shapes in addition
to registry and tenant records and should not be treated as the exact deployed
dev seed.

## CI And Deployment

The main CI workflow runs Worker type checks and Vitest tests on pushes and pull
requests. Dev deployment is manual through `workflow_dispatch` with
`deploy_control_api_dev = true`, or locally with `npm run worker:deploy:dev`
when Wrangler is authenticated.

## Operational Rules

- The Worker uses Cloudflare bindings for D1, R2, and KV access.
- All non-health routes require bearer authentication and endpoint-scoped
  authorization.
- The Worker binds Vectorize indexes for knowledge and memory retrieval.
- Secrets are not stored in `wrangler.toml`; use Worker secrets or GitHub
  Actions secrets for deployment.
- D1 remains authoritative for registry and policy-sensitive reads.
- KV is only a cache snapshot source and must not become the source of truth for
  policy decisions.
- The Worker must not store raw runtime traces or tool outputs. Those remain on
  the Hetzner Runtime Plane.
- Knowledge and memory ingestion writes Cloudflare-owned metadata and
  consolidated objects only.
- AI Gateway routing is the only production OpenAI route exposed by the Control
  API Worker and must fail closed when secrets or account configuration are
  missing.
