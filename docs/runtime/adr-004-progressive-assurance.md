# ADR-004: Progressive Assurance Shadow Mode

Status: Draft

Date: 2026-05-21

## Context

The current runtime runs Critic and Judge always-on for every department task,
regardless of evidence quality, task complexity, or output completeness.
This pattern has three costs:

1. **Financial** — Critic and Judge use `medium`/`high` reasoning budgets
   (ADR-003). At current run volume, they account for a disproportionate share
   of token spend on tasks where the research output is already clean.

2. **Latency** — GroupChat rounds for Critic/Judge add wall-clock time even
   when Researcher output is unambiguous.

3. **Maintainability** — Researcher logic is replicated four times (one per
   department). Any change to evidence-scoring or source-quality rules must be
   applied in four places.

Before any agent is disabled, we need empirical data: how many tasks *would*
auto-accept under a signal-based gate, and how often would the Critic have
found a real problem anyway?

ADR-004 introduces a **shadow mode**: the gate is computed on every run, but
Critic continues to run always-on. The gate verdict is stored alongside the
Critic result so the two can be compared offline.

## Decision

Introduce three new typed structures:

1. `TaskAssuranceSignals` — evidence-derived confidence signals per task attempt.
2. `TaskAssurancePolicy` — per-`task_key` gate configuration.
3. `GateVerdict` — deterministic output of gate evaluation.

Extend the existing `TaskReviewArtifact` with an `AssuranceShadowRecord` that
attaches the verdict and signals to every Critic review.

**No agents are disabled in this ADR.** The gate decides *hypothetically*.
The shadow record's `actual_critic_delta` field records what the Critic actually
changed — this is the primary dataset for the follow-on decision.

## Confidence is not LLM-asserted

`TaskAssuranceSignals` scores are computed from observable artifact properties
only:

- `required_fields_score` — fraction of required fields populated in the
  `TaskArtifact` payload.
- `source_mix_score` — quality of primary/secondary source distribution.
- `source_freshness_score` — recency of cited sources.
- `contradiction_score` — inverted: 1.0 = no contradictions detected,
  0.0 = severe unresolved conflict.
- `evidence_strength_score` — depth and corroboration of evidence facts.

An LLM may not produce or modify any signal field. Signals are computed by
deterministic Python from the `TaskArtifact`.

## LTM pattern match rule

`ltm_pattern_match=True` only acts as a confidence booster when:

- `ltm_pattern_precision >= LTM_PRECISION_FLOOR` (0.70), **and**
- the matched pattern's `task_key`, `department`, `pattern_type`, and
  `source_strategy` are structurally compatible with the current task.

Below the precision floor, an LTM hit is treated as context only — it does not
raise the confidence score. This prevents stale or low-quality memory patterns
from silently bypassing the gate.

## Gate evaluation

```
confidence = weighted_sum(signals) + ltm_bonus_if_qualified

effective_threshold = policy.critic_required_below
                    + criticality_delta(signals.task_criticality)

requires_critic  = confidence < effective_threshold
would_auto_accept = policy.auto_accept_allowed AND NOT requires_critic
requires_judge   = any evaluable judge_condition is triggered by signals
```

Criticality deltas:

| criticality | delta  | effect                           |
|-------------|--------|----------------------------------|
| `low`       | −0.05  | slightly relaxed threshold       |
| `medium`    | 0.00   | no change                        |
| `high`      | +0.10  | stricter threshold               |
| `critical`  | +1.00  | threshold → 1.0; critic always   |

Judge conditions evaluable from signals (shadow mode only):

- `"conflict"` — triggered when `contradiction_score < 0.40`.
- `"critical_decision"` — triggered when `task_criticality == "critical"`.

`"max_retries"` and `"ambiguity"` are runtime-only conditions; they cannot be
evaluated from signals alone and are recorded in `escalation_reason` at
runtime.

## StepReasoningPolicy coupling (ADR-003)

Gate verdict maps to reasoning effort:

| path             | effort   |
|------------------|----------|
| would_auto_accept | `none` / `low` (deterministic export) |
| requires_critic  | `medium` |
| requires_judge   | `high`   |

This coupling is *not* enforced in this ADR — it is a preparation for the
follow-on ADR that activates the fast path.

## Shadow Mode Observation Schema

Every `AssuranceShadowRecord` persists:

- `gate_verdict` — full `GateVerdict` including `confidence_score`.
- `gate_signals` — the `TaskAssuranceSignals` that produced the verdict.
- `escalation_reason` — why Critic/Judge ran despite a potential auto-accept
  verdict (runtime conditions such as `max_retries`).
- `actual_critic_delta` — structured diff of what the Critic changed relative
  to the `TaskArtifact`. `None` if Critic ran but changed nothing.
- `shadow_mode=True` — gate is hypothetical; Critic always runs.

## Consequences

**Positive**

- Gate logic is deterministic and fully testable without AG2.
- Audit and trace chain is preserved: every task has a `TaskReviewArtifact`
  regardless of the gate verdict.
- Shadow data enables data-driven activation of the fast path in a follow-on ADR.
- `required_source_types` in `TaskAssurancePolicy` makes source expectations
  explicit and machine-checkable per task.

**Negative / risks**

- Shadow mode adds a small amount of serialization overhead per task.
- LTM precision floor is a fixed constant (0.70). It may need per-department
  tuning based on observed match quality.
- `actual_critic_delta` requires a diff implementation that does not yet exist
  in the runtime; the field is `None` until that is wired.

## Implementation

- `src/orchestration/assurance.py` — `TaskAssuranceSignals`, `TaskAssurancePolicy`,
  `GateVerdict`, `AssuranceShadowRecord`, `evaluate_gate`.
- `tests/architecture/test_assurance.py` — pure unit tests; no AG2 dependency.

## Related

- ADR-001: RuntimeStep contract
- ADR-003: RoleModelProfile and StepReasoningPolicy
