# Formal Safety Invariants

## Purpose

This document defines the authoritative invariant catalog for profile sealing
and pre-canary safety gates.
It provides explicit pass/fail semantics for invariants that must hold for
every runtime profile composition, validation, and execution attempt.

## Scope

The invariants in this file are mandatory for:

- runtime profile composition outputs,
- runtime profile validation checks,
- pre-canary safety gate decisions, and
- invariant replay fixtures and regression gates.

## Invariant Catalog

### `fail_closed_on_unknowns`

Definition:
Unknown tools, scopes, validators, policies, skill handlers, or module IDs are
denied by default.

Pass:
When any unknown capability is requested, composition or validation rejects the
profile and emits an explicit failure reason.

Fail:
Any unknown capability is accepted, ignored silently, or mapped to a permissive
fallback that allows execution to continue.

### `no_self_granting`

Definition:
The runtime cannot self-grant tools, scopes, policies, validators, skills,
instructions, or memory/knowledge access outside the composed profile.

Pass:
Additional capability requests trigger controlled recomposition through the
control-plane pipeline and produce a new profile generation.

Fail:
The active runtime profile is mutated in place or runtime logic directly adds
capabilities without recomposition.

### `mandatory_validators_per_change_type`

Definition:
Each change type must execute its mandatory validator set before final response
or side effects are accepted.

Pass:
Validator selection is explicit, validator execution is enforced, unknown
validator IDs fail closed, and failed validator results block acceptance.

Fail:
Required validators are skipped, unknown validators are ignored, or failed
validators are treated as warnings without blocking semantics.

### `scope_monotonicity`

Definition:
Effective runtime scopes may only stay equal or become more restrictive within
a single run attempt. Scope widening requires a new composed profile.

Pass:
In-run operations never increase tool, data, memory, or knowledge scope grants.
Wider grants are only possible through recomposition with a new profile
generation.

Fail:
Runtime logic broadens any scope grant during the active run attempt.

### `immutable_profile_after_seal`

Definition:
After profile validation and seal, the profile is immutable for the current run
attempt.

Pass:
The sealed profile content and version pins remain unchanged throughout the run.
Any change requirement creates a new profile generation and new run attempt.

Fail:
Post-seal mutation changes selected modules, version pins, limits, scopes, or
policy bindings in the active profile.

## Evidence Requirements

A completed safety slice must include:

1. repository documentation updates aligned with this catalog,
2. executable checks or tests that assert the invariant contract surface, and
3. queue/issue tracking updates that point to the next execution start item.

The invariant replay fixture corpus is versioned in:

- `examples/evaluations/formal-safety-invariant-replay-cases.json`
- `scripts/runtime/invariant_check.py` executes the corpus as a blocking check.
- `.github/workflows/ci.yml` runs `invariant_check.py` in the required PR gate.
- `.github/workflows/production-readiness.yml` records invariant-check evidence
  before certification output is built.

## Related References

- `docs/policies/contracts.md`
- `docs/policies/formal-safety-change-type-matrix.md`
- `docs/policies/shadow-evaluation-harness.md`
- `docs/policies/shadow-regression-thresholds.md`
- `docs/policies/automatic-rollback-rules.md`
- `docs/policies/runtime-contract.md`
- `docs/policies/production-readiness.md`
- `docs/roadmap/scas-execution-queue.md`
