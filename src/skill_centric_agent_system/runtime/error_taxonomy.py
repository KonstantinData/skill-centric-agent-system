from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol, cast

ErrorClass = Literal[
    "F1_INEFFICIENCY_PATH",
    "F2_INTERFACE_CONTRACT_BREAKDOWN",
    "R8_POLICY_CONFLICT_CONTEXT_CONTAMINATION",
    "NONE",
]

ClassificationSource = Literal["rule_based_runtime_v1", "llm_judge_v1"]
LLM_CLASSIFICATION_SOURCE: ClassificationSource = "llm_judge_v1"


@dataclass(frozen=True)
class ErrorClassification:
    error_class: ErrorClass
    error_confidence: str
    classification_source: ClassificationSource
    error_evidence: dict[str, Any]
    runtime_playbook: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "error_class": self.error_class,
            "error_confidence": self.error_confidence,
            "classification_source": self.classification_source,
            "error_evidence": self.error_evidence,
            "runtime_playbook": self.runtime_playbook,
        }


class ErrorClassificationJudge(Protocol):
    def classify(self, payload: Mapping[str, Any]) -> Mapping[str, Any] | None: ...


def classify_runtime_failure(
    *,
    error: Exception,
    stop_reason: str,
    error_code: str | None,
    enforcer_counters: Mapping[str, int],
) -> ErrorClassification:
    message = str(error).casefold()
    normalized_code = (error_code or "").casefold()

    if stop_reason == "policy_denied" or "policy" in normalized_code:
        return ErrorClassification(
            error_class="R8_POLICY_CONFLICT_CONTEXT_CONTAMINATION",
            error_confidence="high",
            classification_source="rule_based_runtime_v1",
            error_evidence={
                "stop_reason": stop_reason,
                "error_code": error_code,
                "message": str(error),
                "signal": "policy_denied_or_policy_gate",
            },
            runtime_playbook=(
                "fail_closed_and_emit_policy_conflict_event_then_request_policy_or_prompt_cleanup"
            ),
        )

    if (
        stop_reason == "validator_failed"
        or "contract" in message
        or "schema" in message
        or "validation" in message
    ):
        return ErrorClassification(
            error_class="F2_INTERFACE_CONTRACT_BREAKDOWN",
            error_confidence="medium",
            classification_source="rule_based_runtime_v1",
            error_evidence={
                "stop_reason": stop_reason,
                "error_code": error_code,
                "message": str(error),
                "signal": "validator_or_contract_failure",
            },
            runtime_playbook="normalize_interface_retry_once_then_fail_closed",
        )

    return ErrorClassification(
        error_class="NONE",
        error_confidence="low",
        classification_source="rule_based_runtime_v1",
        error_evidence={
            "stop_reason": stop_reason,
            "error_code": error_code,
            "message": str(error),
            "tool_calls": int(enforcer_counters.get("tool_calls", 0)),
            "tokens_used": int(enforcer_counters.get("tokens_used", 0)),
        },
        runtime_playbook="generic_runtime_error_path",
    )


def classify_runtime_success(
    *,
    plan: Mapping[str, Any],
    execution: Mapping[str, Any],
    enforcer_counters: Mapping[str, int],
    profile_limits: Mapping[str, Any],
) -> ErrorClassification:
    actions = plan.get("actions", [])
    action_count = len(actions) if isinstance(actions, list) else 0
    tool_result_count = len(execution.get("tool_results", [])) if isinstance(
        execution.get("tool_results", []), list
    ) else 0
    tool_calls = int(enforcer_counters.get("tool_calls", 0))
    tokens_used = int(enforcer_counters.get("tokens_used", 0))
    max_tokens = int(profile_limits.get("max_tokens", 0))

    inefficiency_signals = [
        tool_calls > max(2, action_count * 2),
        tool_result_count > max(2, action_count * 2),
        max_tokens > 0 and tokens_used > int(max_tokens * 0.75),
    ]
    is_inefficient = sum(1 for signal in inefficiency_signals if signal) >= 2

    if is_inefficient:
        return ErrorClassification(
            error_class="F1_INEFFICIENCY_PATH",
            error_confidence="medium",
            classification_source="rule_based_runtime_v1",
            error_evidence={
                "action_count": action_count,
                "tool_calls": tool_calls,
                "tool_result_count": tool_result_count,
                "tokens_used": tokens_used,
                "max_tokens": max_tokens,
            },
            runtime_playbook="optimize_plan_and_tool_selection_before_next_run",
        )

    return ErrorClassification(
        error_class="NONE",
        error_confidence="high",
        classification_source="rule_based_runtime_v1",
        error_evidence={
            "action_count": action_count,
            "tool_calls": tool_calls,
            "tokens_used": tokens_used,
        },
        runtime_playbook="no_action_required",
    )


def apply_optional_llm_judge(
    base: ErrorClassification,
    *,
    enabled: bool,
    judge: ErrorClassificationJudge | None,
    context: Mapping[str, Any],
) -> ErrorClassification:
    if not enabled:
        return base
    if base.error_confidence != "low":
        return base
    if judge is None:
        return base

    raw = judge.classify(
        {
            "base_classification": base.as_dict(),
            "context": dict(context),
        }
    )
    if not isinstance(raw, Mapping):
        return base

    error_class = raw.get("error_class")
    error_confidence = raw.get("error_confidence")
    runtime_playbook = raw.get("runtime_playbook")
    if (
        not isinstance(error_class, str)
        or error_class
        not in {
            "F1_INEFFICIENCY_PATH",
            "F2_INTERFACE_CONTRACT_BREAKDOWN",
            "R8_POLICY_CONFLICT_CONTEXT_CONTAMINATION",
            "NONE",
        }
        or error_confidence not in {"low", "medium", "high"}
        or not isinstance(runtime_playbook, str)
    ):
        return base

    evidence = raw.get("error_evidence")
    if not isinstance(evidence, Mapping):
        evidence = {}
    merged_evidence = {**base.error_evidence, "llm_judge_evidence": dict(evidence)}

    return ErrorClassification(
        error_class=cast(ErrorClass, error_class),
        error_confidence=error_confidence,
        classification_source=LLM_CLASSIFICATION_SOURCE,
        error_evidence=merged_evidence,
        runtime_playbook=runtime_playbook,
    )
