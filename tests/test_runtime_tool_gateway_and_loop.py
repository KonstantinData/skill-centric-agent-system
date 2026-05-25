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
    FilesystemListAdapter,
    FilesystemReadAdapter,
    FilesystemWriteAdapter,
    GitReadAdapter,
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


def test_filesystem_list_adapter_clamps_entries(tmp_path: Path) -> None:
    for index in range(3):
        (tmp_path / f"file-{index}.txt").write_text("content", encoding="utf-8")
    adapter = FilesystemListAdapter(tmp_path)

    output = adapter.invoke({"path": ".", "max_entries": 2})

    assert output["entry_count"] == 2
    assert output["truncated"] is True
    assert [entry["kind"] for entry in output["entries"]] == ["file", "file"]


def test_git_read_adapter_blocks_config_and_worktree_escape_args() -> None:
    adapter = GitReadAdapter(REPO_ROOT)

    with pytest.raises(ValueError, match="not allowed"):
        adapter.invoke({"args": ["status", "--git-dir=.git"]})


def write_enabled_profile() -> dict[str, Any]:
    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["task_type"] = "task-execution"
    profile["risk_level"] = "high"
    profile["skills"] = []
    profile["tools"] = ["filesystem-write"]
    profile["knowledge_scopes"] = []
    profile["data_scopes"] = ["repository-write"]
    profile["memory_scopes"] = []
    profile["policies"] = ["write-approval-required"]
    profile["validators"] = ["task-execution-output-contract"]
    profile["module_versions"].update(
        {
            "filesystem-write": "0.1.0",
            "repository-write": "0.1.0",
            "write-approval-required": "0.1.0",
            "task-execution-output-contract": "0.1.0",
        }
    )
    profile["limits"]["max_data_reads"] = 10
    return profile


def approved_write_payload(*, apply: bool = False) -> dict[str, Any]:
    return {
        "operation": "write_text_file",
        "path": "notes/output.txt",
        "content": "approved content\n",
        "apply": apply,
        "approval": {
            "approval_id": "approval-p5-05-fixture",
            "approved_by": "repository-maintainer",
            "approved_at": "2026-05-24T18:00:00Z",
            "policy_id": "write-approval-required",
        },
        "rollback": {
            "strategy": "delete_created_file",
            "reason": "Delete the newly created file if validation fails.",
        },
    }


def test_filesystem_write_adapter_rejects_free_form_command(tmp_path: Path) -> None:
    adapter = FilesystemWriteAdapter(tmp_path)

    with pytest.raises(ValueError, match="structured write plans"):
        adapter.invoke({"command": "rm -rf ."})


def test_filesystem_write_adapter_rejects_non_boolean_apply(tmp_path: Path) -> None:
    adapter = FilesystemWriteAdapter(tmp_path)
    payload = approved_write_payload()
    payload["apply"] = "false"

    with pytest.raises(ValueError, match="apply must be a boolean"):
        adapter.invoke(payload)


def test_filesystem_write_adapter_rejects_absolute_path(tmp_path: Path) -> None:
    adapter = FilesystemWriteAdapter(tmp_path)
    payload = approved_write_payload()
    payload["path"] = str(tmp_path / "output.txt")

    with pytest.raises(ValueError, match="path must be relative"):
        adapter.invoke(payload)


def test_tool_gateway_plans_profile_approved_write_without_applying(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    recorder = FlightRecorder(store, JsonArtifactStore(tmp_path / "artifacts"))
    profile = write_enabled_profile()
    run = recorder.start_run(task_id="task-controlled-write", profile=profile)
    step = recorder.start_step(run_id=str(run["id"]), step_index=0, kind="executor")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    gateway = ToolGateway(
        profile=profile,
        run_id=str(run["id"]),
        step_id=str(step["id"]),
        recorder=recorder,
        repository_root=workspace,
    )

    result = gateway.invoke("filesystem-write", approved_write_payload())

    assert result.status == "succeeded"
    assert result.output["status"] == "planned"
    assert not (workspace / "notes" / "output.txt").exists()
    access_event = store.runtime_events[0]
    access_result = load_artifact(tmp_path / "artifacts", str(access_event["result_uri"]))
    assert access_result["required_data_scopes"] == ["repository-write"]
    assert access_result["required_policies"] == ["write-approval-required"]
    output_payload = load_artifact(tmp_path / "artifacts", result.output_uri)
    assert output_payload["output"]["approval"]["approval_id"] == "approval-p5-05-fixture"
    assert output_payload["output"]["rollback"]["metadata_only"] is True


def test_tool_gateway_applies_profile_approved_write(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    recorder = FlightRecorder(store, JsonArtifactStore(tmp_path / "artifacts"))
    profile = write_enabled_profile()
    run = recorder.start_run(task_id="task-controlled-write", profile=profile)
    step = recorder.start_step(run_id=str(run["id"]), step_index=0, kind="executor")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    gateway = ToolGateway(
        profile=profile,
        run_id=str(run["id"]),
        step_id=str(step["id"]),
        recorder=recorder,
        repository_root=workspace,
    )

    result = gateway.invoke("filesystem-write", approved_write_payload(apply=True))

    assert result.output["status"] == "applied"
    assert (workspace / "notes" / "output.txt").read_text(encoding="utf-8") == (
        "approved content\n"
    )
    assert store.tool_invocations[0]["tool_name"] == "filesystem-write"


def test_tool_gateway_denies_write_without_required_policy(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    recorder = FlightRecorder(store, JsonArtifactStore(tmp_path / "artifacts"))
    profile = write_enabled_profile()
    profile["policies"] = []
    run = recorder.start_run(task_id="task-controlled-write", profile=profile)
    step = recorder.start_step(run_id=str(run["id"]), step_index=0, kind="executor")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    gateway = ToolGateway(
        profile=profile,
        run_id=str(run["id"]),
        step_id=str(step["id"]),
        recorder=recorder,
        repository_root=workspace,
    )

    with pytest.raises(ToolDeniedError, match="Policy is not allowed"):
        gateway.invoke("filesystem-write", approved_write_payload(apply=True))

    assert not (workspace / "notes" / "output.txt").exists()


def test_filesystem_write_adapter_requires_restore_rollback_for_overwrite(
    tmp_path: Path,
) -> None:
    target = tmp_path / "notes" / "output.txt"
    target.parent.mkdir()
    target.write_text("previous\n", encoding="utf-8")
    adapter = FilesystemWriteAdapter(tmp_path)
    payload = approved_write_payload(apply=True)

    with pytest.raises(ValueError, match="restore_previous_content"):
        adapter.invoke(payload)

    payload["rollback"]["strategy"] = "restore_previous_content"
    output = adapter.invoke(payload)

    assert output["status"] == "applied"
    assert output["existed_before"] is True
    assert output["previous_content_sha256"] is not None
    assert target.read_text(encoding="utf-8") == "approved content\n"


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
    assert result.response["error_classification"]["error_class"] in {
        "NONE",
        "F1_INEFFICIENCY_PATH",
    }
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
    assert [result["validator_id"] for result in store.validation_results] == [
        "runtime-profile-schema",
        "review-findings-contract",
    ]
    assert [result["status"] for result in store.validation_results] == [
        "passed",
        "passed",
    ]

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


@pytest.mark.parametrize(
    ("task_path", "context_response_path", "expected_task_type", "expected_validator"),
    [
        (
            RESEARCH_TASK_EXAMPLE_PATH,
            RESEARCH_COMPOSITION_CONTEXT_RESPONSE_PATH,
            "research",
            "research-output-contract",
        ),
        (
            TASK_EXECUTION_TASK_EXAMPLE_PATH,
            TASK_EXECUTION_COMPOSITION_CONTEXT_RESPONSE_PATH,
            "task-execution",
            "task-execution-output-contract",
        ),
        (
            GENERAL_TASK_EXAMPLE_PATH,
            GENERAL_COMPOSITION_CONTEXT_RESPONSE_PATH,
            "general-task",
            "general-output-contract",
        ),
    ],
)
def test_minimal_runtime_loop_dispatches_task_type_strategies(
    tmp_path: Path,
    task_path: Path,
    context_response_path: Path,
    expected_task_type: str,
    expected_validator: str,
) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        load_json(task_path),
        composition_context_response=load_json(context_response_path),
    )
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
    )

    result = loop.run(start_result)

    assert result.status == "succeeded"
    assert result.response["task_type"] == expected_task_type
    assert result.response["runtime_output"]["task_type"] == expected_task_type
    assert result.response["runtime_output"]["status"] == "completed"
    assert expected_validator in [record["validator_id"] for record in store.validation_results]
    validator_record = next(
        record
        for record in store.validation_results
        if record["validator_id"] == expected_validator
    )
    assert validator_record["status"] == "passed"
