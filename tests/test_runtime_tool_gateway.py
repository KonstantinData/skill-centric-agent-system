from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from skill_centric_agent_system.runtime import (
    FlightRecorder,
    InMemoryRuntimeStore,
    JsonArtifactStore,
    ToolDeniedError,
    ToolGateway,
)
from skill_centric_agent_system.runtime.tool_gateway import (
    FilesystemListAdapter,
    FilesystemReadAdapter,
    FilesystemWriteAdapter,
    GitReadAdapter,
)
from tests.runtime_gateway_support import approved_write_payload, write_enabled_profile

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
