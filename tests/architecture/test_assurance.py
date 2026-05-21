"""Architecture tests for TaskAssuranceSignals, TaskAssurancePolicy, GateVerdict.

Pure unit tests — no AG2, no OpenAI, no I/O.
All signal values are constructed explicitly; nothing is LLM-generated.
"""
from __future__ import annotations

import pytest

from src.orchestration.assurance import (
    ASSURANCE_SCHEMA_VERSION,
    ASSURANCE_WEIGHTS_VERSION,
    LTM_BONUS_ENABLED,
    LTM_CONFIDENCE_BONUS,
    LTM_PRECISION_FLOOR,
    AssuranceShadowRecord,
    CriticDeltaRecord,
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
    unknown_source_dates_policy: str = "neutral",
) -> TaskAssurancePolicy:
    return TaskAssurancePolicy(
        task_key=task_key,
        auto_accept_allowed=auto_accept_allowed,
        critic_required_below=critic_required_below,
        judge_required_on=judge_required_on or frozenset(),
        required_source_types=required_source_types,
        criticality=criticality,  # type: ignore[arg-type]
        policy_version=policy_version,
        unknown_source_dates_policy=unknown_source_dates_policy,  # type: ignore[arg-type]
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
        assert p.unknown_source_dates_policy == "neutral"

    def test_critic_threshold_out_of_range_raises(self):
        with pytest.raises(ValueError, match="critic_required_below"):
            _policy(critic_required_below=1.5)

    def test_critic_threshold_negative_raises(self):
        with pytest.raises(ValueError, match="critic_required_below"):
            _policy(critic_required_below=-0.1)

    def test_unknown_source_dates_policy_penalize(self):
        p = _policy(unknown_source_dates_policy="penalize")
        assert p.unknown_source_dates_policy == "penalize"

    def test_unknown_source_dates_policy_default_is_neutral(self):
        p = _policy()
        assert p.unknown_source_dates_policy == "neutral"


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

    def test_ltm_bonus_disabled_in_shadow_mode(self):
        """LTM_BONUS_ENABLED=False: LTM hit with high precision must not change score."""
        assert LTM_BONUS_ENABLED is False, (
            "LTM_BONUS_ENABLED must be False in shadow mode — "
            "enable only when empirical precision data is available"
        )
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
            ltm_pattern_precision=0.99,
        )
        assert _compute_confidence(with_ltm) == pytest.approx(
            _compute_confidence(base), abs=1e-6
        )

    def test_ltm_precision_floor_and_bonus_constants_are_sane(self):
        """Constants are defined even when bonus is disabled — verify they are reasonable."""
        assert 0.0 < LTM_PRECISION_FLOOR < 1.0
        assert 0.0 < LTM_CONFIDENCE_BONUS <= 0.10

    def test_ltm_bonus_capped_at_one_when_enabled(self, monkeypatch):
        """When bonus is enabled, perfect score + bonus stays at 1.0."""
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
        assert _compute_confidence(s) == 1.0

    def test_ltm_bonus_applied_when_enabled_above_floor(self, monkeypatch):
        """When bonus is enabled and precision >= floor, bonus is added."""
        monkeypatch.setattr("src.orchestration.assurance.LTM_BONUS_ENABLED", True)
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

    def test_ltm_bonus_not_applied_below_floor_even_when_enabled(self, monkeypatch):
        """Precision below floor: no bonus even when LTM_BONUS_ENABLED=True."""
        monkeypatch.setattr("src.orchestration.assurance.LTM_BONUS_ENABLED", True)
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
        assert any("critical" in r for r in verdict.reasons)

    def test_high_criticality_raises_effective_threshold(self):
        # All scores 0.87 → confidence ~0.87; high delta = +0.10 → threshold 0.85
        # 0.87 > 0.85 → auto-accept
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
        assert verdict.would_auto_accept is True

    def test_low_criticality_relaxes_effective_threshold(self):
        # All scores 0.74 → confidence ~0.74; low delta = -0.05 → threshold 0.70
        # 0.74 > 0.70 → auto-accept
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

    def test_effective_threshold_clamped_at_zero(self):
        # critic_required_below=0.02, low delta=-0.05 → raw -0.03, clamped to 0.0
        # any confidence > 0.0 auto-accepts
        s = _signals(
            required_fields_score=0.10,
            source_mix_score=0.10,
            source_freshness_score=0.10,
            contradiction_score=0.10,
            evidence_strength_score=0.10,
            task_criticality="low",
        )
        p = _policy(auto_accept_allowed=True, critic_required_below=0.02)
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

    def test_verdict_carries_all_versions(self):
        s = _signals()
        p = _policy(policy_version="2.1")
        verdict = evaluate_gate(s, p)
        assert verdict.policy_version == "2.1"
        assert verdict.scoring_version == ASSURANCE_SCHEMA_VERSION
        assert verdict.weights_version == ASSURANCE_WEIGHTS_VERSION

    def test_conflict_condition_triggers_judge(self):
        s = _signals(contradiction_score=0.20)  # below _CONFLICT_SCORE_THRESHOLD
        p = _policy(judge_required_on=frozenset({"conflict"}))
        verdict = evaluate_gate(s, p)
        assert verdict.requires_judge is True
        assert any("conflict" in r for r in verdict.reasons)

    def test_conflict_condition_does_not_trigger_above_threshold(self):
        s = _signals(contradiction_score=0.80)
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

    def test_verdict_to_dict_includes_weights_version(self):
        verdict = evaluate_gate(_signals(), _policy())
        d = verdict.to_dict()
        assert d["weights_version"] == ASSURANCE_WEIGHTS_VERSION
        assert isinstance(d["reasons"], list)
        assert isinstance(d["confidence_score"], float)
        assert isinstance(d["would_auto_accept"], bool)


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

    def test_blocking_severity_with_would_have_blocked(self):
        delta = _critic_delta(
            changed_outcome=True,
            rejected_points_count=3,
            failed_core_rules=("min_sources", "required_field_revenue"),
            critic_severity="blocking",
            would_have_blocked_auto_accept=True,
        )
        assert delta.would_have_blocked_auto_accept is True
        assert delta.critic_severity == "blocking"
        assert "min_sources" in delta.failed_core_rules

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

    def test_failed_core_rules_is_list_in_dict(self):
        delta = _critic_delta(failed_core_rules=("rule_a", "rule_b"))
        assert isinstance(delta.to_dict()["failed_core_rules"], list)


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

    def test_to_dict_with_none_delta(self):
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
        assert d["shadow_mode"] is True

    def test_to_dict_with_critic_delta_record(self):
        verdict = evaluate_gate(_signals(), _policy())
        delta = _critic_delta(
            changed_outcome=True,
            rejected_points_count=1,
            critic_severity="minor",
            would_have_blocked_auto_accept=False,
        )
        record = AssuranceShadowRecord(
            gate_verdict=verdict,
            gate_signals=_signals(),
            escalation_reason="max_retries exceeded",
            actual_critic_delta=delta,
        )
        d = record.to_dict()
        assert d["escalation_reason"] == "max_retries exceeded"
        assert d["actual_critic_delta"]["changed_outcome"] is True
        assert d["actual_critic_delta"]["critic_severity"] == "minor"

    def test_to_dict_gate_signals_complete(self):
        verdict = evaluate_gate(_signals(), _policy())
        record = AssuranceShadowRecord(
            gate_verdict=verdict,
            gate_signals=_signals(),
            escalation_reason=None,
            actual_critic_delta=None,
        )
        gs = record.to_dict()["gate_signals"]
        assert gs["schema_version"] == ASSURANCE_SCHEMA_VERSION
        assert "required_fields_score" in gs
        assert "contradiction_score" in gs
        assert "ltm_pattern_match" in gs

    def test_to_dict_gate_verdict_has_weights_version(self):
        verdict = evaluate_gate(_signals(), _policy())
        record = AssuranceShadowRecord(
            gate_verdict=verdict,
            gate_signals=_signals(),
            escalation_reason=None,
            actual_critic_delta=None,
        )
        gv = record.to_dict()["gate_verdict"]
        assert gv["weights_version"] == ASSURANCE_WEIGHTS_VERSION
