from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator

from skill_centric_agent_system.runtime import (
    PlannerMemoryRecordError,
    build_lesson_relationship_edge,
    build_lesson_relationship_graph,
    validate_lesson_relationship_edge,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "lesson-relationship-graph.schema.json"
EXAMPLE_PATH = REPO_ROOT / "examples" / "evaluations" / "lesson-relationship-graph.json"


def load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def relationship_edges() -> list[dict[str, Any]]:
    return [
        dict(
            build_lesson_relationship_edge(
                edge_id="edge-focused-tests-refines-full-gate",
                source_memory_id="lesson-focused-tests",
                target_memory_id="lesson-full-gate-first",
                relation="refines",
                direction="directed",
                confidence="high",
                reason="Focused tests refine full-gate guidance for narrow changes.",
                evidence_uris=[
                    "hetzner://runtime/run-runtime-reconstruction/relationships/refines.json"
                ],
                ranking_effect="promote_related",
                visibility_effects=["ranking"],
            )
        ),
        dict(
            build_lesson_relationship_edge(
                edge_id="edge-fast-path-contradicts-full-gate",
                source_memory_id="lesson-fast-path",
                target_memory_id="lesson-full-gate-first",
                relation="contradicts",
                direction="symmetric",
                confidence="medium",
                reason="The lessons disagree on whether broad gates can be skipped.",
                evidence_uris=[
                    "hetzner://runtime/run-runtime-reconstruction/relationships/conflict.json"
                ],
                ranking_effect="surface_conflict",
                visibility_effects=["conflict_display"],
            )
        ),
    ]


def test_lesson_relationship_graph_example_matches_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    example = load_json(EXAMPLE_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(example)
    for edge in example["lesson_edges"]:
        validate_lesson_relationship_edge(edge)


def test_lesson_relationship_graph_outputs_non_authoritative_ranking_hints() -> None:
    graph = build_lesson_relationship_graph(relationship_edges())

    assert graph["feedback_effect"] == "non_authoritative_relationship_metadata"
    assert graph["authority_delta"] == []
    assert graph["relation_counts"] == {"contradicts": 1, "refines": 1}
    assert graph["ranking_hints"][0]["non_authoritative"] is True
    assert graph["ranking_hints"][0]["authority_delta"] == []


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda edge: edge.__setitem__("authority_delta", ["scope_expansion"]),
            "authority_delta",
        ),
        (
            lambda edge: edge.__setitem__("target_memory_id", edge["source_memory_id"]),
            "endpoints",
        ),
        (
            lambda edge: edge.__setitem__("ranking_effect", "grant_scope"),
            "ranking_effect",
        ),
        (
            lambda edge: edge.__setitem__("visibility_effects", ["scope_expansion"]),
            "visibility_effect",
        ),
        (
            lambda edge: edge.__setitem__("non_authoritative", False),
            "non-authoritative",
        ),
    ],
)
def test_lesson_relationship_edges_reject_authority_semantics(
    mutator: object,
    message: str,
) -> None:
    edge = relationship_edges()[0]
    mutator(edge)  # type: ignore[operator]

    with pytest.raises(PlannerMemoryRecordError, match=message):
        validate_lesson_relationship_edge(edge)


def test_lesson_relationship_docs_reference_schema_and_example() -> None:
    memory_architecture = (REPO_ROOT / "docs" / "reference" / "memory-architecture.md").read_text(
        encoding="utf-8"
    )
    runtime_contract = (REPO_ROOT / "docs" / "policies" / "runtime-contract.md").read_text(
        encoding="utf-8"
    )
    backlog = (REPO_ROOT / "docs" / "roadmap" / "memory-architecture-backlog.md").read_text(
        encoding="utf-8"
    )

    assert "lesson-relationship-graph.schema.json" in memory_architecture
    assert "lesson-relationship-graph.json" in runtime_contract
    assert "Non-Authoritative Lesson Relationship Graph" in backlog
