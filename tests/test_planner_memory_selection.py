from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from skill_centric_agent_system.runtime.planner_memory import (
    PlannerMemoryRecordError,
    build_lesson_conflict_sets,
    build_planner_memory_selection_record,
    validate_planner_memory_selection_record,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "planner-memory-selection-record.schema.json"


def test_planner_memory_selection_record_is_structured_and_non_authoritative() -> None:
    record = build_planner_memory_selection_record(
        record_id="pmr-plan-runtime-audit",
        plan_id="plan-runtime-audit",
        used_memory_ids=["memory-checkpoint-a"],
        ignored_memory_ids=["memory-checkpoint-b"],
        effect="planner_hint",
        selection_reason="memory-checkpoint-a matched runtime reconstruction applicability.",
        plan_change="Inspect checkpoint evidence before comparing validator output.",
        conflict_sets=[
            {
                "conflict_id": "conflict-checkpoint-order",
                "memory_ids": ["memory-checkpoint-a", "memory-checkpoint-b"],
                "relation": "contradicts",
                "resolution": "used memory-checkpoint-a because applicability matched.",
            }
        ],
    )

    assert record["used_memory_ids"] == ["memory-checkpoint-a"]
    assert record["ignored_memory_ids"] == ["memory-checkpoint-b"]
    assert record["authority_delta"] == []
    assert record["authority_impact"] == {
        "status": "none",
        "validator_visible": True,
        "checked_by": "PostPlanningMemoryInvariantValidator",
    }
    Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))).validate(record)


def test_lesson_conflict_sets_group_conflicting_memory_records() -> None:
    conflict_sets = build_lesson_conflict_sets(
        [
            {
                "id": "memory-checkpoint-a",
                "conflict_key": "checkpoint-order",
                "conflict_relation": "contradicts",
            },
            {
                "id": "memory-checkpoint-b",
                "conflict_key": "checkpoint-order",
                "conflict_relation": "contradicts",
            },
            {"id": "memory-other"},
        ]
    )

    assert len(conflict_sets) == 1
    assert conflict_sets[0].conflict_id == "conflict-checkpoint-order"
    assert conflict_sets[0].memory_ids == ("memory-checkpoint-a", "memory-checkpoint-b")
    assert conflict_sets[0].resolution == "planner_selection_required"


def test_planner_memory_selection_rejects_authority_delta() -> None:
    record = build_planner_memory_selection_record(
        record_id="pmr-plan-runtime-audit",
        plan_id="plan-runtime-audit",
        used_memory_ids=["memory-checkpoint-a"],
        ignored_memory_ids=[],
        effect="planner_hint",
        selection_reason="Structured relevance summary.",
        plan_change="Inspect checkpoint evidence.",
    )
    record["authority_delta"] = ["tool_grant"]

    with pytest.raises(PlannerMemoryRecordError, match="authority_delta"):
        validate_planner_memory_selection_record(record)


def test_planner_memory_selection_rejects_chain_of_thought_reason() -> None:
    with pytest.raises(PlannerMemoryRecordError, match="chain-of-thought"):
        build_planner_memory_selection_record(
            record_id="pmr-plan-runtime-audit",
            plan_id="plan-runtime-audit",
            used_memory_ids=["memory-checkpoint-a"],
            ignored_memory_ids=[],
            effect="planner_hint",
            selection_reason="First I thought through my hidden reasoning step by step.",
            plan_change="Inspect checkpoint evidence.",
        )
