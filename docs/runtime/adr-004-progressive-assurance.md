# ADR-004: Progressive Assurance Shadow Mode

Status: Draft

Date: 2026-05-21

## Context

The current runtime runs Critic and Judge always-on for every department task,
regardless of evidence quality, task complexity, or output completeness.
This pattern has two costs:

1. **Financial** — Critic and Judge use `medium`/`high` reasoning budgets
   (ADR-003). At current run volume they account for a disproportionate share
   of token spend on tasks where the research output is already clean.

2. **Latency** — GroupChat rounds for Critic/Judge add wall-clock time even
   when Researcher output is unambiguous.

Before any agent is disabled we need empirical data: how many tasks *would*
auto-accept under a signal-based gate, and how often would the Critic have
found a real problem anyway?

ADR-004 introduces a **shadow mode**: the gate is computed on every run, but
Critic continues to run always-on. The gate verdict and the Critic outcome are
stored side-by-side so the two can be compared offline.

## Non-Goals

- Researcher logic consolidation (four department copies → one shared skill).
  Related, but out of scope for ADR-004.
- Activating the fast path. No agents are disabled in this ADR.
- Tuning signal weights or policy thresholds. Shadow data drives that decision.

## Decision

Introduce four new typed structures:

1. `TaskAssuranceSignals` — evidence-derived confidence signals per task attempt.
2. `TaskAssurancePolicy` — per-`task_key` gate configuration.
3. `GateVerdict` — deterministic output of gate evaluation.
4. `CriticDeltaRecord` — minimal structured diff between gate verdict and
   actual Critic outcome. This is the primary dataset for shadow-mode analysis.

Extend the existing `TaskReviewArtifact` with an `AssuranceShadowRecord` that
attaches all four to every Critic review.

## Confidence is not LLM-asserted

`TaskAssuranceSignals` scores are computed from observable artifact properties
only. An LLM may not produce or modify any signal field.

| Signal | Source |
|--------|--------|
| `required_fields_score` | fraction of required fields populated in `TaskArtifact.payload` |
| `source_mix_score` | distribution of primary/secondary source types |
| `source_freshness_score` | recency of cited sources; see unknown-date fallback below |
| `contradiction_score` | inverted: 1.0 = no contradictions, 0.0 = severe conflict |
| `evidence_strength_score` | depth and corroboration of evidence facts |

**Contradiction score note:** `contradiction_score` is only deterministic when
contradictions are already structured in the artifact (e.g., as a
`ContractViolation` list). When no structured detection is available,
callers must use an explicit neutral value (0.5) rather than defaulting to 1.0.
A default of 1.0 would silently suppress critic escalation for tasks where
contradictions simply were not checked.

**Source freshness fallback:** When source publication dates are unknown,
callers compute `source_freshness_score` according to
`TaskAssurancePolicy.unknown_source_dates_policy`:

- `"neutral"` — unknown dates contribute 0.5 (no penalty, no bonus).
- `"penalize"` — unknown dates contribute 0.0 (conservative).

## LTM pattern match rule

`ltm_pattern_match=True` is recorded in shadow mode but **does not boost
confidence** until empirical precision metrics from measured recall data are
available in the LTM store.

Rationale: deriving `ltm_pattern_precision` from an uncalibrated match score
creates false assurance. The bonus is implemented (`LTM_CONFIDENCE_BONUS=0.05`,
`LTM_PRECISION_FLOOR=0.70`) but gated behind `LTM_BONUS_ENABLED=False`. It
will be activated in a follow-on ADR once precision is backed by eval data.

When the bonus is active, the structural compatibility check (task_key,
department, pattern_type, source_strategy) remains a prerequisite — a
high-precision match on an incompatible pattern is treated as context only.

## Gate evaluation

```
confidence = weighted_sum(signals)        # LTM bonus currently disabled

effective_threshold = clamp(
    policy.critic_required_below + criticality_delta(signals.task_criticality),
    0.0, 1.0
)

requires_critic  = (task_criticality == "critical")
                   OR (confidence < effective_threshold)
would_auto_accept = policy.auto_accept_allowed AND NOT requires_critic
requires_judge   = any evaluable judge_condition is triggered by signals
```

Criticality deltas applied to `critic_required_below`:

| criticality | delta  | note                                  |
|-------------|--------|---------------------------------------|
| `low`       | −0.05  | slightly relaxed threshold            |
| `medium`    | 0.00   | no change                             |
| `high`      | +0.10  | stricter threshold                    |
| `critical`  | —      | `requires_critic = True` unconditionally |

The `critical` case is an explicit branch, not a delta, so that
`confidence = 1.0` does not slip through when
`effective_threshold = min(1.0, 0.75 + 1.0) = 1.0`.

Signal weights (version `1.0`):

| signal | weight |
|--------|--------|
| `required_fields_score` | 0.30 |
| `source_mix_score` | 0.20 |
| `contradiction_score` | 0.20 |
| `source_freshness_score` | 0.15 |
| `evidence_strength_score` | 0.15 |

## Versioning

Every `GateVerdict` carries three version strings:

- `scoring_version` — schema version of `TaskAssuranceSignals` (signal field set).
- `weights_version` — version of `_SIGNAL_WEIGHTS` used during scoring.
- `policy_version` — version of the `TaskAssurancePolicy` that produced the verdict.

Two runs with the same `TaskAssuranceSignals` are only directly comparable when
all three versions match.

## CriticDeltaRecord

Minimal structured diff between the gate verdict and the actual Critic outcome.
Fields are chosen to answer the core shadow-mode question:
*"Would the Critic have blocked an auto-accept that the gate allowed?"*

```
CriticDeltaRecord:
  changed_outcome:               bool       # did Critic change the task outcome?
  rejected_points_count:         int        # number of points Critic rejected
  failed_core_rules:             tuple[str] # core contract rules the Critic flagged
  critic_severity:               none | minor | major | blocking
  would_have_blocked_auto_accept: bool      # the key shadow-mode signal
```

`actual_critic_delta: None` is allowed while the diff wire-up is not yet
implemented in the runtime, but the field is typed as `CriticDeltaRecord | None`
to signal the intent.

## Judge conditions evaluable from signals

| condition | evaluable from signals? | trigger |
|-----------|------------------------|---------|
| `conflict` | yes | `contradiction_score < 0.40` |
| `critical_decision` | yes | `task_criticality == "critical"` |
| `max_retries` | **no** — runtime state | recorded in `escalation_reason` |
| `ambiguity` | **no** — requires Critic output | recorded in `escalation_reason` |

## StepReasoningPolicy coupling (ADR-003)

Prepared but not enforced in this ADR:

| gate path | reasoning effort |
|-----------|-----------------|
| `would_auto_accept` | `none` / `low` |
| `requires_critic` | `medium` |
| `requires_judge` | `high` |

## Consequences

**Positive**

- Gate logic is deterministic and fully testable without AG2 or OpenAI.
- Audit and trace chain is preserved: every task has a `TaskReviewArtifact`
  with an attached `AssuranceShadowRecord`.
- `CriticDeltaRecord` makes the shadow dataset queryable from day one.
- Versioning (`scoring_version`, `weights_version`, `policy_version`) ensures
  cross-run comparability.
- LTM bonus is disabled until precision is empirically measured — no false
  assurance from uncalibrated pattern scores.

**Negative / risks**

- Shadow mode adds serialization overhead per task.
- `CriticDeltaRecord` diff requires runtime wire-up; `actual_critic_delta`
  will be `None` until that is done.
- `contradiction_score` and `source_freshness_score` require caller discipline:
  callers must not default to 1.0 for unknown states.

## Implementation

- `src/orchestration/assurance.py`
- `tests/architecture/test_assurance.py`

## Related

- ADR-001: RuntimeStep contract
- ADR-003: RoleModelProfile and StepReasoningPolicy
