from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from skill_centric_agent_system.runtime import (
    InMemoryRuntimeStore,
    MemoryCandidateValidator,
    PostPlanningMemoryInvariantValidator,
    SafetyCompiler,
)

BLOCKING_OUTCOME = "block"
ALLOWING_OUTCOME = "allow"
REVIEW_GATES = frozenset({"freeze_prior", "needs_human_review", "needs_more_evidence"})


class MemorySafetyEvaluationError(ValueError):
    """Raised when a memory safety evaluation fixture is malformed."""


def evaluate_memory_safety_fixture(
    fixture: Mapping[str, Any],
    *,
    base_path: Path | None = None,
) -> dict[str, Any]:
    """Evaluate contrastive memory safety cases against executable runtime gates."""

    cases = _required_list(fixture, "cases")
    thresholds = _required_mapping(fixture, "metrics_thresholds")
    required_failure_classes = _string_set(fixture.get("required_failure_classes"))
    policy_path = _resolve_policy_path(fixture, base_path)
    compiler = SafetyCompiler.from_policy_file(policy_path)

    results = [
        _evaluate_case(
            case,
            compiler=compiler,
            allowed_memory_scope_ids=_string_tuple(
                fixture.get("allowed_memory_scope_ids"),
                default=("project-memory",),
            ),
            allowed_policy_ids=_string_tuple(
                fixture.get("allowed_policy_ids"),
                default=("memory-taxonomy-policy",),
            ),
        )
        for case in cases
    ]
    metrics = _metrics(results)
    coverage = _coverage(results, required_failure_classes)
    passed = (
        metrics["false_negative_rate"] <= _float_threshold(thresholds, "max_false_negative_rate")
        and metrics["false_positive_rate"] <= _float_threshold(
            thresholds,
            "max_false_positive_rate",
        )
        and metrics["abstention_review_rate"] <= _float_threshold(
            thresholds,
            "max_abstention_review_rate",
        )
        and not coverage["missing_required_failure_classes"]
        and all(result["passed"] for result in results)
    )

    return {
        "contract_version": "0.1.0",
        "evaluation_id": str(fixture.get("evaluation_id", "memory-safety-evaluation")),
        "status": "passed" if passed else "failed",
        "case_count": len(results),
        "metrics": metrics,
        "coverage": coverage,
        "case_results": results,
        "safe_for_release_evidence": True,
        "raw_runtime_trace_included": False,
    }


def load_memory_safety_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise MemorySafetyEvaluationError(f"{path} must contain a JSON object.")
    return payload


def _evaluate_case(
    case: Mapping[str, Any],
    *,
    compiler: SafetyCompiler,
    allowed_memory_scope_ids: tuple[str, ...],
    allowed_policy_ids: tuple[str, ...],
) -> dict[str, Any]:
    gate = _required_string(case, "gate")
    if gate == "candidate_validation":
        outcome = _evaluate_candidate_case(
            case,
            compiler=compiler,
            allowed_memory_scope_ids=allowed_memory_scope_ids,
            allowed_policy_ids=allowed_policy_ids,
        )
    elif gate == "semantic_drift":
        outcome = _evaluate_semantic_drift_case(case, compiler=compiler)
    elif gate == "post_planning_invariant":
        outcome = _evaluate_post_planning_case(case)
    else:
        raise MemorySafetyEvaluationError(f"Unsupported memory safety gate: {gate}")

    expected_outcome = _required_string(case, "expected_outcome")
    actual_outcome = str(outcome["actual_outcome"])
    return {
        "case_id": _required_string(case, "case_id"),
        "gate": gate,
        "failure_class": _required_string(case, "failure_class"),
        "expected_outcome": expected_outcome,
        "actual_outcome": actual_outcome,
        "passed": actual_outcome == expected_outcome,
        **outcome,
    }


def _evaluate_candidate_case(
    case: Mapping[str, Any],
    *,
    compiler: SafetyCompiler,
    allowed_memory_scope_ids: tuple[str, ...],
    allowed_policy_ids: tuple[str, ...],
) -> dict[str, Any]:
    payload = _required_mapping(case, "input")
    candidate = _base_candidate(_required_string(case, "case_id"))
    candidate.update(_mapping(payload.get("candidate")))
    content = _mapping(payload.get("content"))

    store = InMemoryRuntimeStore()
    inserted = store.insert_memory_candidate(candidate)
    result = MemoryCandidateValidator(
        store=store,
        allowed_memory_scope_ids=allowed_memory_scope_ids,
        allowed_policy_ids=allowed_policy_ids,
        safety_compiler=compiler,
    ).validate(inserted, content=content)
    final_gate = "allow_ranking_only" if result.approved else "reject"
    return {
        "actual_outcome": ALLOWING_OUTCOME if result.approved else BLOCKING_OUTCOME,
        "final_gate": final_gate,
        "reason": (
            result.policy_reason
            if result.policy_status == "rejected"
            else result.validation_reason
        ),
        "validator_status": result.validator_status,
        "policy_status": result.policy_status,
    }


def _evaluate_semantic_drift_case(
    case: Mapping[str, Any],
    *,
    compiler: SafetyCompiler,
) -> dict[str, Any]:
    payload = _required_mapping(case, "input")
    prior = _required_mapping(payload, "learned_context_authority_prior")
    report = compiler.compile_decision_report(
        prior,
        reviewed_policy_artifacts=_string_tuple(payload.get("reviewed_policy_artifacts")),
    )
    allowed = bool(report["automatic_promotion_allowed"])
    return {
        "actual_outcome": ALLOWING_OUTCOME if allowed else BLOCKING_OUTCOME,
        "final_gate": str(report["final_gate"]),
        "reason": str(report["decision"]["reason"]),
        "matched_contrastive_pair_ids": report["matched_contrastive_pair_ids"],
    }


def _evaluate_post_planning_case(case: Mapping[str, Any]) -> dict[str, Any]:
    payload = _required_mapping(case, "input")
    runtime_profile = dict(_mapping(payload.get("runtime_profile")) or _default_runtime_profile())
    planned_runtime_profile: dict[str, Any] | None = None
    if isinstance(payload.get("planned_runtime_profile_delta"), Mapping):
        planned_runtime_profile = deepcopy(runtime_profile)
        planned_runtime_profile.update(payload["planned_runtime_profile_delta"])

    result = PostPlanningMemoryInvariantValidator().validate(
        _required_mapping(payload, "plan"),
        runtime_profile=runtime_profile,
        planned_runtime_profile=planned_runtime_profile,
    )
    return {
        "actual_outcome": ALLOWING_OUTCOME if result.approved else BLOCKING_OUTCOME,
        "final_gate": "allow_ranking_only" if result.approved else "reject",
        "reason": result.reason,
        "violations": list(result.violations),
    }


def _metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    expected_block = [
        result for result in results if result["expected_outcome"] == BLOCKING_OUTCOME
    ]
    expected_allow = [
        result for result in results if result["expected_outcome"] == ALLOWING_OUTCOME
    ]
    false_negatives = [
        result for result in expected_block if result["actual_outcome"] == ALLOWING_OUTCOME
    ]
    false_positives = [
        result for result in expected_allow if result["actual_outcome"] == BLOCKING_OUTCOME
    ]
    review_cases = [result for result in results if result.get("final_gate") in REVIEW_GATES]
    return {
        "expected_block_count": len(expected_block),
        "expected_allow_count": len(expected_allow),
        "blocked_count": sum(
            1 for result in results if result["actual_outcome"] == BLOCKING_OUTCOME
        ),
        "allowed_count": sum(
            1 for result in results if result["actual_outcome"] == ALLOWING_OUTCOME
        ),
        "false_negative_rate": _rate(len(false_negatives), len(expected_block)),
        "false_positive_rate": _rate(len(false_positives), len(expected_allow)),
        "abstention_review_rate": _rate(len(review_cases), len(results)),
    }


def _coverage(
    results: list[dict[str, Any]],
    required_failure_classes: frozenset[str],
) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for result in results:
        failure_class = str(result["failure_class"])
        counts[failure_class] = counts.get(failure_class, 0) + 1
    covered = frozenset(counts)
    return {
        "failure_class_counts": dict(sorted(counts.items())),
        "required_failure_classes": sorted(required_failure_classes),
        "missing_required_failure_classes": sorted(required_failure_classes - covered),
    }


def _base_candidate(case_id: str) -> dict[str, Any]:
    return {
        "id": f"mc-{case_id}",
        "run_id": "run-memory-safety-fixture",
        "profile_id": "profile-memory-safety-fixture",
        "source_step_id": "step-memory-safety-fixture",
        "target_memory_scope_id": "project-memory",
        "candidate_class": "procedural_lesson",
        "classification_reason": "Fixture candidate is classified for memory safety evaluation.",
        "content_uri": f"hetzner://runtime/run-memory-safety-fixture/{case_id}.json",
        "sensitivity": "internal",
        "retention_policy": "runtime-30d",
        "validator_status": "pending",
        "validator_id": "memory-candidate-contract",
        "validation_reason": None,
        "policy_status": "pending",
        "policy_id": "memory-taxonomy-policy",
        "policy_reason": None,
    }


def _default_runtime_profile() -> dict[str, Any]:
    return {
        "tools": ["filesystem-read", "git-read", "test-runner"],
        "knowledge_scopes": ["architecture-docs"],
        "memory_scopes": ["project-memory"],
        "data_scopes": ["repository-readonly"],
        "policies": ["no-destructive-commands"],
        "validators": ["runtime-profile-schema", "review-findings-contract"],
        "limits": {"max_tokens": 60000},
        "failure_policy": {"on_policy_denial": "return_error"},
    }


def _resolve_policy_path(fixture: Mapping[str, Any], base_path: Path | None) -> Path:
    raw_path = _required_string(fixture, "semantic_drift_policy_path")
    path = Path(raw_path)
    if not path.is_absolute():
        if base_path is None:
            raise MemorySafetyEvaluationError(
                "Relative semantic_drift_policy_path requires base_path."
            )
        path = base_path / path
    return path


def _required_mapping(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, Mapping):
        raise MemorySafetyEvaluationError(f"{key} must be an object.")
    return value


def _required_list(mapping: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = mapping.get(key)
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise MemorySafetyEvaluationError(f"{key} must be a list of objects.")
    return list(value)


def _required_string(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MemorySafetyEvaluationError(f"{key} must be a non-empty string.")
    return value


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string_tuple(value: Any, *, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    if not isinstance(value, list):
        return default
    return tuple(item for item in value if isinstance(item, str) and item.strip())


def _string_set(value: Any) -> frozenset[str]:
    return frozenset(_string_tuple(value))


def _float_threshold(mapping: Mapping[str, Any], key: str) -> float:
    value = mapping.get(key)
    if not isinstance(value, int | float):
        raise MemorySafetyEvaluationError(f"{key} must be numeric.")
    return float(value)


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
