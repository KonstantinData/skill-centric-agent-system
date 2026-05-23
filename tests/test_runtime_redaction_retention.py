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
    RuntimeArtifactUriResolver,
    RuntimeRetentionExecutor,
    RuntimeRetentionPlan,
    RuntimeRetentionPlanner,
    RuntimeRetentionPolicy,
    profile_redacts_sensitive_data,
)
from skill_centric_agent_system.runtime.cli import main as runtime_cli_main

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


def test_retention_executor_dry_run_keeps_expired_artifacts(tmp_path: Path) -> None:
    artifacts = JsonArtifactStore(tmp_path)
    expired_uri = artifacts.write_json(("traces", "run-expired", "events", "result"), {})
    retained_uri = artifacts.write_json(("traces", "run-retained", "events", "result"), {})
    plan = RuntimeRetentionPlan(
        expired_run_ids=("run-expired",),
        expired_artifact_uris=(expired_uri,),
        retained_run_ids=("run-retained",),
        retained_artifact_uris=(retained_uri,),
    )

    report = RuntimeRetentionExecutor(
        RuntimeArtifactUriResolver(tmp_path),
        report_artifacts=artifacts,
    ).apply(plan)

    assert report.dry_run is True
    assert report.dry_run_artifact_uris == (expired_uri,)
    assert report.deleted_artifact_uris == ()
    assert report.report_uri is not None
    assert (tmp_path / expired_uri.removeprefix("hetzner://runtime/")).exists()
    assert (tmp_path / retained_uri.removeprefix("hetzner://runtime/")).exists()


def test_retention_executor_confirm_deletes_only_expired_artifacts(
    tmp_path: Path,
) -> None:
    artifacts = JsonArtifactStore(tmp_path)
    expired_uri = artifacts.write_json(("traces", "run-expired", "events", "result"), {})
    retained_uri = artifacts.write_json(("traces", "run-retained", "events", "result"), {})
    plan = RuntimeRetentionPlan(
        expired_run_ids=("run-expired",),
        expired_artifact_uris=(expired_uri,),
        retained_run_ids=("run-retained",),
        retained_artifact_uris=(retained_uri,),
    )

    report = RuntimeRetentionExecutor(
        RuntimeArtifactUriResolver(tmp_path),
        report_artifacts=artifacts,
    ).apply(plan, dry_run=False)

    assert report.deleted_artifact_uris == (expired_uri,)
    assert report.has_errors is False
    assert not (tmp_path / expired_uri.removeprefix("hetzner://runtime/")).exists()
    assert (tmp_path / retained_uri.removeprefix("hetzner://runtime/")).exists()


def test_retention_executor_reports_missing_artifacts_without_failing_by_default(
    tmp_path: Path,
) -> None:
    missing_uri = "hetzner://runtime/traces/run-expired/events/missing.json"
    plan = RuntimeRetentionPlan(
        expired_run_ids=("run-expired",),
        expired_artifact_uris=(missing_uri,),
        retained_run_ids=(),
        retained_artifact_uris=(),
    )

    report = RuntimeRetentionExecutor(RuntimeArtifactUriResolver(tmp_path)).apply(
        plan,
        dry_run=False,
    )
    strict_report = RuntimeRetentionExecutor(RuntimeArtifactUriResolver(tmp_path)).apply(
        plan,
        dry_run=False,
        strict_missing=True,
    )

    assert report.missing_artifact_uris == (missing_uri,)
    assert report.has_errors is False
    assert strict_report.missing_artifact_uris == (missing_uri,)
    assert strict_report.has_errors is True


def test_retention_executor_blocks_unsafe_artifact_uris(tmp_path: Path) -> None:
    plan = RuntimeRetentionPlan(
        expired_run_ids=("run-expired",),
        expired_artifact_uris=(
            "hetzner://runtime/../outside.json",
            "hetzner://runtime/C:/outside.json",
            "s3://runtime/traces/run-expired/events/result.json",
        ),
        retained_run_ids=(),
        retained_artifact_uris=(),
    )

    report = RuntimeRetentionExecutor(RuntimeArtifactUriResolver(tmp_path)).apply(plan)

    assert report.has_errors is True
    assert report.unsafe_artifact_uris == (
        "hetzner://runtime/../outside.json",
        "hetzner://runtime/C:/outside.json",
        "s3://runtime/traces/run-expired/events/result.json",
    )


def test_retention_cli_plans_and_applies_recordset_fixture(
    tmp_path: Path,
    capsys: Any,
) -> None:
    artifacts = JsonArtifactStore(tmp_path)
    expired_uri = artifacts.write_json(("traces", "run-expired", "events", "result"), {})
    recordset_path = tmp_path / "recordset.json"
    recordset_path.write_text(
        json.dumps(
            {
                "contract_version": "0.2.0",
                "environment": "dev",
                "records": {
                    "runtime_runs": [
                        {
                            "id": "run-expired",
                            "status": "succeeded",
                            "completed_at": "2026-01-01T00:00:00Z",
                        }
                    ],
                    "runtime_events": [
                        {
                            "run_id": "run-expired",
                            "result_uri": expired_uri,
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    assert runtime_cli_main(
        [
            "retention",
            "plan",
            "--recordset-file",
            str(recordset_path),
            "--artifact-root",
            str(tmp_path),
        ]
    ) == 0
    planned = json.loads(capsys.readouterr().out)
    assert planned["expired_run_ids"] == ["run-expired"]
    assert planned["expired_artifact_uris"] == [expired_uri]

    assert runtime_cli_main(
        [
            "retention",
            "apply",
            "--recordset-file",
            str(recordset_path),
            "--artifact-root",
            str(tmp_path),
            "--confirm",
        ]
    ) == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["deleted_artifact_uris"] == [expired_uri]
    assert applied["report_uri"].startswith("hetzner://runtime/retention-reports/")
