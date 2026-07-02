# ADR-0014: Source Authority Boundaries

## Status

Accepted

## Date

2026-07-02

## Context

SCAS uses immutable runtime profiles, registry-driven composition, policy
filtering, and fail-closed validators. Those guarantees depend on clear source
authority. If files under `examples/` carry tenant definitions, skill-pack
contracts, production evidence, or control-plane seed authority, future agents
and maintainers can mistake illustrative material for source of truth.

The current repository contains legacy authority-adjacent artifacts under
`examples/`, including tenant declarations, tenant-specific CRM skill packs,
runtime evidence snapshots, operations snapshots, and control-plane seed data.
Moving all of them at once would create unnecessary risk because many tests and
docs still reference those paths.

## Decision

SCAS defines a repository source authority boundary:

- `registry/` is the authoritative home for selectable modules, registry
  records, version pins, and future tenant authority records.
- `schemas/` is the authoritative home for machine-readable contracts.
- `docs/` and `docs/adr/` are authoritative for human-readable policies,
  architecture, operational rules, and durable decisions.
- `policies/`, `migrations/`, `src/`, `workers/`, `apps/`, `packages/`, and
  `scripts/` retain their existing implementation or machine-policy authority.
- `tests/fixtures/` is the preferred location for new executable fixtures.
- `examples/` is non-authoritative and may only hold illustrative examples,
  demo payloads, schema examples, and evaluation cases.

Existing authority-adjacent files in `examples/` are grandfathered as legacy
fixtures through a closed test allowlist. The allowlist prevents new files from
being added to those authority-adjacent `examples/` areas while tenant and
evidence migrations proceed in smaller follow-up changes.

## Consequences

Positive:

- Future SCAS work has a clear rule for where tenant, registry, fixture, and
  evidence artifacts belong.
- New Liquisto skill-pack work can start in a tenant authority surface instead
  of adding more product contracts to `examples/`.
- Governance tests block accidental growth of authority-adjacent examples.
- Tenant migrations can proceed tenant by tenant without a high-risk
  repository-wide move.

Costs:

- Existing tests still read some legacy `examples/` files until migration work
  moves them.
- The governance test must be updated when a legacy authority-adjacent file is
  intentionally removed or migrated.
- Follow-up work is required to create tenant registry paths and migrate
  remaining Kinderhaus and Daskuechenhaus artifacts.

Non-goals:

- This decision does not certify all legacy tenant or skill-pack files as
  migrated.
- This decision does not certify current `examples/` authority-adjacent files as
  production authority.
- This decision does not change the single-agent runtime architecture.

## Acceptance Criteria

- A binding policy documents source authority boundaries.
- The documentation index links the policy and ADR.
- A governance test rejects new authority-adjacent files under `examples/`
  unless they are intentionally allowlisted as legacy.
- Existing tests continue to pass without tenant migration in this phase.
