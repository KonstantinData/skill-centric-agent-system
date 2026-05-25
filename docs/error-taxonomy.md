# Error Taxonomy (F1/F2/R8)

## Purpose

This document defines a runtime and evaluation taxonomy for high-signal failures
and regressions:

- `F1_INEFFICIENCY_PATH`: The task outcome is functionally correct, but the
  runtime path is inefficient (excess tool calls, turns, or token usage).
- `F2_INTERFACE_CONTRACT_BREAKDOWN`: Data handoff or output contracts break
  between planner/executor/validator boundaries.
- `R8_POLICY_CONFLICT_CONTEXT_CONTAMINATION`: Policy conflicts or context
  contamination cause policy denials or contradictory behavior.

The taxonomy is additive to existing stop reasons. Stop reasons remain runtime
control signals; taxonomy classes are analysis signals used by evaluators,
gates, and scoring feedback.

## Contract

The machine-readable contract lives in:

- `schemas/error-classification.schema.json`

Every classified runtime outcome records:

- `error_class`
- `error_confidence`
- `classification_source`
- `error_evidence`
- `runtime_playbook`

## Runtime Classification v1

`rule_based_runtime_v1` currently classifies outcomes as:

1. `R8` when runtime fails with `policy_denied` or policy-gate style error
   codes.
2. `F2` when runtime fails due to validator/contract/schema breakdown.
3. `F1` when runtime succeeds but deterministic inefficiency signals exceed
   thresholds.
4. `NONE` otherwise.

## Runtime Playbooks

The taxonomy includes a standard runtime playbook field:

1. `F1`: optimize plan/tool selection before the next run.
2. `F2`: normalize interface and retry once, then fail closed.
3. `R8`: fail closed immediately and emit policy-conflict evidence.
4. `NONE`: no special action.

## CI Gates

Class metrics are enforced via:

- `scripts/operations/evaluate_error_classification_gates.py`
- `examples/operations/error-classification-gate-policy.json`
- `examples/operations/error-classification-gate-snapshot.json`

Gate thresholds:

- `r8_rate_max`
- `f2_unresolved_max`
- `f1_efficiency_budget_max`

## Composer Feedback

Registry scoring accepts `TaskSignals.error_feedback` and applies
capability-class penalties based on recent taxonomy outcomes. This allows the
Composer to reduce repeated module selections that correlate with known failure
classes without bypassing policy or validation gates.
