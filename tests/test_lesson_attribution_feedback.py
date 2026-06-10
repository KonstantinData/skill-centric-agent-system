from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator

from skill_centric_agent_system.runtime import (
    ErrorClassification,
    PlannerMemoryRecordError,
    build_context_fingerprint,
    build_lesson_attribution_record,
    build_lesson_ranking_feedback_gate,
    build_planner_memory_selection_record,
    validate_lesson_attribution_record,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "lesson-attribution-record.schema.json"
EXAMPLE_PATH = REPO_ROOT / "examples" / "evaluations" / "lesson-attribution-record.json"


def load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def selection_record() -> dict[str, Any]:
    return dict(
        build_planner_memory_selection_record(
            record_id="pmr-runtime-reconstruction",
            plan_id="plan-runtime-reconstruction",
            used_memory_ids=["lesson-focused-tests"],
            ignored_memory_ids=["lesson-full-gate-first"],
            effect="planner_hint",
            selection_reason="Focused lesson matched the narrow runtime helper change.",
            plan_change="Run focused tests before full validation.",
        )
    )


def runtime_context() -> dict[str, Any]:
    return {
        "task_type": "repository-maintenance",
        "risk_level": "medium",
        "changed_surface": "runtime-helper",
    }


def error_classification() -> dict[str, Any]:
    return ErrorClassification(
        error_class="NONE",
        error_confidence="high",
        classification_source="rule_based_runtime_v1",
        error_evidence={"tool_calls": 8, "tokens_used": 12000},
        runtime_playbook="no_action_required",
    ).as_dict()


def success_criteria() -> list[dict[str, Any]]:
    return [
        {
            "criterion": "Focused memory-guided test ran before full gate.",
            "status": "met",
            "evidence_uris": [
                "hetzner://runtime/run-runtime-reconstruction/validation/focused-tests.json"
            ],
        }
    ]


def feedback_items() -> list[dict[str, Any]]:
    return [
        {
            "memory_id": "lesson-focused-tests",
            "effect": "ranking_adjustment",
            "direction": "promote",
            "weight_delta": 0.05,
            "reason": "The selected lesson produced a clean validation path.",
        },
        {
            "memory_id": "lesson-full-gate-first",
            "effect": "planner_hint_adjustment",
            "direction": "neutral",
            "weight_delta": 0,
            "reason": "The broader lesson remains valid for high-impact surfaces.",
        },
    ]


def attribution_record() -> dict[str, Any]:
    return dict(
        build_lesson_attribution_record(
            record_id="lesson-attribution-runtime-reconstruction",
            run_id="run-runtime-reconstruction",
            selection_record=selection_record(),
            context=runtime_context(),
            outcome="succeeded",
            success_criteria=success_criteria(),
            error_classification=error_classification(),
            ranking_feedback=feedback_items(),
        )
    )


def test_lesson_attribution_example_matches_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    example = load_json(EXAMPLE_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(example)
    validate_lesson_attribution_record(example)


def test_lesson_attribution_record_is_context_bound_and_non_authoritative() -> None:
    record = attribution_record()

    assert record["context_fingerprint"] == build_context_fingerprint(runtime_context())
    assert record["feedback_effect"] == "non_authoritative_ranking_only"
    assert record["authority_delta"] == []
    assert record["ranking_feedback"][0]["context_bound"] is True
    assert record["ranking_feedback"][0]["authority_delta"] == []


def test_lesson_ranking_feedback_gate_outputs_only_non_authoritative_items() -> None:
    gate = build_lesson_ranking_feedback_gate(attribution_record())

    assert gate["feedback_effect"] == "non_authoritative_ranking_only"
    assert gate["authority_delta"] == []
    assert gate["items"][0]["effect"] == "ranking_adjustment"
    assert gate["items"][0]["weight_delta"] == pytest.approx(0.05)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda record: record.__setitem__("authority_delta", ["tool_addition"]),
            "authority_delta",
        ),
        (
            lambda record: record["ranking_feedback"][0].__setitem__(
                "context_fingerprint",
                build_context_fingerprint({"task_type": "other"}),
            ),
            "context_fingerprint",
        ),
        (
            lambda record: record["ranking_feedback"][0].__setitem__("context_bound", False),
            "context-bound",
        ),
        (
            lambda record: record["ranking_feedback"][0].__setitem__("weight_delta", 0.5),
            "weight_delta",
        ),
        (
            lambda record: record["ranking_feedback"][0].__setitem__(
                "memory_id",
                "lesson-not-selected",
            ),
            "memory_id",
        ),
    ],
)
def test_lesson_attribution_rejects_unsafe_feedback(mutator: object, message: str) -> None:
    record = attribution_record()
    mutator(record)  # type: ignore[operator]

    with pytest.raises(PlannerMemoryRecordError, match=message):
        validate_lesson_attribution_record(record)


def test_lesson_attribution_docs_reference_schema_and_example() -> None:
    memory_architecture = (REPO_ROOT / "docs" / "reference" / "memory-architecture.md").read_text(
        encoding="utf-8"
    )
    runtime_contract = (REPO_ROOT / "docs" / "policies" / "runtime-contract.md").read_text(
        encoding="utf-8"
    )
    backlog = (REPO_ROOT / "docs" / "roadmap" / "memory-architecture-backlog.md").read_text(
        encoding="utf-8"
    )

    assert "lesson-attribution-record.schema.json" in memory_architecture
    assert "lesson-attribution-record.json" in runtime_contract
    assert "Lesson Attribution And Ranking Feedback Gate" in backlog
