from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any

from skill_centric_agent_system.runtime.artifacts import JsonArtifactStore
from skill_centric_agent_system.runtime.models import iso_timestamp, utc_now


@dataclass(frozen=True)
class RuntimeRetentionPolicy:
    succeeded_run_artifact_days: int = 30
    failed_run_artifact_days: int = 90
    cancelled_run_artifact_days: int = 30
    cleanup_report_artifact_days: int = 180


@dataclass(frozen=True)
class RuntimeRetentionPlan:
    expired_run_ids: tuple[str, ...]
    expired_artifact_uris: tuple[str, ...]
    retained_run_ids: tuple[str, ...]
    retained_artifact_uris: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedArtifactUri:
    uri: str
    path: Path


@dataclass(frozen=True)
class RuntimeRetentionCleanupReport:
    created_at: str
    dry_run: bool
    strict_missing: bool
    cleanup_report_artifact_days: int
    expired_run_ids: tuple[str, ...]
    retained_run_ids: tuple[str, ...]
    deleted_artifact_uris: tuple[str, ...] = ()
    dry_run_artifact_uris: tuple[str, ...] = ()
    missing_artifact_uris: tuple[str, ...] = ()
    unsafe_artifact_uris: tuple[str, ...] = ()
    failed_artifact_uris: tuple[str, ...] = ()
    retained_artifact_uris: tuple[str, ...] = ()
    errors: tuple[dict[str, str], ...] = ()
    report_uri: str | None = None

    @property
    def has_errors(self) -> bool:
        return bool(self.unsafe_artifact_uris or self.failed_artifact_uris or self.errors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "dry_run": self.dry_run,
            "strict_missing": self.strict_missing,
            "cleanup_report_artifact_days": self.cleanup_report_artifact_days,
            "expired_run_ids": list(self.expired_run_ids),
            "retained_run_ids": list(self.retained_run_ids),
            "deleted_artifact_uris": list(self.deleted_artifact_uris),
            "dry_run_artifact_uris": list(self.dry_run_artifact_uris),
            "missing_artifact_uris": list(self.missing_artifact_uris),
            "unsafe_artifact_uris": list(self.unsafe_artifact_uris),
            "failed_artifact_uris": list(self.failed_artifact_uris),
            "retained_artifact_uris": list(self.retained_artifact_uris),
            "errors": list(self.errors),
            "report_uri": self.report_uri,
        }

    def with_report_uri(self, report_uri: str) -> RuntimeRetentionCleanupReport:
        return RuntimeRetentionCleanupReport(
            created_at=self.created_at,
            dry_run=self.dry_run,
            strict_missing=self.strict_missing,
            cleanup_report_artifact_days=self.cleanup_report_artifact_days,
            expired_run_ids=self.expired_run_ids,
            retained_run_ids=self.retained_run_ids,
            deleted_artifact_uris=self.deleted_artifact_uris,
            dry_run_artifact_uris=self.dry_run_artifact_uris,
            missing_artifact_uris=self.missing_artifact_uris,
            unsafe_artifact_uris=self.unsafe_artifact_uris,
            failed_artifact_uris=self.failed_artifact_uris,
            retained_artifact_uris=self.retained_artifact_uris,
            errors=self.errors,
            report_uri=report_uri,
        )


class RuntimeRetentionError(RuntimeError):
    """Raised when runtime retention cleanup cannot be planned or applied safely."""


@dataclass(frozen=True)
class RuntimeArtifactUriResolver:
    """Resolve Hetzner runtime artifact URIs without allowing filesystem escape."""

    artifact_root: Path | str
    uri_prefix: str = "hetzner://runtime"
    _resolved_root: Path = field(init=False, repr=False)

    def __post_init__(self) -> None:
        root = Path(self.artifact_root).expanduser()
        object.__setattr__(self, "_resolved_root", root.resolve(strict=False))

    @property
    def root(self) -> Path:
        return self._resolved_root

    def resolve(self, uri: str) -> ResolvedArtifactUri:
        relative = self._relative_uri_path(uri)
        target = (self.root / Path(*relative.parts)).resolve(strict=False)
        if not target.is_relative_to(self.root):
            raise RuntimeRetentionError(f"Artifact URI escapes runtime root: {uri}")
        return ResolvedArtifactUri(uri=uri, path=target)

    def _relative_uri_path(self, uri: str) -> PurePosixPath:
        prefix = self.uri_prefix.rstrip("/")
        if not uri.startswith(f"{prefix}/"):
            raise RuntimeRetentionError(f"Unsupported runtime artifact URI: {uri}")

        raw = uri.removeprefix(f"{prefix}/")
        relative = PurePosixPath(raw)
        if relative.is_absolute():
            raise RuntimeRetentionError(f"Absolute artifact paths are not allowed: {uri}")
        if not relative.parts:
            raise RuntimeRetentionError(f"Artifact URI has no relative path: {uri}")
        if any(part in {"", ".", ".."} for part in relative.parts):
            raise RuntimeRetentionError(f"Unsafe artifact URI path segment: {uri}")
        if any("\\" in part or ":" in part for part in relative.parts):
            raise RuntimeRetentionError(f"Platform-specific artifact path segment: {uri}")
        return relative


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


class RuntimeRetentionExecutor:
    """Apply a retention plan to runtime artifacts with dry-run as the default."""

    def __init__(
        self,
        resolver: RuntimeArtifactUriResolver,
        *,
        policy: RuntimeRetentionPolicy | None = None,
        report_artifacts: JsonArtifactStore | None = None,
        clock: Any = utc_now,
    ) -> None:
        self.resolver = resolver
        self.policy = policy or RuntimeRetentionPolicy()
        self.report_artifacts = report_artifacts
        self.clock = clock

    def apply(
        self,
        plan: RuntimeRetentionPlan,
        *,
        dry_run: bool = True,
        strict_missing: bool = False,
        persist_report: bool = True,
    ) -> RuntimeRetentionCleanupReport:
        created_at = iso_timestamp(self.clock())
        deleted: list[str] = []
        dry_run_uris: list[str] = []
        missing: list[str] = []
        unsafe: list[str] = []
        failed: list[str] = []
        errors: list[dict[str, str]] = []

        retained_set = set(plan.retained_artifact_uris)
        for uri in plan.expired_artifact_uris:
            if uri in retained_set:
                unsafe.append(uri)
                errors.append(
                    {
                        "uri": uri,
                        "reason": "artifact_uri_is_also_retained",
                    }
                )
                continue

            try:
                resolved = self.resolver.resolve(uri)
            except RuntimeRetentionError as error:
                unsafe.append(uri)
                errors.append({"uri": uri, "reason": str(error)})
                continue

            if resolved.path.is_dir():
                unsafe.append(uri)
                errors.append({"uri": uri, "reason": "artifact_uri_resolves_to_directory"})
                continue

            if not resolved.path.exists():
                missing.append(uri)
                if strict_missing:
                    errors.append({"uri": uri, "reason": "artifact_file_missing"})
                continue

            if dry_run:
                dry_run_uris.append(uri)
                continue

            try:
                resolved.path.unlink()
            except OSError as error:
                failed.append(uri)
                errors.append({"uri": uri, "reason": str(error)})
            else:
                deleted.append(uri)

        report = RuntimeRetentionCleanupReport(
            created_at=created_at,
            dry_run=dry_run,
            strict_missing=strict_missing,
            cleanup_report_artifact_days=self.policy.cleanup_report_artifact_days,
            expired_run_ids=plan.expired_run_ids,
            retained_run_ids=plan.retained_run_ids,
            deleted_artifact_uris=tuple(sorted(deleted)),
            dry_run_artifact_uris=tuple(sorted(dry_run_uris)),
            missing_artifact_uris=tuple(sorted(missing)),
            unsafe_artifact_uris=tuple(sorted(unsafe)),
            failed_artifact_uris=tuple(sorted(failed)),
            retained_artifact_uris=plan.retained_artifact_uris,
            errors=tuple(errors),
        )
        if persist_report and self.report_artifacts is not None:
            report_uri = self._write_report(report)
            report = report.with_report_uri(report_uri)
        return report

    def _write_report(self, report: RuntimeRetentionCleanupReport) -> str:
        return self.report_artifacts.write_json(
            (
                "retention-reports",
                report.created_at,
                "runtime-retention-cleanup-report",
            ),
            report.to_dict(),
        )


def retention_plan_to_json(plan: RuntimeRetentionPlan) -> str:
    return json.dumps(
        {
            "expired_run_ids": list(plan.expired_run_ids),
            "expired_artifact_uris": list(plan.expired_artifact_uris),
            "retained_run_ids": list(plan.retained_run_ids),
            "retained_artifact_uris": list(plan.retained_artifact_uris),
        },
        indent=2,
        sort_keys=True,
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
        for uri_field in ("planned_action_uri", "execution_uri", "result_uri"):
            uri = event.get(uri_field)
            if isinstance(uri, str):
                yield run_id, uri

    for checkpoint in _list_records(records, "runtime_checkpoints"):
        uri = checkpoint.get("state_uri")
        if isinstance(uri, str):
            yield str(checkpoint["run_id"]), uri

    for invocation in _list_records(records, "tool_invocations"):
        run_id = str(invocation["run_id"])
        for uri_field in ("input_uri", "output_uri"):
            uri = invocation.get(uri_field)
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
