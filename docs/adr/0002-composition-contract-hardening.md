# ADR-0002: Composition Contract Hardening Before Runtime Implementation

## Status

Accepted

## Date

2026-05-21

## Context

ADR-0001 establishes a self-composing single-agent runtime. A review of the foundation exposed several contract gaps that would make the implementation difficult to validate:

- module scoring was underspecified and could collapse into keyword matching,
- the Task Analyzer had no explicit output contract,
- runtime profiles referenced modules without version pins,
- recomposition traceability was only a follow-up note,
- execution limits covered tool calls but not tokens, duration, data reads, memory operations, or recomposition count,
- registry dependency graphs, auth/authz, failure semantics, and early observability were not yet contractual.

These concerns affect the safety and reproducibility of the system, so they must be resolved before broad runtime code is written.

## Decision

Harden the composition contracts before choosing the implementation stack or building registries and runtime loops.

The module metadata contract now separates weak textual triggers from structured selection inputs:

- `capability_class`,
- `domain_tags`,
- `task_signals`,
- `selection.base_score`,
- `selection.score_modifiers`,
- `selection.requires_all_policies`.

The runtime profile contract now includes:

- profile version and generation,
- `parent_profile_id` and `recomposition_reason`,
- explicit `auth_context`,
- `module_versions` pins for selected modules,
- expanded execution limits,
- failure policy,
- minimum observability settings.

Human-readable contracts define Task Analyzer output, registry query semantics, scoring, graph validation, auth/authz, failure handling, and observability baseline.

## Consequences

Positive:

- Composition can be tested independently of the runtime implementation.
- Profiles become reproducible because selected modules are version-pinned.
- Recomposition is traceable instead of becoming hidden permission expansion.
- Registry and scorer implementations have a concrete target contract.
- Debugging starts earlier because traces are part of the profile contract.

Tradeoffs:

- Initial examples and schemas are more verbose.
- Registry and Composer code must validate cross-field consistency that JSON Schema cannot express alone.
- Future schema changes need migration discipline once persisted profiles exist.

## Follow-Up

- Add executable contract tests after the stack decision.
- Define concrete scoring thresholds and tie-break behavior in the Composer implementation.
- Add graph validation tests for circular policy, validator, tool, and scope dependencies.
