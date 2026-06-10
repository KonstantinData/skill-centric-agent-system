from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from skill_centric_agent_system.runtime.context import MEMORY_ALLOWED_EFFECTS


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
