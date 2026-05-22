from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from skill_centric_agent_system.runtime import (
    FlightRecorder,
    InMemoryRuntimeStore,
    JsonArtifactStore,
    RuntimeRetentionPlanner,
    RuntimeRetentionPolicy,
    profile_redacts_sensitive_data,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_EXAMPLE_PATH = REPO_ROOT / "examples" / "profiles" / "code-review-profile.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_profile_redaction_policy_defaults_closed() -> None:
    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    assert profile_redacts_sensitive_data(profile) is True

    profile["observability"]["redact_sensitive_data"] = False
    assert profile_redacts_sensitive_data(profile) is False

    profile.pop("observability")
    assert profile_redacts_sensitive_data(profile) is True


def test_flight_recorder_honors_explicit_redaction_flag(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    recorder = FlightRecorder(store, JsonArtifactStore(tmp_path))
    profile = load_json(PROFILE_EXAMPLE_PATH)
    run = recorder.start_run(task_id="task-code-review-latest-commit", profile=profile)

    redacted = recorder.record_event(
        run_id=str(run["id"]),
        event_type="runtime_started",
        actor_role="composer",
        result={"token": "secret-value"},
        redact_sensitive_data=True,
    )
    unredacted = recorder.record_event(
        run_id=str(run["id"]),
        event_type="runtime_started",
        actor_role="composer",
        result={"token": "secret-value"},
        redact_sensitive_data=False,
    )

    redacted_path = tmp_path / str(redacted["result_uri"]).removeprefix("hetzner://runtime/")
    unredacted_path = tmp_path / str(unredacted["result_uri"]).removeprefix(
        "hetzner://runtime/"
    )
    assert load_json(redacted_path)["token"] == "[REDACTED]"
    assert load_json(unredacted_path)["token"] == "secret-value"


def test_retention_planner_marks_expired_run_artifacts_without_deleting(
    tmp_path: Path,
) -> None:
    store = InMemoryRuntimeStore()
    recorder = FlightRecorder(store, JsonArtifactStore(tmp_path))
    profile = load_json(PROFILE_EXAMPLE_PATH)
    run = recorder.start_run(task_id="task-code-review-latest-commit", profile=profile)
    recorder.record_event(
        run_id=str(run["id"]),
        event_type="runtime_completed",
        actor_role="validator",
        result={"summary": "done"},
        stop_reason="completed",
    )
    recorder.complete_run(
        run_id=str(run["id"]),
        status="succeeded",
        stop_reason="completed",
    )
    store.runtime_runs[str(run["id"])]["completed_at"] = "2026-01-01T00:00:00Z"

    plan = RuntimeRetentionPlanner(
        RuntimeRetentionPolicy(succeeded_run_artifact_days=30)
    ).plan(
        store.as_runtime_plane_recordset(),
        now=datetime(2026, 5, 22, tzinfo=UTC),
    )

    assert plan.expired_run_ids == (str(run["id"]),)
    assert plan.expired_artifact_uris
    assert plan.retained_run_ids == ()
