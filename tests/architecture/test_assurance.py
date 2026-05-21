"""Architecture tests for the ADR-004 assurance gate.

Pure unit tests — no AG2, no OpenAI, no I/O.
"""
from __future__ import annotations

import pytest

from src.orchestration.assurance import (
    ASSURANCE_SCHEMA_VERSION,
    ASSURANCE_WEIGHTS_VERSION,
    LTM_BONUS_ENABLED,
    LTM_CONFIDENCE_BONUS,
    AssuranceShadowRecord,
    CriticDeltaRecord,
    GateVerdict,
    TaskAssurancePolicy,
    TaskAssuranceSignals,
    _compute_confidence,
    _resolve_score,
    evaluate_gate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _signals(
    *,
    required_fields_score: float | None = 0.90,
    source_mix_score: float | None = 0.85,
    source_freshness_score: float | None = 0.80,
    contradiction_score: float | None = 0.90,
    evidence_strength_score: float | None = 0.85,
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
    preferred_source_types: tuple[str, ...] = (),
    minimum_source_count: int = 0,
    criticality: str = "medium",
    policy_version: str = "1.0",
    unknown_source_dates_policy: str = "neutral",
    ltm_precision_floor: float = 0.70,
) -> TaskAssurancePolicy:
    return TaskAssurancePolicy(
        task_key=task_key,
        auto_accept_allowed=auto_accept_allowed,
        critic_required_below=critic_required_below,
        judge_required_on=judge_required_on or frozenset(),
        required_source_types=required_source_types,
        preferred_source_types=preferred_source_types,
        minimum_source_count=minimum_source_count,
        criticality=criticality,  # type: ignore[arg-type]
        policy_version=policy_version,
        unknown_source_dates_policy=unknown_source_dates_policy,  # type: ignore[arg-type]
        ltm_precision_floor=ltm_precision_floor,
    )


def _critic_delta(
    *,
    changed_outcome: bool = False,
    rejected_points_count: int = 0,
    failed_core_rules: tuple[str, ...] = (),
    critic_severity: str = "none",
    would_have_blocked_auto_accept: bool = False,
) -> CriticDeltaRecord:
    return CriticDeltaRecord(
        changed_outcome=changed_outcome,
        rejected_points_count=rejected_points_count,
        failed_core_rules=failed_core_rules,
        critic_severity=critic_severity,  # type: ignore[arg-type]
        would_have_blocked_auto_accept=would_have_blocked_auto_accept,
    )


# ---------------------------------------------------------------------------
# _resolve_score
# ---------------------------------------------------------------------------

class TestResolveScore:
    def test_float_passthrough(self):
        assert _resolve_score(0.8) == 0.8

    def test_zero_passthrough(self):
        assert _resolve_score(0.0) == 0.0

    def test_none_returns_neutral(self):
        from src.orchestration.assurance import _UNKNOWN_SCORE_NEUTRAL
        assert _resolve_score(None) == _UNKNOWN_SCORE_NEUTRAL


# ---------------------------------------------------------------------------
# TaskAssuranceSignals validation
# ---------------------------------------------------------------------------

class TestTaskAssuranceSignals:
    def test_valid_construction_all_floats(self):
        s = _signals()
        assert s.schema_version == ASSURANCE_SCHEMA_VERSION
        assert s.task_criticality == "medium"

    def test_valid_construction_all_none(self):
        s = _signals(
            required_fields_score=None,
            source_mix_score=None,
            source_freshness_score=None,
            contradiction_score=None,
            evidence_strength_score=None,
        )
        assert s.required_fields_score is None
        assert s.contradiction_score is None

    def test_mixed_none_and_float(self):
        s = _signals(contradiction_score=None, required_fields_score=0.80)
        assert s.contradiction_score is None
        assert s.required_fields_score == 0.80

    @pytest.mark.parametrize("field,value", [
        ("required_fields_score", -0.01),
        ("required_fields_score", 1.01),
        ("source_mix_score", 1.5),
        ("contradiction_score", -0.001),
        ("evidence_strength_score", 2.0),
    ])
    def test_out_of_range_float_raises(self, field, value):
        with pytest.raises(ValueError, match=field):
            _signals(**{field: value})

    def test_ltm_match_requires_precision(self):
        with pytest.raises(ValueError, match="ltm_pattern_precision must be provided"):
            _signals(ltm_pattern_match=True, ltm_pattern_precision=None)

    def test_ltm_no_match_forbids_precision(self):
        with pytest.raises(ValueError, match="ltm_pattern_precision must be None"):
            _signals(ltm_pattern_match=False, ltm_pattern_precision=0.80)

    def test_ltm_precision_out_of_range(self):
        with pytest.raises(ValueError, match="ltm_pattern_precision must be in"):
            _signals(ltm_pattern_match=True, ltm_pattern_precision=1.01)


# ---------------------------------------------------------------------------
# TaskAssurancePolicy validation
# ---------------------------------------------------------------------------

class TestTaskAssurancePolicy:
    def test_valid_construction_defaults(self):
        p = _policy()
        assert p.unknown_source_dates_policy == "neutral"
        assert p.minimum_source_count == 0
        assert p.preferred_source_types == ()
        assert p.ltm_precision_floor == 0.70

    def test_preferred_source_types(self):
        p = _policy(preferred_source_types=("primary",))
        assert "primary" in p.preferred_source_types

    def test_minimum_source_count(self):
        p = _policy(minimum_source_count=3)
        assert p.minimum_source_count == 3

    def test_minimum_source_count_negative_raises(self):
        with pytest.raises(ValueError, match="minimum_source_count"):
            _policy(minimum_source_count=-1)

    def test_critic_threshold_out_of_range_raises(self):
        with pytest.raises(ValueError, match="critic_required_below"):
            _policy(critic_required_below=1.5)

    def test_ltm_precision_floor_out_of_range_raises(self):
        with pytest.raises(ValueError, match="ltm_precision_floor"):
            _policy(ltm_precision_floor=1.1)

    def test_per_policy_ltm_floor(self):
        p = _policy(ltm_precision_floor=0.85)
        assert p.ltm_precision_floor == 0.85


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
        score, _ = _compute_confidence(s, _policy())
        assert score == 1.0

    def test_all_zero_scores_yield_zero(self):
        s = _signals(
            required_fields_score=0.0,
            source_mix_score=0.0,
            source_freshness_score=0.0,
            contradiction_score=0.0,
            evidence_strength_score=0.0,
        )
        score, _ = _compute_confidence(s, _policy())
        assert score == 0.0

    def test_none_scores_use_neutral_not_zero(self):
        all_none = _signals(
            required_fields_score=None,
            source_mix_score=None,
            source_freshness_score=None,
            contradiction_score=None,
            evidence_strength_score=None,
        )
        score, _ = _compute_confidence(all_none, _policy())
        assert score == pytest.approx(0.5, abs=1e-6)

    def test_none_score_differs_from_zero_score(self):
        none_s = _signals(contradiction_score=None)
        zero_s = _signals(contradiction_score=0.0)
        none_score, _ = _compute_confidence(none_s, _policy())
        zero_score, _ = _compute_confidence(zero_s, _policy())
        assert none_score > zero_score

    def test_ltm_bonus_disabled_in_shadow_mode(self):
        assert LTM_BONUS_ENABLED is False, (
            "LTM_BONUS_ENABLED must remain False until empirical precision data exists"
        )
        base = _signals()
        with_ltm = _signals(ltm_pattern_match=True, ltm_pattern_precision=0.99)
        base_score, base_applied = _compute_confidence(base, _policy())
        ltm_score, ltm_applied = _compute_confidence(with_ltm, _policy())
        assert ltm_score == pytest.approx(base_score, abs=1e-6)
        assert ltm_applied is False
        assert base_applied is False

    def test_ltm_bonus_applied_when_enabled_above_per_policy_floor(self, monkeypatch):
        monkeypatch.setattr("src.orchestration.assurance.LTM_BONUS_ENABLED", True)
        p = _policy(ltm_precision_floor=0.70)
        base = _signals()
        with_ltm = _signals(ltm_pattern_match=True, ltm_pattern_precision=0.70)
        base_score, _ = _compute_confidence(base, p)
        ltm_score, ltm_applied = _compute_confidence(with_ltm, p)
        assert ltm_score == pytest.approx(base_score + LTM_CONFIDENCE_BONUS, abs=1e-6)
        assert ltm_applied is True

    def test_ltm_bonus_not_applied_below_per_policy_floor(self, monkeypatch):
        monkeypatch.setattr("src.orchestration.assurance.LTM_BONUS_ENABLED", True)
        p = _policy(ltm_precision_floor=0.85)
        base = _signals()
        with_ltm = _signals(ltm_pattern_match=True, ltm_pattern_precision=0.84)
        base_score, _ = _compute_confidence(base, p)
        ltm_score, ltm_applied = _compute_confidence(with_ltm, p)
        assert ltm_score == pytest.approx(base_score, abs=1e-6)
        assert ltm_applied is False

    def test_ltm_bonus_capped_at_one(self, monkeypatch):
        monkeypatch.setattr("src.orchestration.assurance.LTM_BONUS_ENABLED", True)
        s = _signals(
            required_fields_score=1.0,
            source_mix_score=1.0,
            source_freshness_score=1.0,
            contradiction_score=1.0,
            evidence_strength_score=1.0,
            ltm_pattern_match=True,
            ltm_pattern_precision=0.99,
        )
        score, _ = _compute_confidence(s, _policy())
        assert score == 1.0


# ---------------------------------------------------------------------------
# evaluate_gate — core logic
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
        verdict = evaluate_gate(s, _policy(auto_accept_allowed=True, critic_required_below=0.75))
        assert verdict.would_auto_accept is True
        assert verdict.requires_critic is False
        assert verdict.requires_judge is False

    def test_low_confidence_requires_critic(self):
        s = _signals(
            required_fields_score=0.30,
            source_mix_score=0.30,
            source_freshness_score=0.30,
            contradiction_score=0.30,
            evidence_strength_score=0.30,
        )
        verdict = evaluate_gate(s, _policy(auto_accept_allowed=True, critic_required_below=0.75))
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
        verdict = evaluate_gate(s, _policy(auto_accept_allowed=False))
        assert verdict.would_auto_accept is False
        assert "auto_accept disabled by policy" in verdict.reasons

    def test_critical_task_forces_critic(self):
        s = _signals(
            required_fields_score=1.0,
            source_mix_score=1.0,
            source_freshness_score=1.0,
            contradiction_score=1.0,
            evidence_strength_score=1.0,
            task_criticality="critical",
        )
        verdict = evaluate_gate(s, _policy(auto_accept_allowed=True))
        assert verdict.requires_critic is True
        assert verdict.would_auto_accept is False
        assert verdict.effective_threshold == 1.0

    def test_high_criticality_raises_threshold(self):
        # confidence ~0.87; high delta +0.10 → threshold 0.85; 0.87 > 0.85
        s = _signals(**{f: 0.87 for f in [
            "required_fields_score", "source_mix_score", "source_freshness_score",
            "contradiction_score", "evidence_strength_score",
        ]}, task_criticality="high")
        verdict = evaluate_gate(s, _policy(critic_required_below=0.75))
        assert verdict.would_auto_accept is True
        assert verdict.effective_threshold == pytest.approx(0.85, abs=1e-6)

    def test_low_criticality_relaxes_threshold(self):
        # confidence ~0.74; low delta -0.05 → threshold 0.70; 0.74 > 0.70
        s = _signals(**{f: 0.74 for f in [
            "required_fields_score", "source_mix_score", "source_freshness_score",
            "contradiction_score", "evidence_strength_score",
        ]}, task_criticality="low")
        verdict = evaluate_gate(s, _policy(critic_required_below=0.75))
        assert verdict.would_auto_accept is True

    def test_effective_threshold_clamped_at_zero(self):
        s = _signals(**{f: 0.10 for f in [
            "required_fields_score", "source_mix_score", "source_freshness_score",
            "contradiction_score", "evidence_strength_score",
        ]}, task_criticality="low")
        verdict = evaluate_gate(s, _policy(critic_required_below=0.02))
        assert verdict.effective_threshold == 0.0
        assert verdict.would_auto_accept is True

    def test_gate_is_deterministic(self):
        s, p = _signals(), _policy()
        assert evaluate_gate(s, p) == evaluate_gate(s, p)

    def test_verdict_stores_confidence_score(self):
        s, p = _signals(), _policy()
        expected, _ = _compute_confidence(s, p)
        assert evaluate_gate(s, p).confidence_score == pytest.approx(expected, abs=1e-6)

    def test_verdict_carries_all_three_versions(self):
        verdict = evaluate_gate(_signals(), _policy(policy_version="2.1"))
        assert verdict.policy_version == "2.1"
        assert verdict.scoring_version == ASSURANCE_SCHEMA_VERSION
        assert verdict.weights_version == ASSURANCE_WEIGHTS_VERSION

    def test_verdict_exposes_effective_threshold(self):
        verdict = evaluate_gate(_signals(), _policy(critic_required_below=0.75))
        assert verdict.effective_threshold == pytest.approx(0.75, abs=1e-6)

    def test_ltm_bonus_applied_flag_in_verdict(self, monkeypatch):
        monkeypatch.setattr("src.orchestration.assurance.LTM_BONUS_ENABLED", True)
        s = _signals(ltm_pattern_match=True, ltm_pattern_precision=0.80)
        verdict = evaluate_gate(s, _policy())
        assert verdict.ltm_bonus_applied is True

    def test_ltm_bonus_not_applied_flag_when_disabled(self):
        s = _signals(ltm_pattern_match=True, ltm_pattern_precision=0.99)
        verdict = evaluate_gate(s, _policy())
        assert verdict.ltm_bonus_applied is False


# ---------------------------------------------------------------------------
# evaluate_gate — the would_auto_accept bug fix
# ---------------------------------------------------------------------------

class TestAutoAcceptRequiresJudgeClear:
    """would_auto_accept must be False whenever requires_judge is True.

    Previously would_auto_accept was computed before requires_judge, so a
    high-confidence task with a judge condition could return
    would_auto_accept=True even when the judge was required.
    """

    def test_auto_accept_blocked_when_judge_required(self):
        # High confidence — would auto-accept without judge condition.
        s = _signals(
            required_fields_score=0.95,
            source_mix_score=0.95,
            source_freshness_score=0.95,
            contradiction_score=0.20,   # triggers conflict condition
            evidence_strength_score=0.95,
        )
        p = _policy(
            auto_accept_allowed=True,
            critic_required_below=0.75,
            judge_required_on=frozenset({"conflict"}),
        )
        verdict = evaluate_gate(s, p)
        assert verdict.requires_judge is True
        assert verdict.would_auto_accept is False

    def test_auto_accept_allowed_when_judge_condition_not_triggered(self):
        s = _signals(
            required_fields_score=0.95,
            source_mix_score=0.95,
            source_freshness_score=0.95,
            contradiction_score=0.90,   # above conflict threshold
            evidence_strength_score=0.95,
        )
        p = _policy(
            auto_accept_allowed=True,
            critic_required_below=0.75,
            judge_required_on=frozenset({"conflict"}),
        )
        verdict = evaluate_gate(s, p)
        assert verdict.requires_judge is False
        assert verdict.would_auto_accept is True

    def test_judge_conditions_triggered_in_verdict(self):
        s = _signals(contradiction_score=0.20)
        p = _policy(judge_required_on=frozenset({"conflict"}))
        verdict = evaluate_gate(s, p)
        assert "conflict" in verdict.judge_conditions_triggered

    def test_no_conditions_triggered_is_empty_frozenset(self):
        verdict = evaluate_gate(_signals(), _policy())
        assert verdict.judge_conditions_triggered == frozenset()

    def test_critical_decision_triggers_judge_for_critical_task(self):
        s = _signals(task_criticality="critical")
        p = _policy(judge_required_on=frozenset({"critical_decision"}))
        verdict = evaluate_gate(s, p)
        assert "critical_decision" in verdict.judge_conditions_triggered
        assert verdict.requires_judge is True
        assert verdict.would_auto_accept is False

    def test_critical_decision_does_not_trigger_for_low_task(self):
        s = _signals(task_criticality="low")
        p = _policy(judge_required_on=frozenset({"critical_decision"}))
        verdict = evaluate_gate(s, p)
        assert verdict.requires_judge is False

    def test_conflict_not_triggered_when_contradiction_score_is_none(self):
        # None contradiction_score → we cannot detect a conflict from signals.
        s = _signals(contradiction_score=None)
        p = _policy(judge_required_on=frozenset({"conflict"}))
        verdict = evaluate_gate(s, p)
        assert verdict.requires_judge is False


# ---------------------------------------------------------------------------
# GateVerdict serialization
# ---------------------------------------------------------------------------

class TestGateVerdictToDict:
    def test_all_keys_present(self):
        verdict = evaluate_gate(_signals(), _policy())
        d = verdict.to_dict()
        expected_keys = {
            "would_auto_accept", "requires_critic", "requires_judge", "reasons",
            "effective_threshold", "judge_conditions_triggered", "ltm_bonus_applied",
            "policy_version", "scoring_version", "weights_version", "confidence_score",
        }
        assert set(d.keys()) == expected_keys

    def test_judge_conditions_triggered_is_sorted_list(self):
        s = _signals(contradiction_score=0.10, task_criticality="critical")
        p = _policy(judge_required_on=frozenset({"conflict", "critical_decision"}))
        d = evaluate_gate(s, p).to_dict()
        assert isinstance(d["judge_conditions_triggered"], list)
        assert d["judge_conditions_triggered"] == sorted(d["judge_conditions_triggered"])

    def test_reasons_is_list(self):
        d = evaluate_gate(_signals(), _policy()).to_dict()
        assert isinstance(d["reasons"], list)


# ---------------------------------------------------------------------------
# CriticDeltaRecord
# ---------------------------------------------------------------------------

class TestCriticDeltaRecord:
    def test_valid_construction(self):
        delta = _critic_delta()
        assert delta.changed_outcome is False
        assert delta.rejected_points_count == 0
        assert delta.failed_core_rules == ()
        assert delta.critic_severity == "none"
        assert delta.would_have_blocked_auto_accept is False

    def test_negative_rejected_points_raises(self):
        with pytest.raises(ValueError, match="rejected_points_count"):
            _critic_delta(rejected_points_count=-1)

    def test_blocking_severity(self):
        delta = _critic_delta(
            changed_outcome=True,
            rejected_points_count=3,
            failed_core_rules=("min_sources", "required_field_revenue"),
            critic_severity="blocking",
            would_have_blocked_auto_accept=True,
        )
        assert delta.would_have_blocked_auto_accept is True
        assert delta.critic_severity == "blocking"

    def test_to_dict_round_trips(self):
        delta = _critic_delta(
            changed_outcome=True,
            rejected_points_count=2,
            failed_core_rules=("required_field_revenue",),
            critic_severity="major",
            would_have_blocked_auto_accept=True,
        )
        d = delta.to_dict()
        assert d["changed_outcome"] is True
        assert d["rejected_points_count"] == 2
        assert d["failed_core_rules"] == ["required_field_revenue"]
        assert d["critic_severity"] == "major"
        assert d["would_have_blocked_auto_accept"] is True

    def test_failed_core_rules_serialized_as_list(self):
        delta = _critic_delta(failed_core_rules=("rule_a", "rule_b"))
        assert isinstance(delta.to_dict()["failed_core_rules"], list)


# ---------------------------------------------------------------------------
# AssuranceShadowRecord
# ---------------------------------------------------------------------------

class TestAssuranceShadowRecord:
    def test_shadow_mode_default_true(self):
        record = AssuranceShadowRecord(
            gate_verdict=evaluate_gate(_signals(), _policy()),
            gate_signals=_signals(),
            escalation_reason=(),
            actual_critic_delta=None,
        )
        assert record.shadow_mode is True

    def test_escalation_reason_is_tuple(self):
        record = AssuranceShadowRecord(
            gate_verdict=evaluate_gate(_signals(), _policy()),
            gate_signals=_signals(),
            escalation_reason=("max_retries", "ambiguity"),
            actual_critic_delta=None,
        )
        assert record.escalation_reason == ("max_retries", "ambiguity")

    def test_to_dict_escalation_reason_is_list(self):
        record = AssuranceShadowRecord(
            gate_verdict=evaluate_gate(_signals(), _policy()),
            gate_signals=_signals(),
            escalation_reason=("max_retries",),
            actual_critic_delta=None,
        )
        assert record.to_dict()["escalation_reason"] == ["max_retries"]

    def test_to_dict_empty_escalation(self):
        record = AssuranceShadowRecord(
            gate_verdict=evaluate_gate(_signals(), _policy()),
            gate_signals=_signals(),
            escalation_reason=(),
            actual_critic_delta=None,
        )
        assert record.to_dict()["escalation_reason"] == []

    def test_to_dict_none_critic_delta(self):
        record = AssuranceShadowRecord(
            gate_verdict=evaluate_gate(_signals(), _policy()),
            gate_signals=_signals(),
            escalation_reason=(),
            actual_critic_delta=None,
        )
        assert record.to_dict()["actual_critic_delta"] is None

    def test_to_dict_with_critic_delta_record(self):
        delta = _critic_delta(
            changed_outcome=True,
            rejected_points_count=1,
            critic_severity="minor",
            would_have_blocked_auto_accept=False,
        )
        record = AssuranceShadowRecord(
            gate_verdict=evaluate_gate(_signals(), _policy()),
            gate_signals=_signals(),
            escalation_reason=("max_retries",),
            actual_critic_delta=delta,
        )
        d = record.to_dict()
        assert d["actual_critic_delta"]["changed_outcome"] is True
        assert d["actual_critic_delta"]["critic_severity"] == "minor"

    def test_gate_signals_in_dict_complete(self):
        record = AssuranceShadowRecord(
            gate_verdict=evaluate_gate(_signals(), _policy()),
            gate_signals=_signals(contradiction_score=None),
            escalation_reason=(),
            actual_critic_delta=None,
        )
        gs = record.to_dict()["gate_signals"]
        assert gs["schema_version"] == ASSURANCE_SCHEMA_VERSION
        assert gs["contradiction_score"] is None
        assert "ltm_pattern_match" in gs

    def test_gate_verdict_dict_has_weights_version(self):
        record = AssuranceShadowRecord(
            gate_verdict=evaluate_gate(_signals(), _policy()),
            gate_signals=_signals(),
            escalation_reason=(),
            actual_critic_delta=None,
        )
        assert record.to_dict()["gate_verdict"]["weights_version"] == ASSURANCE_WEIGHTS_VERSION
