from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from skill_centric_agent_system.operations import evaluate_memory_operations_evidence

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "memory-operations-evidence.schema.json"
SNAPSHOT_PATH = REPO_ROOT / "examples" / "operations" / "memory-operations-evidence.json"


def load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_memory_operations_evidence_matches_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    snapshot = load_json(SNAPSHOT_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(snapshot)


def test_memory_operations_evidence_passes_clean_snapshot() -> None:
    result = evaluate_memory_operations_evidence(load_json(SNAPSHOT_PATH))

    assert result["status"] == "passed"
    assert result["failed_gates"] == []
    assert result["raw_data_policy"] == "aggregate_metadata_only"
    assert result["gates"]["live_smoke"]["status"] == "passed"
    assert result["gates"]["taxonomy_metrics"]["status"] == "passed"


def test_memory_operations_evidence_fails_closed_on_taxonomy_regression() -> None:
    snapshot = deepcopy(load_json(SNAPSHOT_PATH))
    snapshot["aggregate_metrics"]["contrastive_false_negative_count"] = 1

    result = evaluate_memory_operations_evidence(snapshot)

    assert result["status"] == "failed"
    assert "taxonomy_metrics" in result["failed_gates"]
    assert "contrastive false negatives must be zero" in (
        result["gates"]["taxonomy_metrics"]["failures"]
    )


def test_memory_operations_evidence_fails_on_retention_coupling() -> None:
    snapshot = deepcopy(load_json(SNAPSHOT_PATH))
    snapshot["retention_separation"]["cloudflare_memory_deleted_by_runtime_cleanup"] = True

    result = evaluate_memory_operations_evidence(snapshot)

    assert result["status"] == "failed"
    assert "retention_separation" in result["failed_gates"]


def test_memory_operations_evidence_is_wired_into_release_docs() -> None:
    release_script = (
        REPO_ROOT / "scripts" / "release" / "build_production_readiness_evidence.py"
    ).read_text(encoding="utf-8")
    runbook = (REPO_ROOT / "docs" / "runbooks" / "operations-runbook.md").read_text(
        encoding="utf-8"
    )
    backlog = (REPO_ROOT / "docs" / "roadmap" / "memory-architecture-backlog.md").read_text(
        encoding="utf-8"
    )

    assert "Memory taxonomy operations evidence" in release_script
    assert "memory-operations-evidence.json" in runbook
    assert "Operations Telemetry And Evidence Gates" in backlog
