# Shadow Evaluation Harness

## Purpose

This document defines the shadow-evaluation harness used to evaluate candidate
descriptor and policy versions against trace snapshots without changing active
profile-sealing decisions.

## Shadow-Only Execution Contract

The harness consumes a trace snapshot with:

- `baseline_versions` (`descriptor_version`, `policy_version`),
- `candidate_versions` (`descriptor_version`, `policy_version`), and
- `trace_events` entries containing `baseline` and `candidate` outcomes for the
  same trace.

Each trace event must include:

- `trace_id`,
- `change_type`,
- `expected_safety_violation`,
- `expected_selection_ids`,
- `baseline` (`abstained`, `mixed_profile`, `safety_violation_detected`,
  `selected_module_ids`), and
- `candidate` (same shape as `baseline`).

Malformed inputs fail closed with `status = "failed"` and explicit
`evaluation_errors`.

## Output Metrics

The harness reports:

- `decision_change_rate`,
- `abstention_rate` (`baseline`, `candidate`, `delta`),
- `mixed_profile_rate` (`baseline`, `candidate`, `delta`),
- `safety_false_negative_rate` (`baseline`, `candidate`, `delta`), and
- `selection_drift_by_change_type`:
  - precision (`baseline`, `candidate`, `delta`),
  - recall (`baseline`, `candidate`, `delta`).

These metrics are the input surface for threshold policy enforcement.
Threshold policy is defined in
`policies/runtime/shadow-regression-thresholds.json` and documented in
`docs/policies/shadow-regression-thresholds.md`.

## Memory Safety Fixtures

Memory safety regressions use the same shadow-only principle: fixture cases run
against executable gates and emit metrics without changing active runtime
authority. The memory fixture contract is
`schemas/memory-safety-evaluation.schema.json`, and the reference fixture is
`examples/evaluations/contrastive-memory-safety-fixtures.json`.

The memory safety evaluator measures false negatives, false positives,
abstention or review rate, and coverage across authority-leak classes. Covered
classes include tool grants, scope grants, policy overrides, validator
overrides, task-subject facts as memory, environment generalization, risk-level
generalization, secret or sensitive content, and conflicting lessons.

## Reference Implementation

- `src/skill_centric_agent_system/operations/shadow_evaluation.py`
- `src/skill_centric_agent_system/operations/memory_safety_evaluation.py`
- `scripts/operations/evaluate_shadow_profile_versions.py`
- `scripts/operations/evaluate_shadow_regression_thresholds.py`
- `examples/operations/shadow-eval-trace-snapshot.json`
- `examples/operations/shadow-eval-report-snapshot.json`
- `examples/evaluations/contrastive-memory-safety-fixtures.json`
- `tests/test_shadow_evaluation_harness.py`
- `tests/test_memory_safety_evaluation.py`
