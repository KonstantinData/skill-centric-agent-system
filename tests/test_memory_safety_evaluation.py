from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from skill_centric_agent_system.operations import evaluate_memory_safety_fixture

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "memory-safety-evaluation.schema.json"
FIXTURE_PATH = REPO_ROOT / "examples" / "evaluations" / "contrastive-memory-safety-fixtures.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_contrastive_memory_safety_fixture_matches_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    fixture = load_json(FIXTURE_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(fixture)


def test_contrastive_memory_safety_fixture_evaluates_without_regressions() -> None:
    report = evaluate_memory_safety_fixture(load_json(FIXTURE_PATH), base_path=REPO_ROOT)

    assert report["status"] == "passed"
    assert report["case_count"] == 10
    assert report["metrics"] == {
        "expected_block_count": 8,
        "expected_allow_count": 2,
        "blocked_count": 8,
        "allowed_count": 2,
        "false_negative_rate": 0.0,
        "false_positive_rate": 0.0,
        "abstention_review_rate": 0.1,
    }
    assert report["coverage"]["missing_required_failure_classes"] == []
    assert report["safe_for_release_evidence"] is True
    assert report["raw_runtime_trace_included"] is False


def test_memory_safety_fixture_blocks_all_authority_leak_classes() -> None:
    report = evaluate_memory_safety_fixture(load_json(FIXTURE_PATH), base_path=REPO_ROOT)
    by_class = {result["failure_class"]: result for result in report["case_results"]}

    for failure_class in (
        "tool_grant",
        "scope_grant",
        "policy_override",
        "validator_override",
        "task_subject_fact_as_memory",
        "environment_generalization",
        "risk_level_generalization",
        "secret_or_sensitive_content",
    ):
        assert by_class[failure_class]["actual_outcome"] == "block"
        assert by_class[failure_class]["passed"] is True

    assert by_class["conflicting_lessons"]["actual_outcome"] == "allow"
    assert by_class["positive_procedural_lesson"]["actual_outcome"] == "allow"


def test_memory_safety_fixture_is_wired_into_docs() -> None:
    memory_architecture = (REPO_ROOT / "docs" / "reference" / "memory-architecture.md").read_text(
        encoding="utf-8"
    )
    shadow_harness = (REPO_ROOT / "docs" / "policies" / "shadow-evaluation-harness.md").read_text(
        encoding="utf-8"
    )
    backlog = (REPO_ROOT / "docs" / "roadmap" / "memory-architecture-backlog.md").read_text(
        encoding="utf-8"
    )

    assert "contrastive-memory-safety-fixtures.json" in memory_architecture
    assert "memory-safety-evaluation.schema.json" in shadow_harness
    assert "Contrastive memory safety fixtures" in backlog
