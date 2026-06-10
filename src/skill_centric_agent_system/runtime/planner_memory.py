from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from skill_centric_agent_system.runtime.context import MEMORY_ALLOWED_EFFECTS

LESSON_OUTCOMES = frozenset({"succeeded", "failed", "neutral"})
SUCCESS_CRITERION_STATUSES = frozenset({"met", "missed", "not_applicable"})
LESSON_FEEDBACK_EFFECTS = frozenset({"ranking_adjustment", "planner_hint_adjustment"})
LESSON_FEEDBACK_DIRECTIONS = frozenset({"promote", "demote", "neutral"})
LESSON_FEEDBACK_OUTPUT_EFFECT = "non_authoritative_ranking_only"
MAX_LESSON_FEEDBACK_WEIGHT_DELTA = 0.2


class PlannerMemoryRecordError(ValueError):
    """Raised when a planner memory selection record is unsafe."""


@dataclass(frozen=True)
class LessonConflictSet:
    conflict_id: str
    memory_ids: tuple[str, ...]
    relation: str
    resolution: str


def build_lesson_conflict_sets(
    memory_records: Iterable[Mapping[str, Any]],
) -> tuple[LessonConflictSet, ...]:
    """Group retrieved memory records that declare the same conflict key."""

    grouped: dict[str, list[str]] = {}
    relation_by_key: dict[str, str] = {}
    for record in memory_records:
        conflict_key = str(record.get("conflict_key", "")).strip()
        if not conflict_key:
            continue
        memory_id = str(record.get("id", "")).strip()
        if not memory_id:
            continue
        grouped.setdefault(conflict_key, []).append(memory_id)
        relation_by_key[conflict_key] = str(record.get("conflict_relation", "conflicts"))

    conflict_sets: list[LessonConflictSet] = []
    for conflict_key, memory_ids in grouped.items():
        unique_memory_ids = tuple(dict.fromkeys(memory_ids))
        if len(unique_memory_ids) < 2:
            continue
        conflict_sets.append(
            LessonConflictSet(
                conflict_id=f"conflict-{conflict_key}",
                memory_ids=unique_memory_ids,
                relation=relation_by_key[conflict_key],
                resolution="planner_selection_required",
            )
        )
    return tuple(conflict_sets)


def build_planner_memory_selection_record(
    *,
    record_id: str,
    plan_id: str,
    used_memory_ids: Iterable[str],
    ignored_memory_ids: Iterable[str],
    effect: str,
    selection_reason: str,
    plan_change: str,
    conflict_sets: Iterable[LessonConflictSet | Mapping[str, Any]] = (),
) -> Mapping[str, Any]:
    record = {
        "contract_version": "0.1.0",
        "record_id": record_id,
        "plan_id": plan_id,
        "used_memory_ids": _string_tuple(used_memory_ids),
        "ignored_memory_ids": _string_tuple(ignored_memory_ids),
        "effect": effect,
        "selection_reason": selection_reason,
        "authority_delta": [],
        "plan_change": plan_change,
        "authority_impact": {
            "status": "none",
            "validator_visible": True,
            "checked_by": "PostPlanningMemoryInvariantValidator",
        },
        "conflict_sets": [
            _conflict_set_to_mapping(conflict_set) for conflict_set in conflict_sets
        ],
    }
    return validate_planner_memory_selection_record(record)


def validate_planner_memory_selection_record(record: Mapping[str, Any]) -> Mapping[str, Any]:
    required = {
        "contract_version",
        "record_id",
        "plan_id",
        "used_memory_ids",
        "ignored_memory_ids",
        "effect",
        "selection_reason",
        "authority_delta",
        "plan_change",
        "authority_impact",
        "conflict_sets",
    }
    missing = sorted(field for field in required if field not in record)
    if missing:
        raise PlannerMemoryRecordError("missing fields: " + ", ".join(missing))
    if record["contract_version"] != "0.1.0":
        raise PlannerMemoryRecordError("contract_version must be 0.1.0")
    used_memory_ids = _string_tuple(record.get("used_memory_ids"))
    if not used_memory_ids:
        raise PlannerMemoryRecordError("used_memory_ids are required")
    ignored_memory_ids = _string_tuple(record.get("ignored_memory_ids"))
    if set(used_memory_ids).intersection(ignored_memory_ids):
        raise PlannerMemoryRecordError("used and ignored memory IDs must be disjoint")
    if record["effect"] not in MEMORY_ALLOWED_EFFECTS:
        raise PlannerMemoryRecordError("effect must be non-authoritative")
    if not str(record.get("selection_reason", "")).strip():
        raise PlannerMemoryRecordError("selection_reason is required")
    if _string_tuple(record.get("authority_delta")):
        raise PlannerMemoryRecordError("authority_delta must be empty")
    authority_impact = record.get("authority_impact")
    if not isinstance(authority_impact, Mapping):
        raise PlannerMemoryRecordError("authority_impact is required")
    if authority_impact.get("status") != "none":
        raise PlannerMemoryRecordError("authority_impact.status must be none")
    if authority_impact.get("validator_visible") is not True:
        raise PlannerMemoryRecordError("authority_impact must be validator-visible")
    if _contains_chain_of_thought(str(record.get("selection_reason", ""))):
        raise PlannerMemoryRecordError("selection_reason must be structured, not chain-of-thought")
    return {
        **dict(record),
        "used_memory_ids": list(used_memory_ids),
        "ignored_memory_ids": list(ignored_memory_ids),
    }


def build_context_fingerprint(context: Mapping[str, Any]) -> str:
    """Build a deterministic, non-secret context fingerprint for lesson attribution."""

    canonical_context = json.dumps(
        dict(context),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return "sha256:" + hashlib.sha256(canonical_context.encode("utf-8")).hexdigest()


def build_lesson_attribution_record(
    *,
    record_id: str,
    run_id: str,
    selection_record: Mapping[str, Any],
    context: Mapping[str, Any],
    outcome: str,
    success_criteria: Iterable[Mapping[str, Any]],
    error_classification: Mapping[str, Any],
    ranking_feedback: Iterable[Mapping[str, Any]] = (),
) -> Mapping[str, Any]:
    selection = validate_planner_memory_selection_record(selection_record)
    context_fingerprint = build_context_fingerprint(context)
    record = {
        "contract_version": "0.1.0",
        "record_id": record_id,
        "run_id": run_id,
        "selection_record_id": selection["record_id"],
        "plan_id": selection["plan_id"],
        "used_memory_ids": list(selection["used_memory_ids"]),
        "ignored_memory_ids": list(selection["ignored_memory_ids"]),
        "context_fingerprint": context_fingerprint,
        "outcome": outcome,
        "success_criteria": [dict(item) for item in success_criteria],
        "error_classification": dict(error_classification),
        "ranking_feedback": [
            {
                "context_fingerprint": context_fingerprint,
                "context_bound": True,
                "authority_delta": [],
                **dict(item),
            }
            for item in ranking_feedback
        ],
        "feedback_effect": LESSON_FEEDBACK_OUTPUT_EFFECT,
        "authority_delta": [],
    }
    return validate_lesson_attribution_record(record)


def validate_lesson_attribution_record(record: Mapping[str, Any]) -> Mapping[str, Any]:
    required = {
        "contract_version",
        "record_id",
        "run_id",
        "selection_record_id",
        "plan_id",
        "used_memory_ids",
        "ignored_memory_ids",
        "context_fingerprint",
        "outcome",
        "success_criteria",
        "error_classification",
        "ranking_feedback",
        "feedback_effect",
        "authority_delta",
    }
    missing = sorted(field for field in required if field not in record)
    if missing:
        raise PlannerMemoryRecordError("missing fields: " + ", ".join(missing))
    if record["contract_version"] != "0.1.0":
        raise PlannerMemoryRecordError("contract_version must be 0.1.0")
    used_memory_ids = _string_tuple(record.get("used_memory_ids"))
    if not used_memory_ids:
        raise PlannerMemoryRecordError("used_memory_ids are required")
    ignored_memory_ids = _string_tuple(record.get("ignored_memory_ids"))
    if set(used_memory_ids).intersection(ignored_memory_ids):
        raise PlannerMemoryRecordError("used and ignored memory IDs must be disjoint")
    context_fingerprint = str(record.get("context_fingerprint", ""))
    if not context_fingerprint.startswith("sha256:"):
        raise PlannerMemoryRecordError("context_fingerprint must be a sha256 fingerprint")
    if record["outcome"] not in LESSON_OUTCOMES:
        raise PlannerMemoryRecordError("outcome is invalid")
    if record["feedback_effect"] != LESSON_FEEDBACK_OUTPUT_EFFECT:
        raise PlannerMemoryRecordError("feedback_effect must be non-authoritative")
    if _string_tuple(record.get("authority_delta")):
        raise PlannerMemoryRecordError("authority_delta must be empty")
    _validate_success_criteria(record.get("success_criteria"))
    _validate_error_classification(record.get("error_classification"))
    feedback = _validate_lesson_ranking_feedback(
        record.get("ranking_feedback"),
        context_fingerprint=context_fingerprint,
        known_memory_ids=set(used_memory_ids) | set(ignored_memory_ids),
    )
    return {
        **dict(record),
        "used_memory_ids": list(used_memory_ids),
        "ignored_memory_ids": list(ignored_memory_ids),
        "ranking_feedback": feedback,
    }


def build_lesson_ranking_feedback_gate(record: Mapping[str, Any]) -> Mapping[str, Any]:
    attribution = validate_lesson_attribution_record(record)
    return {
        "contract_version": "0.1.0",
        "record_id": f"feedback-{attribution['record_id']}",
        "source_attribution_record_id": attribution["record_id"],
        "selection_record_id": attribution["selection_record_id"],
        "context_fingerprint": attribution["context_fingerprint"],
        "feedback_effect": LESSON_FEEDBACK_OUTPUT_EFFECT,
        "authority_delta": [],
        "items": list(attribution["ranking_feedback"]),
    }


def _conflict_set_to_mapping(conflict_set: LessonConflictSet | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(conflict_set, LessonConflictSet):
        return {
            "conflict_id": conflict_set.conflict_id,
            "memory_ids": list(conflict_set.memory_ids),
            "relation": conflict_set.relation,
            "resolution": conflict_set.resolution,
        }
    return dict(conflict_set)


def _string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, tuple | list):
        return tuple(item for item in value if isinstance(item, str) and item.strip())
    if not isinstance(value, str):
        return ()
    return (value,) if value.strip() else ()


def _validate_success_criteria(value: Any) -> None:
    if not isinstance(value, list) or not value:
        raise PlannerMemoryRecordError("success_criteria are required")
    for item in value:
        if not isinstance(item, Mapping):
            raise PlannerMemoryRecordError("success_criteria entries must be objects")
        if not str(item.get("criterion", "")).strip():
            raise PlannerMemoryRecordError("success criteria require criterion")
        if item.get("status") not in SUCCESS_CRITERION_STATUSES:
            raise PlannerMemoryRecordError("success criteria status is invalid")
        evidence_uris = _string_tuple(item.get("evidence_uris"))
        if not evidence_uris:
            raise PlannerMemoryRecordError("success criteria require evidence_uris")
        if any(not uri.startswith("hetzner://runtime/") for uri in evidence_uris):
            raise PlannerMemoryRecordError("success criteria evidence must stay on Hetzner")


def _validate_error_classification(value: Any) -> None:
    if not isinstance(value, Mapping):
        raise PlannerMemoryRecordError("error_classification is required")
    if value.get("error_class") not in {
        "F1_INEFFICIENCY_PATH",
        "F2_INTERFACE_CONTRACT_BREAKDOWN",
        "R8_POLICY_CONFLICT_CONTEXT_CONTAMINATION",
        "NONE",
    }:
        raise PlannerMemoryRecordError("error_classification.error_class is invalid")
    if value.get("classification_source") not in {"rule_based_runtime_v1", "llm_judge_v1"}:
        raise PlannerMemoryRecordError("error_classification.classification_source is invalid")


def _validate_lesson_ranking_feedback(
    value: Any,
    *,
    context_fingerprint: str,
    known_memory_ids: set[str],
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise PlannerMemoryRecordError("ranking_feedback must be a list")
    feedback: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise PlannerMemoryRecordError("ranking_feedback entries must be objects")
        memory_id = str(item.get("memory_id", "")).strip()
        if memory_id not in known_memory_ids:
            raise PlannerMemoryRecordError("ranking_feedback memory_id must be selected or ignored")
        effect = item.get("effect")
        if effect not in LESSON_FEEDBACK_EFFECTS:
            raise PlannerMemoryRecordError("ranking_feedback effect is invalid")
        direction = item.get("direction")
        if direction not in LESSON_FEEDBACK_DIRECTIONS:
            raise PlannerMemoryRecordError("ranking_feedback direction is invalid")
        weight_delta = item.get("weight_delta")
        if not isinstance(weight_delta, int | float):
            raise PlannerMemoryRecordError("ranking_feedback weight_delta must be numeric")
        if abs(float(weight_delta)) > MAX_LESSON_FEEDBACK_WEIGHT_DELTA:
            raise PlannerMemoryRecordError("ranking_feedback weight_delta exceeds safe maximum")
        if direction == "promote" and float(weight_delta) <= 0:
            raise PlannerMemoryRecordError("promote feedback requires positive weight_delta")
        if direction == "demote" and float(weight_delta) >= 0:
            raise PlannerMemoryRecordError("demote feedback requires negative weight_delta")
        if direction == "neutral" and float(weight_delta) != 0:
            raise PlannerMemoryRecordError("neutral feedback requires zero weight_delta")
        if item.get("context_bound") is not True:
            raise PlannerMemoryRecordError("ranking_feedback must be context-bound")
        if item.get("context_fingerprint") != context_fingerprint:
            raise PlannerMemoryRecordError("ranking_feedback context_fingerprint mismatch")
        if _string_tuple(item.get("authority_delta")):
            raise PlannerMemoryRecordError("ranking_feedback authority_delta must be empty")
        if not str(item.get("reason", "")).strip():
            raise PlannerMemoryRecordError("ranking_feedback reason is required")
        feedback.append(dict(item))
    return feedback


def _contains_chain_of_thought(value: str) -> bool:
    text = value.lower()
    return any(
        marker in text
        for marker in (
            "my hidden reasoning",
            "chain of thought",
            "step-by-step reasoning",
            "first i thought",
        )
    )
