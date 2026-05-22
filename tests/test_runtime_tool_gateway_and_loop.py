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
    RuntimeEntryPoint,
    ToolDeniedError,
    ToolGateway,
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
        "tool_invocation_started",
        "tool_invocation_completed",
    ]


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
