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

## Dev Resource Names

| Resource | Name |
| --- | --- |
| Worker | `scas-control-api-dev` |
| D1 database | `scas-control-dev` |
| Knowledge R2 bucket | `scas-knowledge-dev` |
| Memory R2 bucket | `scas-memory-dev` |
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
  --data-binary @examples/control-api/composition-context-request.json
```

The response must include `composition_status: "ready"` and a scored
`git-diff-analysis` candidate.

## Seed Scope

`examples/control-plane/dev-seed.sql` is generated from
`examples/modules/*.json` and is the operational dev registry seed. Referenced
tools, scopes, policies, and validators are emitted as generated stub modules
until they have first-class module metadata files.

`examples/control-plane/cloudflare-control-plane.json` is a broader storage
contract fixture. It exercises knowledge and memory record shapes in addition
to registry records and should not be treated as the exact deployed dev seed.

## CI And Deployment

The main CI workflow runs Worker type checks and Vitest tests on pushes and pull
requests. Dev deployment is manual through `workflow_dispatch` with
`deploy_control_api_dev = true`, or locally with `npm run worker:deploy:dev`
when Wrangler is authenticated.

## Operational Rules

- The Worker uses Cloudflare bindings for D1, R2, and KV access.
- Secrets are not stored in `wrangler.toml`; use Worker secrets or GitHub
  Actions secrets for deployment.
- D1 remains authoritative for registry and policy-sensitive reads.
- KV is only a cache snapshot source and must not become the source of truth for
  policy decisions.
- The Worker must not store raw runtime traces or tool outputs. Those remain on
  the Hetzner Runtime Plane.
