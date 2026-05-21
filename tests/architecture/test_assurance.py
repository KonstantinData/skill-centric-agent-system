"""Architecture tests for TaskAssuranceSignals, TaskAssurancePolicy, GateVerdict.

Pure unit tests — no AG2, no OpenAI, no I/O.
All signal values are constructed explicitly; nothing is LLM-generated.
"""
from __future__ import annotations

import pytest

from src.orchestration.assurance import (
    ASSURANCE_SCHEMA_VERSION,
    LTM_CONFIDENCE_BONUS,
    LTM_PRECISION_FLOOR,
    AssuranceShadowRecord,
    GateVerdict,
    TaskAssurancePolicy,
    TaskAssuranceSignals,
    _compute_confidence,
    evaluate_gate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _signals(
    *,
    required_fields_score: float = 0.90,
    source_mix_score: float = 0.85,
    source_freshness_score: float = 0.80,
    contradiction_score: float = 0.90,
    evidence_strength_score: float = 0.85,
    task_criticality: str = "medium",
    ltm_pattern_match: bool = False,
    ltm_pattern_precision: float | None = None,
) -> TaskAssuranceSignals:
    return TaskAssuranceSignals(
        schema_version=ASSURANCE_SCHEMA_VERSION,
        required_fields_score=required_fields_score,
        source_mix_score=source_mix_score,
        source_freshness_score=source_freshness_score,
        contradiction_score=contradiction_score,
        evidence_strength_score=evidence_strength_score,
        task_criticality=task_criticality,  # type: ignore[arg-type]
        ltm_pattern_match=ltm_pattern_match,
        ltm_pattern_precision=ltm_pattern_precision,
    )


def _policy(
    *,
    task_key: str = "company_overview",
    auto_accept_allowed: bool = True,
    critic_required_below: float = 0.75,
    judge_required_on: frozenset | None = None,
    required_source_types: tuple[str, ...] = ("primary", "secondary"),
    criticality: str = "medium",
    policy_version: str = "1.0",
) -> TaskAssurancePolicy:
    return TaskAssurancePolicy(
        task_key=task_key,
        auto_accept_allowed=auto_accept_allowed,
        critic_required_below=critic_required_below,
        judge_required_on=judge_required_on or frozenset(),
        required_source_types=required_source_types,
        criticality=criticality,  # type: ignore[arg-type]
        policy_version=policy_version,
    )


# ---------------------------------------------------------------------------
# TaskAssuranceSignals validation
# ---------------------------------------------------------------------------

class TestTaskAssuranceSignals:
    def test_valid_construction(self):
        s = _signals()
        assert s.schema_version == ASSURANCE_SCHEMA_VERSION
        assert s.task_criticality == "medium"
        assert s.ltm_pattern_match is False
        assert s.ltm_pattern_precision is None

    @pytest.mark.parametrize("field,value", [
        ("required_fields_score", -0.01),
        ("required_fields_score", 1.01),
        ("source_mix_score", -0.01),
        ("contradiction_score", 1.001),
        ("evidence_strength_score", 2.0),
    ])
    def test_score_out_of_range_raises(self, field, value):
        with pytest.raises(ValueError, match=field):
            _signals(**{field: value})

    def test_ltm_match_requires_precision(self):
        with pytest.raises(ValueError, match="ltm_pattern_precision must be provided"):
            _signals(ltm_pattern_match=True, ltm_pattern_precision=None)

    def test_ltm_no_match_forbids_precision(self):
        with pytest.raises(ValueError, match="ltm_pattern_precision must be None"):
            _signals(ltm_pattern_match=False, ltm_pattern_precision=0.80)

    def test_ltm_precision_out_of_range_raises(self):
        with pytest.raises(ValueError, match="ltm_pattern_precision must be in"):
            _signals(ltm_pattern_match=True, ltm_pattern_precision=1.01)

    def test_ltm_match_with_valid_precision(self):
        s = _signals(ltm_pattern_match=True, ltm_pattern_precision=0.80)
        assert s.ltm_pattern_match is True
        assert s.ltm_pattern_precision == 0.80


# ---------------------------------------------------------------------------
# TaskAssurancePolicy validation
# ---------------------------------------------------------------------------

class TestTaskAssurancePolicy:
    def test_valid_construction(self):
        p = _policy()
        assert p.task_key == "company_overview"
        assert p.auto_accept_allowed is True
        assert p.critic_required_below == 0.75

    def test_critic_threshold_out_of_range_raises(self):
        with pytest.raises(ValueError, match="critic_required_below"):
            _policy(critic_required_below=1.5)

    def test_critic_threshold_negative_raises(self):
        with pytest.raises(ValueError, match="critic_required_below"):
            _policy(critic_required_below=-0.1)


# ---------------------------------------------------------------------------
# _compute_confidence
# ---------------------------------------------------------------------------

class TestComputeConfidence:
    def test_all_perfect_scores_yield_one(self):
        s = _signals(
            required_fields_score=1.0,
            source_mix_score=1.0,
            source_freshness_score=1.0,
            contradiction_score=1.0,
            evidence_strength_score=1.0,
        )
        assert _compute_confidence(s) == 1.0

    def test_all_zero_scores_yield_zero(self):
        s = _signals(
            required_fields_score=0.0,
            source_mix_score=0.0,
            source_freshness_score=0.0,
            contradiction_score=0.0,
            evidence_strength_score=0.0,
        )
        assert _compute_confidence(s) == 0.0

    def test_ltm_bonus_applied_above_precision_floor(self):
        base = _signals(
            required_fields_score=0.80,
            source_mix_score=0.80,
            source_freshness_score=0.80,
            contradiction_score=0.80,
            evidence_strength_score=0.80,
        )
        with_ltm = _signals(
            required_fields_score=0.80,
            source_mix_score=0.80,
            source_freshness_score=0.80,
            contradiction_score=0.80,
            evidence_strength_score=0.80,
            ltm_pattern_match=True,
            ltm_pattern_precision=LTM_PRECISION_FLOOR,
        )
        assert _compute_confidence(with_ltm) == pytest.approx(
            _compute_confidence(base) + LTM_CONFIDENCE_BONUS, abs=1e-6
        )

    def test_ltm_bonus_not_applied_below_precision_floor(self):
        base = _signals(
            required_fields_score=0.80,
            source_mix_score=0.80,
            source_freshness_score=0.80,
            contradiction_score=0.80,
            evidence_strength_score=0.80,
        )
        low_precision = _signals(
            required_fields_score=0.80,
            source_mix_score=0.80,
            source_freshness_score=0.80,
            contradiction_score=0.80,
            evidence_strength_score=0.80,
            ltm_pattern_match=True,
            ltm_pattern_precision=LTM_PRECISION_FLOOR - 0.01,
        )
        assert _compute_confidence(low_precision) == pytest.approx(
            _compute_confidence(base), abs=1e-6
        )

    def test_ltm_bonus_capped_at_one(self):
        s = _signals(
            required_fields_score=1.0,
            source_mix_score=1.0,
            source_freshness_score=1.0,
            contradiction_score=1.0,
            evidence_strength_score=1.0,
            ltm_pattern_match=True,
            ltm_pattern_precision=0.99,
        )
        assert _compute_confidence(s) == 1.0


# ---------------------------------------------------------------------------
# evaluate_gate
# ---------------------------------------------------------------------------

class TestEvaluateGate:
    def test_high_confidence_auto_accepts(self):
        s = _signals(
            required_fields_score=0.95,
            source_mix_score=0.90,
            source_freshness_score=0.90,
            contradiction_score=0.95,
            evidence_strength_score=0.90,
        )
        p = _policy(auto_accept_allowed=True, critic_required_below=0.75)
        verdict = evaluate_gate(s, p)
        assert verdict.would_auto_accept is True
        assert verdict.requires_critic is False

    def test_low_confidence_requires_critic(self):
        s = _signals(
            required_fields_score=0.30,
            source_mix_score=0.30,
            source_freshness_score=0.30,
            contradiction_score=0.30,
            evidence_strength_score=0.30,
        )
        p = _policy(auto_accept_allowed=True, critic_required_below=0.75)
        verdict = evaluate_gate(s, p)
        assert verdict.would_auto_accept is False
        assert verdict.requires_critic is True

    def test_auto_accept_disabled_blocks_fast_path(self):
        s = _signals(
            required_fields_score=1.0,
            source_mix_score=1.0,
            source_freshness_score=1.0,
            contradiction_score=1.0,
            evidence_strength_score=1.0,
        )
        p = _policy(auto_accept_allowed=False, critic_required_below=0.75)
        verdict = evaluate_gate(s, p)
        assert verdict.would_auto_accept is False
        assert "auto_accept disabled by policy" in verdict.reasons

    def test_critical_criticality_forces_critic(self):
        # Even perfect signals: critical criticality raises threshold to 1.0+
        s = _signals(
            required_fields_score=1.0,
            source_mix_score=1.0,
            source_freshness_score=1.0,
            contradiction_score=1.0,
            evidence_strength_score=1.0,
            task_criticality="critical",
        )
        p = _policy(auto_accept_allowed=True, critic_required_below=0.75)
        verdict = evaluate_gate(s, p)
        assert verdict.requires_critic is True
        assert verdict.would_auto_accept is False

    def test_high_criticality_raises_effective_threshold(self):
        # confidence ~0.87 (all scores 0.87), threshold 0.75 + 0.10 = 0.85
        # With high criticality, 0.87 > 0.85 so auto-accept should pass
        s = _signals(
            required_fields_score=0.87,
            source_mix_score=0.87,
            source_freshness_score=0.87,
            contradiction_score=0.87,
            evidence_strength_score=0.87,
            task_criticality="high",
        )
        p = _policy(auto_accept_allowed=True, critic_required_below=0.75)
        verdict = evaluate_gate(s, p)
        # effective threshold = 0.75 + 0.10 = 0.85; confidence ~0.87 > 0.85
        assert verdict.would_auto_accept is True

    def test_low_criticality_relaxes_effective_threshold(self):
        # confidence ~0.74 (just below 0.75), but low criticality gives -0.05
        # effective threshold = 0.70; 0.74 > 0.70 → auto-accept
        s = _signals(
            required_fields_score=0.74,
            source_mix_score=0.74,
            source_freshness_score=0.74,
            contradiction_score=0.74,
            evidence_strength_score=0.74,
            task_criticality="low",
        )
        p = _policy(auto_accept_allowed=True, critic_required_below=0.75)
        verdict = evaluate_gate(s, p)
        assert verdict.would_auto_accept is True

    def test_gate_is_deterministic(self):
        s = _signals()
        p = _policy()
        assert evaluate_gate(s, p) == evaluate_gate(s, p)

    def test_verdict_stores_confidence_score(self):
        s = _signals()
        p = _policy()
        verdict = evaluate_gate(s, p)
        assert verdict.confidence_score == pytest.approx(_compute_confidence(s), abs=1e-6)

    def test_verdict_carries_versions(self):
        s = _signals()
        p = _policy(policy_version="2.1")
        verdict = evaluate_gate(s, p)
        assert verdict.policy_version == "2.1"
        assert verdict.scoring_version == ASSURANCE_SCHEMA_VERSION

    def test_conflict_condition_triggers_judge(self):
        s = _signals(contradiction_score=0.20)  # below _CONFLICT_SCORE_THRESHOLD
        p = _policy(judge_required_on=frozenset({"conflict"}))
        verdict = evaluate_gate(s, p)
        assert verdict.requires_judge is True
        assert any("conflict" in r for r in verdict.reasons)

    def test_conflict_condition_does_not_trigger_above_threshold(self):
        s = _signals(contradiction_score=0.80)  # well above threshold
        p = _policy(judge_required_on=frozenset({"conflict"}))
        verdict = evaluate_gate(s, p)
        assert verdict.requires_judge is False

    def test_critical_decision_triggers_judge_for_critical_tasks(self):
        s = _signals(task_criticality="critical")
        p = _policy(
            auto_accept_allowed=True,
            critic_required_below=0.75,
            judge_required_on=frozenset({"critical_decision"}),
        )
        verdict = evaluate_gate(s, p)
        assert verdict.requires_judge is True
        assert any("critical_decision" in r for r in verdict.reasons)

    def test_critical_decision_does_not_trigger_for_low_tasks(self):
        s = _signals(task_criticality="low")
        p = _policy(judge_required_on=frozenset({"critical_decision"}))
        verdict = evaluate_gate(s, p)
        assert verdict.requires_judge is False

    def test_no_judge_conditions_returns_false(self):
        s = _signals(contradiction_score=0.10, task_criticality="critical")
        p = _policy(judge_required_on=frozenset())
        verdict = evaluate_gate(s, p)
        assert verdict.requires_judge is False

    def test_verdict_to_dict_is_serializable(self):
        verdict = evaluate_gate(_signals(), _policy())
        d = verdict.to_dict()
        assert isinstance(d["reasons"], list)
        assert isinstance(d["confidence_score"], float)
        assert isinstance(d["would_auto_accept"], bool)


# ---------------------------------------------------------------------------
# AssuranceShadowRecord
# ---------------------------------------------------------------------------

class TestAssuranceShadowRecord:
    def test_shadow_mode_default_is_true(self):
        verdict = evaluate_gate(_signals(), _policy())
        record = AssuranceShadowRecord(
            gate_verdict=verdict,
            gate_signals=_signals(),
            escalation_reason=None,
            actual_critic_delta=None,
        )
        assert record.shadow_mode is True

    def test_to_dict_round_trips_key_fields(self):
        verdict = evaluate_gate(_signals(), _policy())
        record = AssuranceShadowRecord(
            gate_verdict=verdict,
            gate_signals=_signals(),
            escalation_reason="max_retries exceeded",
            actual_critic_delta="critic added two missing_points",
        )
        d = record.to_dict()
        assert d["shadow_mode"] is True
        assert d["escalation_reason"] == "max_retries exceeded"
        assert d["actual_critic_delta"] == "critic added two missing_points"
        assert d["gate_signals"]["schema_version"] == ASSURANCE_SCHEMA_VERSION
        assert isinstance(d["gate_verdict"]["confidence_score"], float)

    def test_actual_critic_delta_none_allowed(self):
        verdict = evaluate_gate(_signals(), _policy())
        record = AssuranceShadowRecord(
            gate_verdict=verdict,
            gate_signals=_signals(),
            escalation_reason=None,
            actual_critic_delta=None,
        )
        d = record.to_dict()
        assert d["actual_critic_delta"] is None
        assert d["escalation_reason"] is None
