from __future__ import annotations

from skill_centric_agent_system.runtime.error_taxonomy import (
    apply_optional_llm_judge,
    classify_runtime_failure,
    classify_runtime_success,
)


def test_runtime_failure_classifies_policy_denial_as_r8() -> None:
    classification = classify_runtime_failure(
        error=RuntimeError("Policy denied by runtime profile."),
        stop_reason="policy_denied",
        error_code="tool_not_in_runtime_profile",
        enforcer_counters={"tool_calls": 1, "tokens_used": 100},
    )
    assert classification.error_class == "R8_POLICY_CONFLICT_CONTEXT_CONTAMINATION"
    assert classification.error_confidence == "high"


def test_runtime_failure_classifies_validation_failures_as_f2() -> None:
    classification = classify_runtime_failure(
        error=RuntimeError("Output contract validation failed."),
        stop_reason="validator_failed",
        error_code="runtime_output_contract_failed",
        enforcer_counters={"tool_calls": 2, "tokens_used": 200},
    )
    assert classification.error_class == "F2_INTERFACE_CONTRACT_BREAKDOWN"
    assert classification.error_confidence in {"medium", "high"}


def test_runtime_success_classifies_inefficient_paths_as_f1() -> None:
    classification = classify_runtime_success(
        plan={"actions": [{"tool": "git-read"}, {"tool": "filesystem-read"}]},
        execution={"tool_results": [{}] * 7},
        enforcer_counters={"tool_calls": 8, "tokens_used": 52000},
        profile_limits={"max_tokens": 60000},
    )
    assert classification.error_class == "F1_INEFFICIENCY_PATH"
    assert classification.runtime_playbook.startswith("optimize_")


class _StaticJudge:
    def __init__(self, payload: dict[str, str]) -> None:
        self.payload = payload

    def classify(self, payload: object) -> dict[str, str]:
        assert payload is not None
        return self.payload


def test_optional_llm_judge_reclassifies_low_confidence_when_enabled() -> None:
    base = classify_runtime_failure(
        error=RuntimeError("unexpected runtime error"),
        stop_reason="runtime_error",
        error_code="runtime_error",
        enforcer_counters={"tool_calls": 0, "tokens_used": 0},
    )
    assert base.error_confidence == "low"
    judged = apply_optional_llm_judge(
        base,
        enabled=True,
        judge=_StaticJudge(
            {
                "error_class": "F2_INTERFACE_CONTRACT_BREAKDOWN",
                "error_confidence": "medium",
                "runtime_playbook": "normalize_interface_retry_once_then_fail_closed",
            }
        ),
        context={"run_id": "run-1"},
    )
    assert judged.classification_source == "llm_judge_v1"
    assert judged.error_class == "F2_INTERFACE_CONTRACT_BREAKDOWN"


def test_optional_llm_judge_falls_back_when_disabled_or_invalid() -> None:
    base = classify_runtime_failure(
        error=RuntimeError("unexpected runtime error"),
        stop_reason="runtime_error",
        error_code="runtime_error",
        enforcer_counters={"tool_calls": 0, "tokens_used": 0},
    )
    disabled = apply_optional_llm_judge(
        base,
        enabled=False,
        judge=_StaticJudge(
            {
                "error_class": "R8_POLICY_CONFLICT_CONTEXT_CONTAMINATION",
                "error_confidence": "high",
                "runtime_playbook": "fail_closed",
            }
        ),
        context={"run_id": "run-1"},
    )
    assert disabled == base
    invalid = apply_optional_llm_judge(
        base,
        enabled=True,
        judge=_StaticJudge(
            {
                "error_class": "INVALID",
                "error_confidence": "high",
                "runtime_playbook": "fail_closed",
            }
        ),
        context={"run_id": "run-1"},
    )
    assert invalid == base
