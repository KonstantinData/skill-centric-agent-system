# SOTA 2026 Target Profile

## Purpose

This document defines the binding quality baseline for SCAS in 2026.
The baseline is code-first: architecture and governance exist to protect code
quality, safety, and production reliability.

## Scope

The criteria primarily apply to repository code and tests. Architecture and
operations requirements are supporting guardrails.

## Core Rules

1. Keep the runtime single-agent and composable.
2. Use explicit capability control (registry + policy + version pins).
3. Fail closed for unknown, ambiguous, or unauthorized behavior.
4. Require reproducible live evidence for production claims.
5. Prefer small, reversible, testable changes.

## Binding Code Quality Criteria

### C1 Readability

- Use clear, intention-revealing names for functions, classes, and variables.
- Keep logic easy to follow without requiring verbose comments.
- Use comments to explain why a decision exists, not to restate obvious code.

Done when:

- changed code can be understood without external explanation,
- naming communicates intent and domain meaning,
- comments capture rationale for non-obvious choices.

### C2 Maintainability

- Keep modules and functions focused on one clear responsibility.
- Minimize coupling so local changes do not create remote breakage.
- Keep runtime contracts, schemas, and docs aligned with implemented behavior.

Done when:

- each changed unit has a clear single purpose,
- dependency impact is bounded and explicit,
- related contracts/tests/docs are updated in the same change.

### C3 Simplicity

- Apply KISS: implement the simplest design that satisfies requirements.
- Apply DRY: avoid duplicated logic by extracting shared behavior.
- Do not add abstraction layers without a concrete, current need.

Done when:

- solution complexity is proportional to the requirement,
- duplicated logic is removed or intentionally justified,
- no speculative architecture is introduced.

### C4 Reliability And Testability

- Handle error paths and edge cases explicitly.
- Structure code so targeted unit/integration tests are straightforward.
- Enforce fail-closed behavior for policy, version, and capability violations.

Done when:

- relevant automated tests pass for changed behavior,
- failure handling is deterministic and observable,
- unauthorized or invalid execution paths are denied by design.

### C5 Efficiency

- Avoid unnecessary CPU, memory, network, and token usage.
- Optimize only where measurable impact exists.
- Prefer readability over micro-optimizations unless the path is performance-critical.

Done when:

- no unbounded resource path is introduced,
- material performance/cost impacts are measured and documented,
- optimizations preserve maintainability and clarity.

## Architecture And Governance Guardrails

- Every selected capability must be version-pinned in `module_versions`.
- Runtime execution must deny unselected capabilities and version mismatches.
- Graph validation must reject missing references, kind mismatches, and cycles.
- Production-ready claims require gate evidence (commit SHA, workflow runs, outcomes).
- Security-governance gates and CODEOWNERS remain mandatory for high-impact paths.

## Non-Goals

- Introduce a separate multi-agent runtime model.
- Add process overhead without measurable quality or risk reduction.
- Replace durable repository contracts with chat-only conventions.

## Change Rule

Any change affecting architecture boundaries, capability control, governance
gates, or production claims must update contracts, tests, and operational docs
in the same change.
