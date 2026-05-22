from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class RuntimeRetentionPolicy:
    succeeded_run_artifact_days: int = 30
    failed_run_artifact_days: int = 90
    cancelled_run_artifact_days: int = 30


@dataclass(frozen=True)
class RuntimeRetentionPlan:
    expired_run_ids: tuple[str, ...]
    expired_artifact_uris: tuple[str, ...]
    retained_run_ids: tuple[str, ...]
    retained_artifact_uris: tuple[str, ...]


class RuntimeRetentionPlanner:
    """Plan runtime artifact cleanup without deleting data."""

    def __init__(self, policy: RuntimeRetentionPolicy | None = None) -> None:
        self.policy = policy or RuntimeRetentionPolicy()

    def plan(
        self,
        runtime_plane_recordset: Mapping[str, Any],
        *,
        now: datetime | None = None,
    ) -> RuntimeRetentionPlan:
        timestamp = (now or datetime.now(UTC)).astimezone(UTC)
        records = runtime_plane_recordset.get("records", {})
        if not isinstance(records, Mapping):
            raise ValueError("runtime_plane_recordset.records must be an object.")

        runs = _records_by_id(records.get("runtime_runs", []))
        expired_run_ids: list[str] = []
        retained_run_ids: list[str] = []
        for run_id, run in runs.items():
            if _run_is_expired(run, timestamp, self.policy):
                expired_run_ids.append(run_id)
            else:
                retained_run_ids.append(run_id)

        expired_set = set(expired_run_ids)
        expired_artifact_uris: list[str] = []
        retained_artifact_uris: list[str] = []
        for run_id, uri in _iter_runtime_artifact_uris(records):
            if run_id in expired_set:
                expired_artifact_uris.append(uri)
            else:
                retained_artifact_uris.append(uri)

        return RuntimeRetentionPlan(
            expired_run_ids=tuple(sorted(expired_run_ids)),
            expired_artifact_uris=tuple(sorted(set(expired_artifact_uris))),
            retained_run_ids=tuple(sorted(retained_run_ids)),
            retained_artifact_uris=tuple(sorted(set(retained_artifact_uris))),
        )


def _run_is_expired(
    run: Mapping[str, Any],
    now: datetime,
    policy: RuntimeRetentionPolicy,
) -> bool:
    status = str(run.get("status") or "")
    completed_at = run.get("completed_at")
    if status in {"queued", "running"} or completed_at is None:
        return False

    completed = _parse_datetime(str(completed_at))
    if status == "failed":
        retention = timedelta(days=policy.failed_run_artifact_days)
    elif status == "cancelled":
        retention = timedelta(days=policy.cancelled_run_artifact_days)
    else:
        retention = timedelta(days=policy.succeeded_run_artifact_days)
    return completed + retention <= now


def _records_by_id(raw_records: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(raw_records, list):
        return {}
    return {
        str(record["id"]): record
        for record in raw_records
        if isinstance(record, Mapping) and "id" in record
    }


def _iter_runtime_artifact_uris(records: Mapping[str, Any]) -> Any:
    for event in _list_records(records, "runtime_events"):
        run_id = str(event["run_id"])
        for field in ("planned_action_uri", "execution_uri", "result_uri"):
            uri = event.get(field)
            if isinstance(uri, str):
                yield run_id, uri

    for checkpoint in _list_records(records, "runtime_checkpoints"):
        uri = checkpoint.get("state_uri")
        if isinstance(uri, str):
            yield str(checkpoint["run_id"]), uri

    for invocation in _list_records(records, "tool_invocations"):
        run_id = str(invocation["run_id"])
        for field in ("input_uri", "output_uri"):
            uri = invocation.get(field)
            if isinstance(uri, str):
                yield run_id, uri

    for validation in _list_records(records, "validation_results"):
        uri = validation.get("findings_uri")
        if isinstance(uri, str):
            yield str(validation["run_id"]), uri

    for candidate in _list_records(records, "memory_candidates"):
        uri = candidate.get("content_uri")
        if isinstance(uri, str):
            yield str(candidate["run_id"]), uri


def _list_records(records: Mapping[str, Any], field: str) -> list[Mapping[str, Any]]:
    values = records.get(field, [])
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, Mapping)]


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
