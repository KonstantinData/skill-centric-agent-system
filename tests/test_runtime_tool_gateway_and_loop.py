from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from skill_centric_agent_system.runtime import (
    FlightRecorder,
    InMemoryRuntimeStore,
    JsonArtifactStore,
    MinimalRuntimeLoop,
    ProfileEnforcementError,
    RuntimeContextManager,
    RuntimeEntryPoint,
    RuntimeLoopError,
    RuntimeProfileEnforcer,
    ToolDeniedError,
    ToolGateway,
)
from skill_centric_agent_system.runtime.tool_gateway import (
    FilesystemReadAdapter,
    GitReadAdapter,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_EXAMPLE_PATH = REPO_ROOT / "examples" / "tasks" / "code-review-task.json"
PROFILE_EXAMPLE_PATH = REPO_ROOT / "examples" / "profiles" / "code-review-profile.json"
COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response.json"
)
RUNTIME_PLANE_SCHEMA_PATH = REPO_ROOT / "schemas" / "hetzner-runtime-plane.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_artifact(root: Path, uri: str) -> dict[str, Any]:
    artifact_path = root / Path(uri.removeprefix("hetzner://runtime/"))
    return load_json(artifact_path)


def test_profile_enforcer_denies_unselected_knowledge_and_memory_scopes() -> None:
    profile = load_json(PROFILE_EXAMPLE_PATH)
    enforcer = RuntimeProfileEnforcer(profile)

    with pytest.raises(ProfileEnforcementError) as knowledge_error:
        enforcer.require_knowledge_scopes(["outside-knowledge"])
    with pytest.raises(ProfileEnforcementError) as memory_error:
        enforcer.require_memory_scopes(["project-memory"])

    assert knowledge_error.value.stop_reason == "policy_denied"
    assert knowledge_error.value.code == "knowledge_scope_not_in_runtime_profile"
    assert memory_error.value.stop_reason == "policy_denied"
    assert memory_error.value.code == "memory_scope_not_in_runtime_profile"


def test_profile_enforcer_enforces_token_and_memory_budgets() -> None:
    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["limits"]["max_tokens"] = 1
    profile["limits"]["max_memory_ops"] = 0
    token_enforcer = RuntimeProfileEnforcer(profile)
    memory_enforcer = RuntimeProfileEnforcer(profile)

    with pytest.raises(ProfileEnforcementError) as token_error:
        token_enforcer.consume_tokens(2)
    with pytest.raises(ProfileEnforcementError) as memory_error:
        memory_enforcer.record_memory_op()

    assert token_error.value.stop_reason == "max_tokens"
    assert memory_error.value.stop_reason == "max_memory_ops"


def test_tool_gateway_denies_tools_not_in_runtime_profile(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    recorder = FlightRecorder(store, JsonArtifactStore(tmp_path))
    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["tools"] = ["filesystem-read"]
    run = recorder.start_run(task_id="task-code-review-latest-commit", profile=profile)
    step = recorder.start_step(run_id=str(run["id"]), step_index=0, kind="executor")
    gateway = ToolGateway(
        profile=profile,
        run_id=str(run["id"]),
        step_id=str(step["id"]),
        recorder=recorder,
        repository_root=REPO_ROOT,
    )

    with pytest.raises(ToolDeniedError, match="not allowed"):
        gateway.invoke("git-read", {"args": ["status", "--short"]})

    event = store.runtime_events[-1]
    assert event["event_type"] == "access_attempted"
    assert event["actor_role"] == "policy_engine"
    assert event["stop_reason"] == "policy_denied"
    assert store.tool_invocations == []


def test_tool_gateway_enforces_profile_tool_call_budget(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    recorder = FlightRecorder(store, JsonArtifactStore(tmp_path))
    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["limits"]["max_tool_calls"] = 0
    run = recorder.start_run(task_id="task-code-review-latest-commit", profile=profile)
    step = recorder.start_step(run_id=str(run["id"]), step_index=0, kind="executor")
    gateway = ToolGateway(
        profile=profile,
        run_id=str(run["id"]),
        step_id=str(step["id"]),
        recorder=recorder,
        repository_root=REPO_ROOT,
    )

    with pytest.raises(ToolDeniedError) as exc_info:
        gateway.invoke("git-read", {"args": ["status", "--short"]})

    assert exc_info.value.stop_reason == "max_tool_calls"
    assert store.runtime_events[-1]["event_type"] == "access_attempted"
    assert store.runtime_events[-1]["stop_reason"] == "max_tool_calls"
    assert store.tool_invocations == []


def test_tool_gateway_enforces_required_data_scope(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    recorder = FlightRecorder(store, JsonArtifactStore(tmp_path))
    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["data_scopes"] = []
    run = recorder.start_run(task_id="task-code-review-latest-commit", profile=profile)
    step = recorder.start_step(run_id=str(run["id"]), step_index=0, kind="executor")
    gateway = ToolGateway(
        profile=profile,
        run_id=str(run["id"]),
        step_id=str(step["id"]),
        recorder=recorder,
        repository_root=REPO_ROOT,
    )

    with pytest.raises(ToolDeniedError) as exc_info:
        gateway.invoke("filesystem-read", {"path": "README.md"})

    assert exc_info.value.stop_reason == "policy_denied"
    assert store.runtime_events[-1]["event_type"] == "access_attempted"
    assert store.runtime_events[-1]["stop_reason"] == "policy_denied"
    assert store.tool_invocations == []


def test_tool_gateway_enforces_tool_risk_gate(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    recorder = FlightRecorder(store, JsonArtifactStore(tmp_path))
    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["risk_level"] = "low"
    run = recorder.start_run(task_id="task-code-review-latest-commit", profile=profile)
    step = recorder.start_step(run_id=str(run["id"]), step_index=0, kind="executor")
    gateway = ToolGateway(
        profile=profile,
        run_id=str(run["id"]),
        step_id=str(step["id"]),
        recorder=recorder,
        repository_root=REPO_ROOT,
    )

    with pytest.raises(ToolDeniedError) as exc_info:
        gateway.invoke("test-runner", {"pytest_args": ["tests/test_repository_neutrality.py"]})

    assert exc_info.value.stop_reason == "policy_denied"
    assert store.runtime_events[-1]["event_type"] == "access_attempted"
    result_payload = load_artifact(tmp_path, str(store.runtime_events[-1]["result_uri"]))
    assert result_payload["reason"] == "tool_risk_exceeds_profile"


def test_tool_gateway_records_allowed_tool_invocation(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    recorder = FlightRecorder(store, JsonArtifactStore(tmp_path))
    profile = load_json(PROFILE_EXAMPLE_PATH)
    run = recorder.start_run(task_id="task-code-review-latest-commit", profile=profile)
    step = recorder.start_step(run_id=str(run["id"]), step_index=0, kind="executor")
    gateway = ToolGateway(
        profile=profile,
        run_id=str(run["id"]),
        step_id=str(step["id"]),
        recorder=recorder,
        repository_root=REPO_ROOT,
    )

    result = gateway.invoke("filesystem-read", {"path": "README.md", "max_bytes": 120})

    assert result.status == "succeeded"
    assert result.tool_name == "filesystem-read"
    assert store.tool_invocations[0]["input_uri"].startswith("hetzner://runtime/")
    assert store.tool_invocations[0]["output_uri"].startswith("hetzner://runtime/")
    assert [event["event_type"] for event in store.runtime_events] == [
        "access_attempted",
        "tool_invocation_started",
        "tool_invocation_completed",
    ]
    result_payload = load_artifact(tmp_path, str(store.runtime_events[0]["result_uri"]))
    assert result_payload["effect"] == "allow"


def test_filesystem_read_adapter_clamps_output_bytes(tmp_path: Path) -> None:
    large_file = tmp_path / "large.txt"
    large_file.write_text("x" * 120_000, encoding="utf-8")
    adapter = FilesystemReadAdapter(tmp_path)

    output = adapter.invoke({"path": "large.txt", "max_bytes": 200_000})

    assert output["bytes_read"] == FilesystemReadAdapter.MAX_FILE_BYTES
    assert output["truncated"] is True


def test_git_read_adapter_blocks_config_and_worktree_escape_args() -> None:
    adapter = GitReadAdapter(REPO_ROOT)

    with pytest.raises(ValueError, match="not allowed"):
        adapter.invoke({"args": ["status", "--git-dir=.git"]})


def test_minimal_runtime_loop_executes_profile_scoped_read_tools(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
    )

    result = loop.run(start_result)

    assert result.status == "succeeded"
    assert store.runtime_runs[result.run_id]["status"] == "succeeded"
    assert store.runtime_runs[result.run_id]["stop_reason"] == "completed"
    assert [step["kind"] for step in store.runtime_steps.values()] == [
        "context",
        "planner",
        "executor",
        "validator",
    ]
    assert [invocation["tool_name"] for invocation in store.tool_invocations] == [
        "git-read",
        "filesystem-read",
    ]
    assert store.validation_results[0]["status"] == "passed"

    event_types = [event["event_type"] for event in store.runtime_events]
    assert "runtime_started" in event_types
    assert "tool_invocation_started" in event_types
    assert "tool_invocation_completed" in event_types
    assert event_types[-1] == "runtime_completed"

    recordset = store.as_runtime_plane_recordset()
    Draft202012Validator(load_json(RUNTIME_PLANE_SCHEMA_PATH)).validate(recordset)


def test_minimal_runtime_loop_loads_retrieval_context_through_control_plane(
    tmp_path: Path,
) -> None:
    class FakeRetrievalClient:
        def __init__(self) -> None:
            self.requests: list[Mapping[str, Any]] = []

        def retrieval_context(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
            self.requests.append(dict(request_body))
            return {
                "contract_version": "0.1.0",
                "retrieval_status": "ready",
                "query": request_body["query"],
                "vectorize": {
                    "status": "d1_prefilter_ready",
                    "knowledge_index": "scas-knowledge-dev",
                    "memory_index": "scas-memory-dev",
                    "bindings": {"knowledge": True, "memory": True},
                    "note": "D1 prefilter only.",
                },
                "allowed_knowledge_scope_ids": list(request_body["knowledge_scope_ids"]),
                "allowed_memory_scope_ids": list(request_body["memory_scope_ids"]),
                "knowledge_chunks": [],
                "memory_records": [],
                "vectorize_matches": {"knowledge": [], "memory": []},
            }

    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    client = FakeRetrievalClient()
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
        control_plane_client=client,
    )

    loop.run(start_result)

    assert client.requests
    request = client.requests[0]
    assert request["principal"] == {"kind": "role", "id": "repository-maintainer"}
    assert request["knowledge_scope_ids"] == [
        "mod-architecture-docs",
        "mod-coding-guidelines",
    ]
    assert request["memory_scope_ids"] == []
    context_checkpoint = next(
        checkpoint for checkpoint in store.runtime_checkpoints if checkpoint["phase"] == "context"
    )
    context_payload = load_artifact(tmp_path, str(context_checkpoint["state_uri"]))
    assert context_payload["retrieval_response"]["retrieval_status"] == "ready"


def test_runtime_context_manager_rejects_retrieval_scopes_outside_profile() -> None:
    class BadRetrievalClient:
        def retrieval_context(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
            return {
                "contract_version": "0.1.0",
                "retrieval_status": "ready",
                "query": request_body["query"],
                "vectorize": {
                    "status": "d1_prefilter_ready",
                    "knowledge_index": "scas-knowledge-dev",
                    "memory_index": "scas-memory-dev",
                    "bindings": {"knowledge": True, "memory": True},
                    "note": "D1 prefilter only.",
                },
                "allowed_knowledge_scope_ids": ["mod-outside-knowledge"],
                "allowed_memory_scope_ids": [],
                "knowledge_chunks": [],
                "memory_records": [],
                "vectorize_matches": {"knowledge": [], "memory": []},
            }

    profile = load_json(PROFILE_EXAMPLE_PATH)
    manager = RuntimeContextManager(
        enforcer=RuntimeProfileEnforcer(profile),
        control_plane_client=BadRetrievalClient(),
    )

    with pytest.raises(ProfileEnforcementError) as exc_info:
        manager.load(profile, query=profile["objective"])

    assert exc_info.value.code == "retrieval_response_scope_not_in_runtime_profile"


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


def test_postgres_runtime_store_uses_uri_tool_and_validation_payloads() -> None:
    class FakeConnection:
        def __init__(self) -> None:
            self.calls: list[tuple[str, Mapping[str, Any] | None]] = []

        def execute(self, sql: str, params: Mapping[str, Any] | None = None) -> Any:
            self.calls.append((sql, params))
            return self

        def fetchall(self) -> list[Mapping[str, Any]]:
            return []

    from skill_centric_agent_system.runtime.storage import PostgresRuntimeStore

    fake = FakeConnection()
    store = PostgresRuntimeStore(fake)
    store.insert_tool_invocation(
        {
            "id": "tool-example",
            "run_id": "run-example",
            "step_id": "step-example",
            "tool_name": "git-read",
            "status": "succeeded",
            "input_uri": "hetzner://runtime/tool/input.json",
            "output_uri": "hetzner://runtime/tool/output.json",
            "started_at": "2026-05-22T08:00:00Z",
            "completed_at": "2026-05-22T08:00:01Z",
        }
    )
    store.insert_validation_result(
        {
            "id": "validation-example",
            "run_id": "run-example",
            "step_id": "step-example",
            "validator_id": "review-findings-contract",
            "status": "passed",
            "findings_uri": "hetzner://runtime/findings.json",
            "created_at": "2026-05-22T08:00:02Z",
        }
    )
    store.insert_memory_candidate(
        {
            "id": "mc-example",
            "run_id": "run-example",
            "profile_id": "profile-example",
            "source_step_id": "step-example",
            "target_memory_scope_id": "mod-project-memory",
            "content_uri": "hetzner://runtime/memory/candidate.json",
            "sensitivity": "internal",
            "retention_policy": "project-memory-180d",
            "validator_status": "pending",
            "validator_id": "memory-candidate-contract",
            "policy_status": "pending",
            "policy_id": "mod-no-destructive-commands",
            "created_at": "2026-05-22T08:00:03Z",
        }
    )
    store.update_memory_candidate(
        "mc-example",
        {
            "validator_status": "approved",
            "validation_reason": "passed",
            "policy_status": "approved",
            "policy_reason": "allowed",
        },
    )

    sql = "\n".join(call[0] for call in fake.calls)
    assert "input_uri" in sql
    assert "output_uri" in sql
    assert "findings_uri" in sql
    assert "validation_reason" in sql
    assert "policy_reason" in sql
    assert "input_json" not in sql
    assert "output_json" not in sql
    assert "findings_json" not in sql
