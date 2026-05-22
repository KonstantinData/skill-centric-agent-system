from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from skill_centric_agent_system.runtime import (
    FlightRecorder,
    InMemoryRuntimeStore,
    JsonArtifactStore,
    RuntimeEntryPoint,
    RuntimeEntryPointError,
)
from skill_centric_agent_system.runtime.cli import main as runtime_cli_main

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_EXAMPLE_PATH = REPO_ROOT / "examples" / "tasks" / "code-review-task.json"
COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response.json"
)
RUNTIME_PLANE_SCHEMA_PATH = REPO_ROOT / "schemas" / "hetzner-runtime-plane.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_runtime_entrypoint_starts_run_and_emits_flight_recorder_events(
    tmp_path: Path,
) -> None:
    store = InMemoryRuntimeStore()
    runtime = RuntimeEntryPoint(
        store=store,
        artifacts=JsonArtifactStore(tmp_path),
    )

    result = runtime.start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )

    assert result.run_id == "run-code-review-latest-commit"
    assert store.runtime_runs[result.run_id]["profile_id"] == "profile-code-review-latest-commit"
    assert store.runtime_runs[result.run_id]["status"] == "running"

    event_types = [event["event_type"] for event in store.runtime_events]
    assert event_types == [
        "task_analyzed",
        "candidates_discovered",
        "profile_emitted",
        "profile_validated",
        "checkpoint_created",
        "runtime_started",
    ]
    assert store.runtime_checkpoints[0]["phase"] == "composition"

    for event in store.runtime_events:
        assert "planned_action_json" not in event
        assert "execution_json" not in event
        assert "result_json" not in event
        for field in ("planned_action_uri", "execution_uri", "result_uri"):
            uri = event[field]
            if uri is not None:
                assert uri.startswith("hetzner://runtime/")

    recordset = store.as_runtime_plane_recordset()
    Draft202012Validator(load_json(RUNTIME_PLANE_SCHEMA_PATH)).validate(recordset)


def test_flight_recorder_deduplicates_events_by_idempotency_key(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    recorder = FlightRecorder(store, JsonArtifactStore(tmp_path))
    profile = load_json(REPO_ROOT / "examples" / "profiles" / "code-review-profile.json")
    run = recorder.start_run(task_id="task-code-review-latest-commit", profile=profile)

    first = recorder.record_event(
        run_id=str(run["id"]),
        event_type="runtime_started",
        actor_role="composer",
        result={"attempt": 1},
        idempotency_key="same-event",
    )
    second = recorder.record_event(
        run_id=str(run["id"]),
        event_type="runtime_started",
        actor_role="composer",
        result={"attempt": 2},
        idempotency_key="same-event",
    )

    assert first == second
    assert len(store.runtime_events) == 1
    assert store.runtime_events[0]["event_index"] == 0


def test_artifact_store_redacts_sensitive_payload_fields(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    recorder = FlightRecorder(store, JsonArtifactStore(tmp_path))
    profile = load_json(REPO_ROOT / "examples" / "profiles" / "code-review-profile.json")
    run = recorder.start_run(task_id="task-code-review-latest-commit", profile=profile)

    event = recorder.record_event(
        run_id=str(run["id"]),
        event_type="runtime_started",
        actor_role="composer",
        result={
            "public": "visible",
            "openai_api_key": "must-not-leak",
            "nested": {"authorization": "Bearer token"},
        },
    )

    uri = str(event["result_uri"])
    artifact_path = tmp_path / Path(uri.removeprefix("hetzner://runtime/"))
    payload = load_json(artifact_path)
    assert payload == {
        "nested": {"authorization": "[REDACTED]"},
        "openai_api_key": "[REDACTED]",
        "public": "visible",
    }


def test_runtime_entrypoint_requires_context_source(tmp_path: Path) -> None:
    runtime = RuntimeEntryPoint(
        store=InMemoryRuntimeStore(),
        artifacts=JsonArtifactStore(tmp_path),
    )

    with pytest.raises(RuntimeEntryPointError, match="ControlPlaneClient"):
        runtime.start(load_json(TASK_EXAMPLE_PATH))


def test_runtime_cli_starts_fixture_backed_run(tmp_path: Path, capsys: Any) -> None:
    exit_code = runtime_cli_main(
        [
            "--task-file",
            str(TASK_EXAMPLE_PATH),
            "--composition-context-file",
            str(COMPOSITION_CONTEXT_RESPONSE_PATH),
            "--artifact-root",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["run_id"] == "run-code-review-latest-commit"
    assert output["profile_id"] == "profile-code-review-latest-commit"
    assert output["status"] == "running"
