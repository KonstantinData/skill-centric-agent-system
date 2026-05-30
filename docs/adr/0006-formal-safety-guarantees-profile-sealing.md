# ADR-0006: Formal Safety Guarantees for Profile Sealing and Pre-Canary Gates

## Status

Accepted

## Date

2026-05-30

## Context

Profile sealing and runtime governance already enforce fail-closed behavior, but
the repository lacked a single durable architecture decision that binds:

- the formal invariant model,
- executable invariant replay checks,
- shadow-evaluation drift thresholds,
- pre-canary enforcement behavior, and
- automatic rollback policy when safety regressions occur.

Without one ADR, those rules could drift across docs, scripts, CI workflows,
and release evidence without a clear contract for change control.

## Decision

Adopt a formal-safety package with mandatory executable gates:

1. **Invariant contract**
   - Canonical invariant catalog in `docs/policies/formal-safety-invariants.md`.
   - Change-type matrix in
     `policies/runtime/formal-safety-change-type-matrix.json`.

2. **Executable invariant checks**
   - `scripts/runtime/invariant_check.py` is a required CI and production-readiness gate.
   - Replay fixtures are versioned and deterministic.

3. **Shadow-evaluation and thresholds**
   - Candidate descriptor/policy versions are evaluated in shadow mode against trace snapshots.
   - Quantitative thresholds are enforced through
     `policies/runtime/shadow-regression-thresholds.json`.

4. **Pre-canary enforcement**
   - Canary readiness requires both invariant-check and shadow-threshold gates to pass.
   - Failure output must include explicit reasons and remediation paths.

5. **Automatic rollback controls**
   - Failed pre-canary gate triggers rollback policy evaluation.
   - Rollback targets must be signed and verified last-known-good descriptor/policy versions.

6. **Incident-locked regressions**
   - Confirmed incidents must become never-again fixtures bound to invariant IDs and
     change-type expectations.

## Consequences

Positive:

- Formal safety logic is executable and auditable, not narrative-only.
- Release decisions fail closed on missing, malformed, or failing evidence.
- Governance rules for pre-canary promotion and rollback become deterministic.
- Incident learnings are codified as permanent regression fixtures.

Tradeoffs:

- Governance workflows now require additional policy/fixture maintenance.
- CI and release-evidence workflows carry more gate logic and artifacts.
- Threshold and rollback policy updates require disciplined review to avoid
  accidental over-permissiveness.

## Follow-Up

- Extend shadow-evaluation inputs from reference snapshots to live environment
  snapshots as part of broader production readiness work.
- Keep incident-locked regressions current for every confirmed safety drift.
- Review threshold baselines periodically as workload mix and task taxonomy evolve.
