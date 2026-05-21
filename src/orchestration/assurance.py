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
ASSURANCE_WEIGHTS_VERSION = "1.0"

TaskCriticality = Literal["low", "medium", "high", "critical"]
JudgeCondition = Literal["conflict", "max_retries", "critical_decision", "ambiguity"]
CriticSeverity = Literal["none", "minor", "major", "blocking"]

# Signal weights.  Must sum to 1.0.
# Bumping _SIGNAL_WEIGHTS requires a new ASSURANCE_WEIGHTS_VERSION.
_SIGNAL_WEIGHTS: dict[str, float] = {
    "required_fields_score":  0.30,
    "source_mix_score":       0.20,
    "contradiction_score":    0.20,  # inverted: 1.0 = no contradictions
    "source_freshness_score": 0.15,
    "evidence_strength_score": 0.15,
}

# Neutral fallback applied when a score is None (unknown/undetected).
_UNKNOWN_SCORE_NEUTRAL: float = 0.5

# LTM bonus disabled until empirical precision from eval data is available.
# Set to True in a follow-on ADR after precision is measured.
LTM_BONUS_ENABLED: bool = False
LTM_CONFIDENCE_BONUS: float = 0.05  # applied only when LTM_BONUS_ENABLED is True

# Additive adjustment to critic_required_below by criticality.
# "critical" is an unconditional branch — not a delta.
_CRITICALITY_DELTA: dict[str, float] = {
    "low":    -0.05,
    "medium":  0.00,
    "high":    0.10,
}

# contradiction_score below this value triggers the "conflict" judge condition.
_CONFLICT_SCORE_THRESHOLD: float = 0.40


@dataclass(frozen=True, slots=True)
class TaskAssuranceSignals:
    """Evidence-derived confidence signals for one task attempt.

    Score fields are ``float | None``.
    - ``float``: computed value in [0.0, 1.0].
    - ``None``: signal is unknown or not yet detectable from the artifact.
      ``_compute_confidence`` treats None as ``_UNKNOWN_SCORE_NEUTRAL`` (0.5).

    Caller discipline:
    - ``contradiction_score``: use ``None`` when contradictions are not yet
      structurally detected in the artifact.  Do NOT default to 1.0.
    - ``source_freshness_score``: apply
      ``TaskAssurancePolicy.unknown_source_dates_policy`` for sources with
      missing publication dates (neutral → 0.5, penalize → 0.0).
    """

    schema_version: str
    required_fields_score: float | None
    source_mix_score: float | None
    source_freshness_score: float | None
    contradiction_score: float | None   # 1.0 = no contradictions; 0.0 = severe conflict
    evidence_strength_score: float | None
    task_criticality: TaskCriticality
    ltm_pattern_match: bool
    ltm_pattern_precision: float | None  # None when ltm_pattern_match is False

    def __post_init__(self) -> None:
        score_fields = {
            "required_fields_score": self.required_fields_score,
            "source_mix_score": self.source_mix_score,
            "source_freshness_score": self.source_freshness_score,
            "contradiction_score": self.contradiction_score,
            "evidence_strength_score": self.evidence_strength_score,
        }
        for name, value in score_fields.items():
            if value is not None and not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be in [0.0, 1.0] or None, got {value!r}")
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
    regardless of signal quality.

    ``unknown_source_dates_policy`` instructs callers how to score sources
    with missing publication dates when computing ``source_freshness_score``:
    - ``"neutral"``  → contribute 0.5 (no penalty, no bonus)
    - ``"penalize"`` → contribute 0.0 (conservative)

    ``ltm_precision_floor`` overrides the global floor for this task,
    enabling per-task or per-department tuning once eval data exists.
    """

    task_key: str
    auto_accept_allowed: bool
    critic_required_below: float            # Critic runs when confidence < threshold
    judge_required_on: frozenset[JudgeCondition]
    required_source_types: tuple[str, ...]
    criticality: TaskCriticality
    policy_version: str
    preferred_source_types: tuple[str, ...] = ()
    minimum_source_count: int = 0
    unknown_source_dates_policy: Literal["neutral", "penalize"] = "neutral"
    ltm_precision_floor: float = 0.70       # per-policy override; default matches global

    def __post_init__(self) -> None:
        if not (0.0 <= self.critic_required_below <= 1.0):
            raise ValueError("critic_required_below must be in [0.0, 1.0]")
        if self.minimum_source_count < 0:
            raise ValueError("minimum_source_count must be >= 0")
        if not (0.0 <= self.ltm_precision_floor <= 1.0):
            raise ValueError("ltm_precision_floor must be in [0.0, 1.0]")


@dataclass(frozen=True, slots=True)
class GateVerdict:
    """Deterministic output of evaluate_gate for one (signals, policy) pair.

    ``would_auto_accept`` is True only when:
    - ``policy.auto_accept_allowed`` is True, AND
    - ``requires_critic`` is False, AND
    - ``requires_judge`` is False.

    ``effective_threshold``, ``judge_conditions_triggered``, and
    ``ltm_bonus_applied`` make the verdict self-describing for shadow analysis
    without requiring callers to re-derive internal gate state.
    """

    would_auto_accept: bool
    requires_critic: bool
    requires_judge: bool
    reasons: tuple[str, ...]
    effective_threshold: float
    judge_conditions_triggered: frozenset[JudgeCondition]
    ltm_bonus_applied: bool
    policy_version: str
    scoring_version: str
    weights_version: str
    confidence_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "would_auto_accept": self.would_auto_accept,
            "requires_critic": self.requires_critic,
            "requires_judge": self.requires_judge,
            "reasons": list(self.reasons),
            "effective_threshold": self.effective_threshold,
            "judge_conditions_triggered": sorted(self.judge_conditions_triggered),
            "ltm_bonus_applied": self.ltm_bonus_applied,
            "policy_version": self.policy_version,
            "scoring_version": self.scoring_version,
            "weights_version": self.weights_version,
            "confidence_score": self.confidence_score,
        }


@dataclass(frozen=True, slots=True)
class CriticDeltaRecord:
    """Minimal structured diff between gate verdict and actual Critic outcome.

    The primary dataset for shadow-mode analysis.  The key question answered
    by ``would_have_blocked_auto_accept``: did the Critic find a problem that
    the gate would have missed?
    """

    changed_outcome: bool
    rejected_points_count: int
    failed_core_rules: tuple[str, ...]
    critic_severity: CriticSeverity
    would_have_blocked_auto_accept: bool

    def __post_init__(self) -> None:
        if self.rejected_points_count < 0:
            raise ValueError("rejected_points_count must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed_outcome": self.changed_outcome,
            "rejected_points_count": self.rejected_points_count,
            "failed_core_rules": list(self.failed_core_rules),
            "critic_severity": self.critic_severity,
            "would_have_blocked_auto_accept": self.would_have_blocked_auto_accept,
        }


@dataclass(frozen=True, slots=True)
class AssuranceShadowRecord:
    """Shadow-mode observation record attached to a TaskReviewArtifact.

    In shadow mode the gate verdict is hypothetical — Critic always runs.
    ``actual_critic_delta`` records what the Critic actually changed.
    It is None until the diff wire-up is implemented in the runtime.

    ``escalation_reason`` is a tuple so multiple runtime conditions
    (e.g. max_retries + ambiguity) can be recorded independently.
    """

    gate_verdict: GateVerdict
    gate_signals: TaskAssuranceSignals
    escalation_reason: tuple[str, ...]       # empty tuple when no escalation
    actual_critic_delta: CriticDeltaRecord | None
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
            "escalation_reason": list(self.escalation_reason),
            "actual_critic_delta": (
                self.actual_critic_delta.to_dict()
                if self.actual_critic_delta is not None
                else None
            ),
            "shadow_mode": self.shadow_mode,
        }


def _resolve_score(value: float | None) -> float:
    """Return the score value or the neutral fallback for unknown signals."""
    return _UNKNOWN_SCORE_NEUTRAL if value is None else value


def _compute_confidence(
    signals: TaskAssuranceSignals,
    policy: TaskAssurancePolicy,
) -> tuple[float, bool]:
    """Return (confidence_score, ltm_bonus_applied).

    None scores are resolved to ``_UNKNOWN_SCORE_NEUTRAL``.
    LTM bonus uses ``policy.ltm_precision_floor`` for per-task tuning.
    Score is clamped to [0.0, 1.0].
    """
    base = (
        _SIGNAL_WEIGHTS["required_fields_score"] * _resolve_score(signals.required_fields_score)
        + _SIGNAL_WEIGHTS["source_mix_score"] * _resolve_score(signals.source_mix_score)
        + _SIGNAL_WEIGHTS["source_freshness_score"] * _resolve_score(signals.source_freshness_score)
        + _SIGNAL_WEIGHTS["contradiction_score"] * _resolve_score(signals.contradiction_score)
        + _SIGNAL_WEIGHTS["evidence_strength_score"] * _resolve_score(signals.evidence_strength_score)
    )

    ltm_bonus_applied = (
        LTM_BONUS_ENABLED
        and signals.ltm_pattern_match
        and signals.ltm_pattern_precision is not None
        and signals.ltm_pattern_precision >= policy.ltm_precision_floor
    )
    bonus = LTM_CONFIDENCE_BONUS if ltm_bonus_applied else 0.0

    return min(1.0, round(base + bonus, 6)), ltm_bonus_applied


def evaluate_gate(
    signals: TaskAssuranceSignals,
    policy: TaskAssurancePolicy,
) -> GateVerdict:
    """Evaluate the assurance gate deterministically.

    Pure function — no side effects, no I/O, no randomness.
    The same (signals, policy) pair always produces the same GateVerdict.

    ``would_auto_accept`` requires all three conditions to hold:
    - ``policy.auto_accept_allowed``
    - ``not requires_critic``
    - ``not requires_judge``

    Judge conditions evaluable from signals:
    - ``"conflict"``          when contradiction_score < _CONFLICT_SCORE_THRESHOLD
    - ``"critical_decision"`` when task_criticality == "critical"

    ``"max_retries"`` and ``"ambiguity"`` are runtime-only; capture them in
    ``AssuranceShadowRecord.escalation_reason``.
    """
    reasons: list[str] = []
    confidence, ltm_bonus_applied = _compute_confidence(signals, policy)

    # Resolve critic requirement and effective threshold.
    if signals.task_criticality == "critical":
        # Unconditional branch: critical tasks always require Critic.
        # An explicit check prevents confidence=1.0 slipping through when
        # effective_threshold would equal 1.0 via the delta path.
        requires_critic = True
        effective_threshold = 1.0
        reasons.append("critic required: task_criticality=critical")
    else:
        delta = _CRITICALITY_DELTA.get(signals.task_criticality, 0.0)
        effective_threshold = max(0.0, min(1.0, policy.critic_required_below + delta))
        requires_critic = confidence < effective_threshold
        if requires_critic:
            reasons.append(
                f"confidence {confidence:.4f} < threshold {effective_threshold:.4f}"
                f" (criticality={signals.task_criticality})"
            )

    if not policy.auto_accept_allowed:
        reasons.append("auto_accept disabled by policy")

    # Resolve judge conditions from signals.
    judge_conditions_triggered: set[JudgeCondition] = set()

    contradiction = signals.contradiction_score
    if (
        "conflict" in policy.judge_required_on
        and contradiction is not None
        and contradiction < _CONFLICT_SCORE_THRESHOLD
    ):
        judge_conditions_triggered.add("conflict")
        reasons.append(
            f"judge required: conflict detected"
            f" (contradiction_score={contradiction:.4f})"
        )

    if (
        "critical_decision" in policy.judge_required_on
        and signals.task_criticality == "critical"
    ):
        judge_conditions_triggered.add("critical_decision")
        reasons.append("judge required: critical_decision + critical task")

    requires_judge = bool(judge_conditions_triggered)

    # Auto-accept requires critic AND judge to be clear.
    would_auto_accept = (
        policy.auto_accept_allowed
        and not requires_critic
        and not requires_judge
    )

    return GateVerdict(
        would_auto_accept=would_auto_accept,
        requires_critic=requires_critic,
        requires_judge=requires_judge,
        reasons=tuple(reasons),
        effective_threshold=effective_threshold,
        judge_conditions_triggered=frozenset(judge_conditions_triggered),
        ltm_bonus_applied=ltm_bonus_applied,
        policy_version=policy.policy_version,
        scoring_version=signals.schema_version,
        weights_version=ASSURANCE_WEIGHTS_VERSION,
        confidence_score=confidence,
    )
