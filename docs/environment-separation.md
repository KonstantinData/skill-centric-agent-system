# Environment Separation

## Purpose

Production readiness requires Cloudflare Control Plane and Hetzner Runtime
Plane resources to be separated by environment. Development evidence must not
share mutable state with staging or production.

The machine-readable resource plan lives in
`examples/infrastructure/environment-manifest.json` and is validated against
`schemas/environment-manifest.schema.json`.

## Environments

| Environment | Role | Release Use |
| --- | --- | --- |
| `dev` | Development | Live development gates and seeded fixtures. |
| `staging` | Rehearsal | Production-like release rehearsal without user-facing traffic by default. |
| `prod` | Production | Production runtime with explicit approval and stricter change control. |

## Separation Rules

- Cloudflare resources use environment-suffixed names.
- Hetzner runtime databases, owner roles, and artifact roots are environment
  specific.
- GitHub Actions secrets use environment-specific prefixes for staging and
  production.
- `dev` evidence cannot certify `staging` or `prod`.
- Runtime artifacts stay on the Hetzner Runtime Plane for the target
  environment.
- Cloudflare receives only Control Plane data and validated memory records for
  the target environment.
- Production release workflows must select exactly one target environment.

## Cloudflare Resource Names

| Resource | `dev` | `staging` | `prod` |
| --- | --- | --- | --- |
| Worker | `scas-control-api-dev` | `scas-control-api-staging` | `scas-control-api-prod` |
| D1 database | `scas-control-dev` | `scas-control-staging` | `scas-control-prod` |
| Knowledge R2 bucket | `scas-knowledge-dev` | `scas-knowledge-staging` | `scas-knowledge-prod` |
| Memory R2 bucket | `scas-memory-dev` | `scas-memory-staging` | `scas-memory-prod` |
| Knowledge Vectorize index | `scas-knowledge-dev` | `scas-knowledge-staging` | `scas-knowledge-prod` |
| Memory Vectorize index | `scas-memory-dev` | `scas-memory-staging` | `scas-memory-prod` |
| KV namespace | `scas-config-dev` | `scas-config-staging` | `scas-config-prod` |
| Ingestion queue | `scas-ingest-dev` | `scas-ingest-staging` | `scas-ingest-prod` |
| Ingestion dead-letter queue | `scas-ingest-dev-dlq` | `scas-ingest-staging-dlq` | `scas-ingest-prod-dlq` |
| AI Gateway | `scas-ai-gateway-dev-run` | `scas-ai-gateway-staging-run` | `scas-ai-gateway-prod-run` |

## Hetzner Resource Names

| Resource | `dev` | `staging` | `prod` |
| --- | --- | --- | --- |
| Runtime database | `scas_runtime` | `scas_runtime_staging` | `scas_runtime_prod` |
| Runtime schema | `runtime` | `runtime` | `runtime` |
| Owner role | `scas_runtime_app` | `scas_runtime_staging_app` | `scas_runtime_prod_app` |
| Artifact root | `/opt/scas/runtime/dev` | `/opt/scas/runtime/staging` | `/opt/scas/runtime/prod` |

## Secret Naming

Use environment-specific secrets for release automation:

| Environment | Prefix |
| --- | --- |
| `dev` | `SCAS_DEV_` |
| `staging` | `SCAS_STAGING_` |
| `prod` | `SCAS_PROD_` |

The current development workflows may still use legacy unprefixed secret names
for backward compatibility. Staging and production workflows must not use
legacy unprefixed secret names.

## Validation

Environment separation is valid when:

- the manifest passes schema validation,
- persistent Cloudflare resource names are unique across environments,
- Hetzner runtime databases and artifact roots are unique across environments,
- each environment's GitHub Actions secret prefix matches its environment,
- release workflows document which environment they target,
- runbooks include migration, smoke, disable, backup, and restore steps for the
  target environment.

The production readiness gate in `docs/production-readiness.md` requires this
validation before `staging-ready` or `production-ready` status can be claimed.

## Provisioning Checklist

For each new environment:

1. Create the Cloudflare resources named in the manifest.
2. Store the resulting D1 and KV resource IDs in the environment-specific
   Worker configuration or deployment variables.
3. Create the environment-specific GitHub Actions secrets.
4. Apply Cloudflare D1 migrations and seed only the intended environment.
5. Bootstrap the Hetzner runtime database, owner role, and artifact root for
   the target environment.
6. Run Control API auth checks, retrieval smoke, AI Gateway smoke, live runtime
   gate, Postgres concurrency smoke, and retention dry-run.
7. Record the evidence through `.github/workflows/production-readiness.yml`.

Provisioning is complete only when all checks pass for that environment without
using another environment's secrets, database, buckets, indexes, queues, or
artifact root.
