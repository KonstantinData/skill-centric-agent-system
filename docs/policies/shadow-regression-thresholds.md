# Shadow Regression Thresholds

## Purpose

This policy defines quantitative acceptance thresholds for shadow-evaluation
drift metrics.
It is used to decide whether candidate descriptor/policy versions are eligible
for pre-canary promotion checks.

## Threshold Surface

The threshold policy in
`policies/runtime/shadow-regression-thresholds.json` controls:

- `abstention_delta_max_abs`
- `mixed_profile_rate_delta_max_abs`
- `safety_false_negative_delta_max`
- `decision_change_rate_max`

It also defines selection-drift minima by change type:

- `precision_delta_min`
- `recall_delta_min`

## Enforcement Inputs

- Shadow report generator:
  `scripts/operations/evaluate_shadow_profile_versions.py`
- Threshold evaluator:
  `scripts/operations/evaluate_shadow_regression_thresholds.py`
- Reference shadow report:
  `examples/operations/shadow-eval-report-snapshot.json`
- Reference threshold evaluation output:
  `examples/operations/shadow-regression-threshold-evaluation.json`

The evaluator fails closed when:

- required metrics are missing,
- threshold definitions are malformed,
- drift exceeds thresholds, or
- `fail_closed_on_missing_change_type` is enabled and an observed change type
  has no explicit threshold.
