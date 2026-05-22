from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from skill_centric_agent_system.runtime import (
    InMemoryRuntimeStore,
    JsonArtifactStore,
    MemoryCandidateError,
    MemoryCandidateExtractor,
    MemoryCandidateValidator,
    MemoryFeedbackPipeline,
    MinimalRuntimeLoop,
    RuntimeEntryPoint,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_EXAMPLE_PATH = REPO_ROOT / "examples" / "tasks" / "code-review-task.json"
COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response.json"
)
RUNTIME_PLANE_SCHEMA_PATH = REPO_ROOT / "schemas" / "hetzner-runtime-plane.schema.json"
LEARNING_FIXTURE_PATH = REPO_ROOT / "examples" / "evaluations" / "learning-memory-roundtrip.json"


class FakeMemoryClient:
    def __init__(self) -> None:
        self.requests: list[Mapping[str, Any]] = []

    def ingest_memory(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
        self.requests.append(request_body)
        return {
            "status": "succeeded",
            "memory_id": request_body["memory"]["id"],  # type: ignore[index]
        }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def completed_runtime(tmp_path: Path) -> tuple[InMemoryRuntimeStore, JsonArtifactStore, str]:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    composition_context = deepcopy(load_json(COMPOSITION_CONTEXT_RESPONSE_PATH))
    start_result = entrypoint.start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=composition_context,
    )
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
    )
    result = loop.run(start_result)
    return store, artifacts, result.run_id


def validator_step(store: InMemoryRuntimeStore, run_id: str) -> Mapping[str, Any]:
    return next(
        step
        for step in store.runtime_steps.values()
        if step["run_id"] == run_id and step["kind"] == "validator"
    )


def test_memory_candidate_can_be_extracted_validated_and_submitted(tmp_path: Path) -> None:
    store, artifacts, run_id = completed_runtime(tmp_path)
    run = store.runtime_runs[run_id]
    step = validator_step(store, run_id)
    content = {
        "summary": "Use Flight Recorder events and checkpoints for runtime reconstruction.",
        "evidence_uris": [store.validation_results[0]["findings_uri"]],
    }
    extractor = MemoryCandidateExtractor(store=store, artifacts=artifacts)

    candidate = extractor.extract_from_step(
        run=run,
        source_step=step,
        target_memory_scope_id="mod-project-memory",
        content=content,
        sensitivity="internal",
        retention_policy="project-memory-180d",
        policy_id="mod-no-destructive-commands",
    )

    assert candidate["validator_status"] == "pending"
    assert candidate["policy_status"] == "pending"
    assert str(candidate["content_uri"]).startswith("hetzner://runtime/")

    validator = MemoryCandidateValidator(
        store=store,
        allowed_memory_scope_ids={"mod-project-memory"},
        allowed_policy_ids={"mod-no-destructive-commands"},
    )
    validation = validator.validate(candidate, content=content)

    assert validation.approved
    assert validation.candidate["validator_status"] == "approved"
    assert validation.candidate["policy_status"] == "approved"

    client = FakeMemoryClient()
    pipeline = MemoryFeedbackPipeline(client)  # type: ignore[arg-type]
    response = pipeline.submit_candidate(validation.candidate, consolidated_content=content)

    assert response == {
        "status": "succeeded",
        "memory_id": candidate["id"],
    }
    assert client.requests[0]["memory"]["content"] == {  # type: ignore[index]
        **content,
        "source_artifact_uri": candidate["content_uri"],
    }

    Draft202012Validator(load_json(RUNTIME_PLANE_SCHEMA_PATH)).validate(
        store.as_runtime_plane_recordset()
    )


def test_memory_candidate_extraction_requires_completed_step(tmp_path: Path) -> None:
    store, artifacts, run_id = completed_runtime(tmp_path)
    run = store.runtime_runs[run_id]
    source_step = dict(validator_step(store, run_id))
    source_step["status"] = "running"
    extractor = MemoryCandidateExtractor(store=store, artifacts=artifacts)

    with pytest.raises(MemoryCandidateError, match="completed steps"):
        extractor.extract_from_step(
            run=run,
            source_step=source_step,
            target_memory_scope_id="mod-project-memory",
            content={"summary": "Do not persist from incomplete work."},
            sensitivity="internal",
            retention_policy="project-memory-180d",
            policy_id="mod-no-destructive-commands",
        )


def test_memory_candidate_validator_records_rejection_reasons(tmp_path: Path) -> None:
    store, artifacts, run_id = completed_runtime(tmp_path)
    extractor = MemoryCandidateExtractor(store=store, artifacts=artifacts)
    candidate = extractor.extract_from_step(
        run=store.runtime_runs[run_id],
        source_step=validator_step(store, run_id),
        target_memory_scope_id="mod-project-memory",
        content={"summary": "Policy must block this memory update."},
        sensitivity="secret",
        retention_policy="project-memory-180d",
        policy_id="mod-no-destructive-commands",
    )
    validator = MemoryCandidateValidator(
        store=store,
        allowed_memory_scope_ids={"mod-other-memory"},
        allowed_policy_ids={"mod-no-destructive-commands"},
    )

    validation = validator.validate(
        candidate,
        content={"summary": "Policy must block this memory update."},
    )

    assert not validation.approved
    assert validation.candidate["validator_status"] == "rejected"
    assert validation.candidate["policy_status"] == "rejected"
    assert "secret candidates" in str(validation.candidate["validation_reason"])
    assert "target memory scope" in str(validation.candidate["policy_reason"])


def test_learning_evaluation_fixture_documents_positive_and_negative_roundtrip() -> None:
    fixture = load_json(LEARNING_FIXTURE_PATH)

    assert fixture["producer"]["expected_candidate"]["validator_status"] == "approved"
    assert fixture["producer"]["expected_candidate"]["policy_status"] == "approved"
    assert (
        fixture["consumer"]["authorized_retrieval_request"]["principal"]["id"]
        == "repository-maintainer"
    )
    assert fixture["consumer"]["unauthorized_retrieval_request"]["principal"]["id"] == "guest"
    assert "returns no memory records" in fixture["expected_negative_behavior"]
