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
`schemas/composition-context.schema.json`. The initial Worker implementation
validates the request shape and returns an empty
`pending_registry_implementation` context. Registry reads and scoring are added
in the next implementation phase.

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
