# ADR-0007: Learned Context Authority Boundary

## Status

Accepted

## Date

2026-06-02

## Context

SCAS is evolving from controlled memory retrieval toward a Brain capability that
can learn from runtime evidence, capability gaps, reflection, and evaluation
results. That learning must improve future task analysis, planning, ranking,
retrieval, and review proposals without becoming a hidden authority source.

The current safety model already requires immutable runtime profiles, versioned
modules, scoped memory, policy gates, validation, and fail-closed runtime
enforcement. A Brain layer adds a new risk: probabilistic learned context can
look like a harmless analyzer prior while indirectly widening future tools,
scopes, budgets, validators, or failure behavior.

## Decision

SCAS adopts the invariant:

```text
Learned context must not become authority.
```

Runtime learning artifacts may influence:

- retrieval ranking,
- planner hints,
- analyzer priors,
- composer candidate bias,
- golden workflow proposals,
- policy change proposals,
- scoped exception proposals.

They must not independently grant executable authority. Any increase in tools,
scopes, budgets, policy exceptions, validator removal, or failure-mode
relaxation must be represented by a separate reviewed, versioned policy-registry
artifact with explicit scope, expiry, rollback, tests, and code-owner approval.

## Influence Classes

Every Brain learning object must declare one influence class:

| Influence class | Maximum automatic effect |
| --- | --- |
| `retrieval_only` | Retrieval ordering only |
| `planner_hint` | Non-authoritative plan shaping |
| `analyzer_prior` | Task classification/risk hints only |
| `composer_candidate_bias` | Candidate ranking only, no grants |
| `golden_workflow_proposal` | Reviewable workflow-suite proposal |
| `policy_change_proposal` | Reviewable policy proposal |
| `scoped_exception_proposal` | Reviewable scoped exception proposal |

The Safety Compiler must reject any automatic path where a learned artifact
causes a non-empty authority delta without a reviewed policy artifact.

## Semantic Drift Guard

Similarity thresholds alone are insufficient because they can produce excessive
false positives and miss business-specific boundaries. SCAS therefore uses
versioned contrastive pairs as explicit negative examples for forbidden
generalizations.

The semantic drift guard checks analyzer priors and composer biases against
contrastive pairs before promotion. If a prior matches a forbidden boundary, the
compiler freezes the prior and routes the decision to human review, more
evidence, or rejection depending on the configured pair.

## Consequences

- Learned context can improve behavior without becoming a hidden capability
  grant path.
- Staging and low-risk learning cannot automatically generalize into production
  or high-risk authority.
- Brain promotion requires deterministic evidence, schema validation, and
  replayable contrastive tests.
- The system gains another governance artifact that must be maintained alongside
  safety invariants and release gates.

## Implementation Requirements

- Add `schemas/contrastive-pair.schema.json`.
- Add `policies/runtime/semantic-drift-guard.json`.
- Add a deterministic validator for contrastive pair structure and matching
  semantics.
- Add tests proving that staging budget gaps do not automatically generalize to
  production authority.
- Add backlog items for runtime integration, red-team coverage, and UI/reporting
  surfaces.
