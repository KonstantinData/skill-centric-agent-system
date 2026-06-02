# Semantic Drift Guard

## Purpose

The semantic drift guard prevents learned context from crossing authority
boundaries through analyzer priors, planner hints, or composer candidate bias.
It is part of the Brain promotion path and applies before learned artifacts can
shape future runtime profile composition.

## Rule

Learned artifacts may improve ranking, retrieval, decomposition, and review
proposals. They must not create executable authority. A learned artifact that
would add tools, widen scopes, raise budgets, remove validators, relax failure
behavior, or create a policy exception must be routed to a reviewed policy
artifact before it can affect active profiles.

## Contrastive Pairs

The guard uses contrastive pairs: explicit negative examples for forbidden
generalizations. Each pair has:

- a positive context where the learned signal is valid,
- a forbidden generalization boundary,
- the authority delta that must not be automated,
- the expected compiler gate.

Example:

```json
{
  "pair_id": "staging-budget-gap-must-not-generalize-to-prod",
  "positive_context": {
    "environment": "staging",
    "risk_level": "medium",
    "workflow_id": "runtime-preflight-required"
  },
  "forbidden_generalization": {
    "environment": "prod",
    "risk_level": "high",
    "authority_delta": ["budget_increase"]
  },
  "expected_gate": "needs_human_review"
}
```

## Compiler Behavior

The Safety Compiler must:

1. validate the guard policy against `schemas/contrastive-pair.schema.json`,
2. compare proposed analyzer priors or composer biases against every contrastive
   pair,
3. block automatic promotion when a forbidden boundary matches,
4. emit a machine-readable decision with the matching `pair_id`,
5. require reviewed policy artifacts for any non-empty authority delta.

The runtime implementation lives in
`src/skill_centric_agent_system/runtime/safety_compiler.py`. The Brain promotion
path can pass learned authority priors into the memory candidate validator; when
the compiler returns a blocking gate, the candidate remains non-promotable and
the policy reason records the matched contrastive pair IDs.

Capability-gap learning uses the same boundary. Runtime denials may emit
non-executable `CapabilityGapCandidate` artifacts only when the denial comes
from deterministic policy, scope, budget, tool, or validator predicates. Secret
denials and unknown-tool denials are excluded from learning, and every candidate
requires reviewed Brain promotion before it can affect future composition.

Allowed decisions are:

- `allow_ranking_only`,
- `freeze_prior`,
- `needs_human_review`,
- `needs_more_evidence`,
- `reject`.

## Non-Goals

The guard does not decide whether a new capability is business-useful. It only
prevents learned context from becoming an implicit authority source. Business
continuity remains covered by golden workflows, replay checks, and reviewed
exceptions.

## Contract Artifacts

- `schemas/contrastive-pair.schema.json`
- `schemas/capability-gap-candidate.schema.json`
- `policies/runtime/semantic-drift-guard.json`
- `scripts/runtime/validate_semantic_drift_guard.py`
- `src/skill_centric_agent_system/runtime/capability_gaps.py`
- `docs/adr/0007-learned-context-authority-boundary.md`
