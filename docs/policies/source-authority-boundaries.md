# Source Authority Boundaries

## Purpose

SCAS depends on explicit source authority. A runtime profile must be assembled
from governed registries, schemas, policies, and validated records, not from a
file that is only intended to illustrate a shape.

This policy defines where repository artifacts may carry authority and where
they may only act as examples or fixtures.

## Directory Authority Model

| Path | Authority | Allowed content |
|---|---|---|
| `registry/` | Authoritative | Selectable modules, version pins, lockfiles, registry metadata, and future tenant registry declarations. |
| `schemas/` | Authoritative | Machine-readable contracts that validators, tests, and runtime gates enforce. |
| `docs/` | Authoritative for human policy | Architecture, ADRs, policies, runbooks, contracts, and operational rules that must version with the code. |
| `policies/` | Authoritative | Machine-readable policy records consumed by gates, scripts, or runtime checks. |
| `migrations/` | Authoritative | Executable database and infrastructure schema changes. |
| `src/`, `workers/`, `apps/`, `packages/`, `scripts/` | Authoritative implementation | Runtime, control-plane, application, package, and automation behavior. |
| `tests/fixtures/` | Non-authoritative fixture | Test-only records. Fixtures may mirror production contracts but must not be selected by runtime composition. |
| `examples/` | Non-authoritative illustration | Small representative examples, demo payloads, schema examples, evaluation cases, and documentation aids. |
| `operations/staging-tasks/` | Approved operational input | Committed, non-secret task files approved for supervised staging operations. |

## Examples Boundary

`examples/` must not be treated as a registry, deployment source, tenant source
of truth, production evidence store, or runtime authority surface.

Allowed under `examples/`:

- minimal sample payloads for API and schema documentation,
- deterministic test fixtures when their path is explicitly treated as a
  fixture by tests,
- evaluation cases for analyzers, validators, and scoring,
- demo data that contains no production authority and no sensitive tenant data.

Not allowed under `examples/` for new work:

- authoritative tenant declarations,
- tenant-specific skill-pack contracts,
- production readiness evidence,
- production telemetry or rollback evidence,
- control-plane seed data intended for active deployment,
- runtime records that are presented as live or certified evidence.

## Fixture Boundary

If a test needs representative data, prefer `tests/fixtures/` for new fixtures.
Existing tests may continue to read legacy `examples/` fixtures during migration,
but new authority-adjacent examples must not be added there.

Fixtures must be safe to delete or regenerate. If deleting a fixture would alter
runtime capability selection, tenant access, deployment, production status, or
policy behavior, the artifact belongs outside `examples/` and outside
`tests/fixtures/`.

## Tenant Boundary

Tenant-specific authority belongs in a governed tenant registry or another
explicit tenant authority surface, not in `examples/`.

The target tenant authority shape is:

```text
registry/tenants/<tenant-id>/tenant.json
registry/tenants/<tenant-id>/ui-profile.json
registry/tenants/<tenant-id>/data-sources.json
```

Tenant configuration files define tenant identity, roles, UI bindings, data
sources, and tenant-local authority. Tenant-specific skill-pack contracts are
tenant skill authority and live under the tenant module namespace, not beside
`tenant.json`.

Current migrated tenant authority:

- `liquisto`: `registry/tenants/liquisto/tenant.json`.

Common and tenant-specific selectable modules remain under `registry/modules/`,
grouped by namespace:

```text
registry/modules/common/skills/
registry/modules/common/validators/
registry/modules/common/policies/
registry/modules/tenants/<tenant-id>/skills/
registry/modules/tenants/<tenant-id>/validators/
registry/modules/tenants/<tenant-id>/policies/
```

Tenant-specific CRM skill-pack contracts are stored as skill authority:

```text
registry/modules/tenants/<tenant-id>/skills/<skill-pack-id>/skill-pack.json
```

Current migrated tenant skill-pack authority:

- `liquisto`: `registry/modules/tenants/liquisto/skills/liquisto-research-assistance/skill-pack.json`.

## Legacy Exception Rule

Some existing files under `examples/` are authority-adjacent. They remain
temporary legacy fixtures until migrated. The governance test keeps a closed
allowlist for those paths so no new authority-adjacent files are added under
`examples/` by accident.

Adding a new path to that allowlist requires a repository decision explaining
why the artifact cannot live in `registry/`, `tests/fixtures/`, `operations/`,
or another authoritative location.

## Acceptance

This policy is satisfied when:

1. `examples/` is documented as non-authoritative.
2. New authority-adjacent files under `examples/` fail a governance test unless
   explicitly allowlisted as legacy.
3. Tenant-specific authority migrates out of `examples/` tenant by tenant.
4. Runtime composition and production gates use authoritative paths, not
   illustrative examples.
