"""Task-level assurance signals, policy, and gate verdict.

ADR-004: Progressive Assurance Shadow Mode.

Confidence is derived exclusively from observable evidence signals — never
from an LLM self-assessment.  The gate is a pure function: same inputs always
produce the same GateVerdict.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ASSURANCE_SCHEMA_VERSION = "1.0"

TaskCriticality = Literal["low", "medium", "high", "critical"]
JudgeCondition = Literal["conflict", "max_retries", "critical_decision", "ambiguity"]

# Signal weights for the confidence score.  Must sum to 1.0.
_SIGNAL_WEIGHTS: dict[str, float] = {
    "required_fields_score": 0.30,
    "source_mix_score":      0.20,
    "source_freshness_score": 0.15,
    "contradiction_score":   0.20,  # inverted: 1.0 = no contradictions
    "evidence_strength_score": 0.15,
}

# An LTM hit only acts as a confidence booster when precision >= this floor.
# Below the floor the match is treated as context only — not a signal.
LTM_PRECISION_FLOOR: float = 0.70
LTM_CONFIDENCE_BONUS: float = 0.05

# Additive adjustment to critic_required_below based on task criticality.
# "critical" sets the effective threshold to 1.0, forcing critic always.
_CRITICALITY_DELTA: dict[str, float] = {
    "low":      -0.05,
    "medium":    0.00,
    "high":      0.10,
    "critical":  1.00,
}

# contradiction_score below this value triggers the "conflict" judge condition.
_CONFLICT_SCORE_THRESHOLD: float = 0.40


@dataclass(frozen=True, slots=True)
class TaskAssuranceSignals:
    """Evidence-derived confidence signals for one task attempt.

    All score fields are in [0.0, 1.0].  Computed from TaskArtifact properties
    by deterministic Python — never produced or modified by an LLM.
    """

    schema_version: str
    required_fields_score: float    # fraction of required fields populated
    source_mix_score: float         # quality of primary/secondary source mix
    source_freshness_score: float   # recency of sources (1.0 = all fresh)
    contradiction_score: float      # 1.0 = no contradictions; 0.0 = severe conflict
    evidence_strength_score: float  # depth and corroboration of evidence
    task_criticality: TaskCriticality
    ltm_pattern_match: bool
    ltm_pattern_precision: float | None  # None when ltm_pattern_match is False

    def __post_init__(self) -> None:
        scores = {
            "required_fields_score": self.required_fields_score,
            "source_mix_score": self.source_mix_score,
            "source_freshness_score": self.source_freshness_score,
            "contradiction_score": self.contradiction_score,
            "evidence_strength_score": self.evidence_strength_score,
        }
        for name, value in scores.items():
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be in [0.0, 1.0], got {value!r}")
        if self.ltm_pattern_match and self.ltm_pattern_precision is None:
            raise ValueError(
                "ltm_pattern_precision must be provided when ltm_pattern_match is True"
            )
        if not self.ltm_pattern_match and self.ltm_pattern_precision is not None:
            raise ValueError(
                "ltm_pattern_precision must be None when ltm_pattern_match is False"
            )
        if self.ltm_pattern_precision is not None and not (
            0.0 <= self.ltm_pattern_precision <= 1.0
        ):
            raise ValueError("ltm_pattern_precision must be in [0.0, 1.0]")


@dataclass(frozen=True, slots=True)
class TaskAssurancePolicy:
    """Per-task gate configuration.

    ``auto_accept_allowed=False`` unconditionally disables the fast path
    regardless of signal quality — use for tasks where human or Critic review
    is contractually required.
    """

    task_key: str
    auto_accept_allowed: bool
    critic_required_below: float        # Critic runs when confidence < this
    judge_required_on: frozenset[JudgeCondition]
    required_source_types: tuple[str, ...]
    criticality: TaskCriticality
    policy_version: str

    def __post_init__(self) -> None:
        if not (0.0 <= self.critic_required_below <= 1.0):
            raise ValueError("critic_required_below must be in [0.0, 1.0]")


@dataclass(frozen=True, slots=True)
class GateVerdict:
    """Deterministic output of evaluate_gate for one (signals, policy) pair."""

    would_auto_accept: bool
    requires_critic: bool
    requires_judge: bool
    reasons: tuple[str, ...]
    policy_version: str
    scoring_version: str
    confidence_score: float  # stored for shadow-mode comparison

    def to_dict(self) -> dict[str, Any]:
        return {
            "would_auto_accept": self.would_auto_accept,
            "requires_critic": self.requires_critic,
            "requires_judge": self.requires_judge,
            "reasons": list(self.reasons),
            "policy_version": self.policy_version,
            "scoring_version": self.scoring_version,
            "confidence_score": self.confidence_score,
        }


@dataclass(frozen=True, slots=True)
class AssuranceShadowRecord:
    """Shadow-mode observation record attached to a TaskReviewArtifact.

    In shadow mode the gate verdict is hypothetical — Critic always runs.
    ``actual_critic_delta`` records what the Critic actually changed so the
    two paths can be compared offline.  It is None until the diff wire-up
    is implemented.
    """

    gate_verdict: GateVerdict
    gate_signals: TaskAssuranceSignals
    escalation_reason: str | None   # runtime conditions (e.g. max_retries)
    actual_critic_delta: str | None  # None = Critic changed nothing or not wired yet
    shadow_mode: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_verdict": self.gate_verdict.to_dict(),
            "gate_signals": {
                "schema_version": self.gate_signals.schema_version,
                "required_fields_score": self.gate_signals.required_fields_score,
                "source_mix_score": self.gate_signals.source_mix_score,
                "source_freshness_score": self.gate_signals.source_freshness_score,
                "contradiction_score": self.gate_signals.contradiction_score,
                "evidence_strength_score": self.gate_signals.evidence_strength_score,
                "task_criticality": self.gate_signals.task_criticality,
                "ltm_pattern_match": self.gate_signals.ltm_pattern_match,
                "ltm_pattern_precision": self.gate_signals.ltm_pattern_precision,
            },
            "escalation_reason": self.escalation_reason,
            "actual_critic_delta": self.actual_critic_delta,
            "shadow_mode": self.shadow_mode,
        }


def _compute_confidence(signals: TaskAssuranceSignals) -> float:
    """Return a weighted confidence score derived from evidence signals.

    LTM hits only contribute when precision >= LTM_PRECISION_FLOOR.
    Score is clamped to [0.0, 1.0].
    """
    base = (
        _SIGNAL_WEIGHTS["required_fields_score"] * signals.required_fields_score
        + _SIGNAL_WEIGHTS["source_mix_score"] * signals.source_mix_score
        + _SIGNAL_WEIGHTS["source_freshness_score"] * signals.source_freshness_score
        + _SIGNAL_WEIGHTS["contradiction_score"] * signals.contradiction_score
        + _SIGNAL_WEIGHTS["evidence_strength_score"] * signals.evidence_strength_score
    )

    ltm_bonus = 0.0
    if (
        signals.ltm_pattern_match
        and signals.ltm_pattern_precision is not None
        and signals.ltm_pattern_precision >= LTM_PRECISION_FLOOR
    ):
        ltm_bonus = LTM_CONFIDENCE_BONUS

    return min(1.0, round(base + ltm_bonus, 6))


def evaluate_gate(
    signals: TaskAssuranceSignals,
    policy: TaskAssurancePolicy,
) -> GateVerdict:
    """Evaluate the assurance gate deterministically.

    Pure function — no side effects, no I/O, no randomness.
    The same (signals, policy) pair always produces the same GateVerdict.

    Judge conditions evaluable from signals:
    - "conflict"          when contradiction_score < _CONFLICT_SCORE_THRESHOLD
    - "critical_decision" when task_criticality == "critical"

    "max_retries" and "ambiguity" are runtime-only conditions; they cannot be
    evaluated here and must be captured in AssuranceShadowRecord.escalation_reason.
    """
    reasons: list[str] = []
    confidence = _compute_confidence(signals)

    delta = _CRITICALITY_DELTA.get(signals.task_criticality, 0.0)
    effective_threshold = min(1.0, policy.critic_required_below + delta)

    # "critical" tasks always require Critic — the delta already pushes threshold
    # to 1.0, but we also use >= so a perfect score of 1.0 does not slip through.
    requires_critic = (
        signals.task_criticality == "critical"
        or confidence < effective_threshold
    )
    if requires_critic:
        reasons.append(
            f"confidence {confidence:.4f} < threshold {effective_threshold:.4f}"
            f" (criticality={signals.task_criticality})"
        )

    if not policy.auto_accept_allowed:
        reasons.append("auto_accept disabled by policy")

    would_auto_accept = policy.auto_accept_allowed and not requires_critic

    requires_judge = False
    if (
        "conflict" in policy.judge_required_on
        and signals.contradiction_score < _CONFLICT_SCORE_THRESHOLD
    ):
        requires_judge = True
        reasons.append(
            f"judge required: conflict detected"
            f" (contradiction_score={signals.contradiction_score:.4f})"
        )
    if (
        "critical_decision" in policy.judge_required_on
        and signals.task_criticality == "critical"
    ):
        requires_judge = True
        reasons.append("judge required: critical_decision + critical task")

    return GateVerdict(
        would_auto_accept=would_auto_accept,
        requires_critic=requires_critic,
        requires_judge=requires_judge,
        reasons=tuple(reasons),
        policy_version=policy.policy_version,
        scoring_version=signals.schema_version,
        confidence_score=confidence,
    )
