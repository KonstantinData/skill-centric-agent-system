from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from skill_centric_agent_system.runtime import (
    InMemoryRuntimeStore,
    JsonArtifactStore,
    MinimalRuntimeLoop,
    RuntimeEntryPoint,
    RuntimeLoopError,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_EXAMPLE_PATH = REPO_ROOT / "examples" / "tasks" / "code-review-task.json"
PROFILE_EXAMPLE_PATH = REPO_ROOT / "examples" / "profiles" / "code-review-profile.json"
COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response.json"
)
RESEARCH_TASK_EXAMPLE_PATH = REPO_ROOT / "examples" / "tasks" / "research-task.json"
TASK_EXECUTION_TASK_EXAMPLE_PATH = (
    REPO_ROOT / "examples" / "tasks" / "task-execution-task.json"
)
GENERAL_TASK_EXAMPLE_PATH = REPO_ROOT / "examples" / "tasks" / "general-task.json"
RESEARCH_COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response-research.json"
)
TASK_EXECUTION_COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response-task-execution.json"
)
GENERAL_COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response-general-task.json"
)
RUNTIME_PLANE_SCHEMA_PATH = REPO_ROOT / "schemas" / "hetzner-runtime-plane.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_artifact(root: Path, uri: str) -> dict[str, Any]:
    artifact_path = root / Path(uri.removeprefix("hetzner://runtime/"))
    return load_json(artifact_path)

def test_minimal_runtime_loop_fails_closed_for_unknown_profile_validator(
    tmp_path: Path,
) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )
    start_result.profile["validators"].append("unknown-validator")
    start_result.profile["module_versions"]["unknown-validator"] = "0.1.0"
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
    )

    with pytest.raises(RuntimeLoopError):
        loop.run(start_result)

    assert store.runtime_runs[start_result.run_id]["status"] == "failed"
    assert store.runtime_runs[start_result.run_id]["stop_reason"] == "validator_failed"
    failed_event = store.runtime_events[-1]
    failed_result = load_artifact(tmp_path, str(failed_event["result_uri"]))
    assert (
        failed_result["error_classification"]["error_class"]
        == "F2_INTERFACE_CONTRACT_BREAKDOWN"
    )
    assert store.validation_results[-1]["validator_id"] == "unknown-validator"
    assert store.validation_results[-1]["status"] == "failed"


def test_minimal_runtime_loop_requests_recomposition_for_missing_capability(
    tmp_path: Path,
) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )
    start_result.profile["tools"].remove("git-read")
    start_result.profile["failure_policy"]["on_policy_denial"] = "recompose_once"
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
    )

    with pytest.raises(RuntimeLoopError) as exc_info:
        loop.run(start_result)

    assert store.runtime_runs[start_result.run_id]["status"] == "failed"
    assert store.runtime_runs[start_result.run_id]["stop_reason"] == "needs_recomposition"
    assert exc_info.value.stop_reason == "needs_recomposition"
    assert exc_info.value.recomposition_request is not None
    assert exc_info.value.recomposition_request.source_run_id == start_result.run_id
    recomposition_event = store.runtime_events[-1]
    assert recomposition_event["event_type"] == "recomposition_requested"
    result_payload = load_artifact(tmp_path, str(recomposition_event["result_uri"]))
    assert result_payload["source_run_id"] == start_result.run_id
    assert result_payload["parent_profile_id"] == start_result.profile["id"]
    assert result_payload["requested_profile_generation"] == 2
    assert result_payload["recomposition_reason"] == "missing_capability"


def test_minimal_runtime_loop_continues_with_newly_composed_profile(
    tmp_path: Path,
) -> None:
    task = load_json(TASK_EXAMPLE_PATH)
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        task,
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )
    start_result.profile["tools"].remove("git-read")
    start_result.profile["failure_policy"]["on_policy_denial"] = "recompose_once"
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
    )

    result = loop.run_with_recomposition(
        start_result,
        task=task,
        entrypoint=entrypoint,
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )

    assert result.status == "succeeded"
    assert result.run_id == "run-code-review-latest-commit-generation-2"
    assert result.attempt_run_ids == (
        "run-code-review-latest-commit",
        "run-code-review-latest-commit-generation-2",
    )
    assert result.recomposed_profile_ids == ("profile-code-review-latest-commit-g2",)
    assert store.runtime_runs["run-code-review-latest-commit"]["status"] == "failed"
    assert store.runtime_runs["run-code-review-latest-commit"]["stop_reason"] == (
        "needs_recomposition"
    )
    assert store.runtime_runs[result.run_id]["status"] == "succeeded"
    assert "git-read" not in start_result.profile["tools"]
    profile_emitted_event = next(
        event
        for event in store.events_for_run(result.run_id)
        if event["event_type"] == "profile_emitted"
    )
    recomposed_profile_payload = load_artifact(tmp_path, str(profile_emitted_event["result_uri"]))
    recomposed_profile = recomposed_profile_payload["profile"]
    assert recomposed_profile["id"] == "profile-code-review-latest-commit-g2"
    assert recomposed_profile["profile_generation"] == 2
    assert recomposed_profile["parent_profile_id"] == start_result.profile["id"]
    assert recomposed_profile["recomposition_reason"] == "missing_capability"
    assert "git-read" in recomposed_profile["tools"]
    assert (
        recomposed_profile["observability"]["trace_id"]
        == start_result.profile["observability"]["trace_id"]
    )
    candidates_event = next(
        event
        for event in store.events_for_run(result.run_id)
        if event["event_type"] == "candidates_discovered"
    )
    context_request = load_artifact(tmp_path, str(candidates_event["planned_action_uri"]))
    assert context_request["requested_profile_generation"] == {
        "mode": "recomposition",
        "parent_profile_id": start_result.profile["id"],
    }
    assert result.response["attempt_run_ids"] == list(result.attempt_run_ids)


def test_minimal_runtime_loop_respects_recomposition_budget(
    tmp_path: Path,
) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )
    start_result.profile["profile_generation"] = 2
    start_result.profile["tools"].remove("git-read")
    start_result.profile["failure_policy"]["on_policy_denial"] = "recompose_once"
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
    )

    with pytest.raises(RuntimeLoopError):
        loop.run(start_result)

    assert store.runtime_runs[start_result.run_id]["status"] == "failed"
    assert store.runtime_runs[start_result.run_id]["stop_reason"] == "max_recompositions"
    assert store.runtime_events[-1]["event_type"] == "runtime_failed"
    assert store.runtime_events[-1]["stop_reason"] == "max_recompositions"


def test_minimal_runtime_loop_fails_closed_when_profile_limit_is_exceeded(
    tmp_path: Path,
) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )
    start_result.profile["limits"]["max_tool_calls"] = 1
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
    )

    with pytest.raises(RuntimeLoopError):
        loop.run(start_result)

    assert store.runtime_runs[start_result.run_id]["status"] == "failed"
    assert store.runtime_runs[start_result.run_id]["stop_reason"] == "max_tool_calls"
    assert store.runtime_events[-1]["event_type"] == "runtime_failed"
    assert store.runtime_events[-1]["stop_reason"] == "max_tool_calls"


def test_minimal_runtime_loop_classifies_policy_denial_as_r8(
    tmp_path: Path,
) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )
    start_result.profile["tools"].remove("git-read")
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
    )

    with pytest.raises(RuntimeLoopError):
        loop.run(start_result)

    failed_event = store.runtime_events[-1]
    assert failed_event["event_type"] == "runtime_failed"
    failed_result = load_artifact(tmp_path, str(failed_event["result_uri"]))
    assert (
        failed_result["error_classification"]["error_class"]
        == "R8_POLICY_CONFLICT_CONTEXT_CONTAMINATION"
    )


def test_minimal_runtime_loop_uses_llm_judge_when_enabled_for_low_confidence_failure(
    tmp_path: Path,
) -> None:
    class StaticJudge:
        def classify(self, payload: Mapping[str, Any]) -> dict[str, Any]:
            assert payload["base_classification"]["error_confidence"] == "low"
            return {
                "error_class": "F2_INTERFACE_CONTRACT_BREAKDOWN",
                "error_confidence": "medium",
                "runtime_playbook": "normalize_interface_retry_once_then_fail_closed",
                "error_evidence": {"judge": "static"},
            }

    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )
    start_result.profile["failure_policy"]["on_policy_denial"] = "return_error"
    start_result.profile["failure_policy"]["on_validator_failure"] = "return_error"
    start_result.profile["failure_policy"]["on_budget_exhausted"] = "return_error"
    start_result.profile["limits"]["max_duration_seconds"] = 0
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
        enable_llm_error_judge=True,
        llm_error_judge=StaticJudge(),
    )

    with pytest.raises(RuntimeLoopError):
        loop.run(start_result)

    failed_event = store.runtime_events[-1]
    failed_result = load_artifact(tmp_path, str(failed_event["result_uri"]))
    assert failed_result["error_classification"]["classification_source"] == "llm_judge_v1"
    assert failed_result["error_classification"]["error_class"] == "F2_INTERFACE_CONTRACT_BREAKDOWN"
