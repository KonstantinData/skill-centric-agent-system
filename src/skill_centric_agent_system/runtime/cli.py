from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from skill_centric_agent_system.composition import ControlPlaneClient
from skill_centric_agent_system.runtime import (
    JsonArtifactStore,
    MinimalRuntimeLoop,
    RuntimeArtifactUriResolver,
    RuntimeEntryPoint,
    RuntimeEntryPointError,
    RuntimeQueueConfig,
    RuntimeQueueManager,
    RuntimeQueueWorker,
    RuntimeRetentionExecutor,
    RuntimeRetentionPlanner,
    RuntimeRetentionPolicy,
    open_runtime_store_session,
    retention_plan_to_json,
)


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    if raw_argv[:1] == ["retention"]:
        return _retention_main(raw_argv[1:])
    if raw_argv[:1] == ["queue"]:
        return _queue_main(raw_argv[1:])

    parser = argparse.ArgumentParser(description="Start a SCAS runtime run.")
    parser.add_argument("--task-file", required=True, help="Path to task intake JSON.")
    parser.add_argument(
        "--composition-context-file",
        help="Path to a composition context response JSON fixture.",
    )
    parser.add_argument(
        "--control-plane-url",
        help="Control Plane base URL. Used when no composition context fixture is supplied.",
    )
    parser.add_argument(
        "--control-plane-token",
        default=os.getenv("SCAS_CONTROL_API_TOKEN"),
        help=(
            "Bearer token for Control Plane requests. "
            "Defaults to SCAS_CONTROL_API_TOKEN."
        ),
    )
    parser.add_argument(
        "--artifact-root",
        default=".scas-runtime",
        help="Artifact root for runtime traces and tool outputs.",
    )
    parser.add_argument(
        "--repository-root",
        default=".",
        help="Repository root used by profile-scoped read tools.",
    )
    parser.add_argument(
        "--run-minimal-loop",
        action="store_true",
        help="Run the first context/planner/executor/validator loop after start.",
    )
    parser.add_argument(
        "--enable-llm-error-judge",
        action="store_true",
        default=_env_bool("SCAS_ENABLE_LLM_ERROR_JUDGE"),
        help=(
            "Enable optional second-stage LLM error classification for low-confidence "
            "rule-based outcomes. Defaults to SCAS_ENABLE_LLM_ERROR_JUDGE."
        ),
    )
    parser.add_argument(
        "--environment",
        default="dev",
        choices=("dev", "staging", "prod"),
        help="Composition environment.",
    )
    parser.add_argument(
        "--storage-mode",
        default="memory",
        choices=("memory", "postgres"),
        help="Runtime storage backend. Use postgres for the Hetzner Runtime Plane.",
    )
    parser.add_argument(
        "--database-url",
        help=(
            "PostgreSQL connection URL for --storage-mode postgres. "
            "Defaults to SCAS_RUNTIME_DATABASE_URL."
        ),
    )
    args = parser.parse_args(raw_argv)

    task = _load_json(Path(args.task_file))
    context_response = (
        _load_json(Path(args.composition_context_file))
        if args.composition_context_file
        else None
    )
    control_plane_client = (
        ControlPlaneClient(args.control_plane_url, api_token=args.control_plane_token)
        if args.control_plane_url
        else None
    )
    artifacts = JsonArtifactStore(args.artifact_root)
    with open_runtime_store_session(
        mode=args.storage_mode,
        database_url=args.database_url,
    ) as storage:
        runtime = RuntimeEntryPoint(
            store=storage.store,
            artifacts=artifacts,
            control_plane_client=control_plane_client,
            environment=args.environment,
        )
        result = runtime.start(task, composition_context_response=context_response)
        loop_result = None
        if args.run_minimal_loop:
            loop_result = MinimalRuntimeLoop(
                store=storage.store,
                artifacts=artifacts,
                repository_root=args.repository_root,
                control_plane_client=control_plane_client,
                enable_llm_error_judge=args.enable_llm_error_judge,
            ).run(result)

        run_record = storage.store.get_runtime_run(result.run_id)
        if run_record is None:
            raise RuntimeEntryPointError(f"Runtime run was not persisted: {result.run_id}.")

        print(
            json.dumps(
                {
                    "run_id": result.run_id,
                    "task_id": result.analyzed_task.task_id,
                    "profile_id": result.profile["id"],
                    "profile_version": result.profile["profile_version"],
                    "status": run_record["status"],
                    "stop_reason": run_record["stop_reason"],
                    "artifact_root_uri": run_record["artifact_root_uri"],
                    "storage_mode": args.storage_mode,
                    "runtime_response": loop_result.response if loop_result else None,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


def _queue_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Operate the SCAS runtime queue.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    enqueue_parser = subparsers.add_parser("enqueue", help="Enqueue a runtime task.")
    _add_queue_storage_args(enqueue_parser)
    enqueue_parser.add_argument("--task-file", required=True, help="Path to task intake JSON.")
    enqueue_parser.add_argument(
        "--composition-context-file",
        help="Path to a composition context response JSON fixture.",
    )
    enqueue_parser.add_argument("--priority", type=int, default=0)
    enqueue_parser.add_argument("--scheduled-at")
    enqueue_parser.add_argument("--max-attempts", type=int, default=3)
    enqueue_parser.add_argument("--idempotency-key")

    worker_parser = subparsers.add_parser("worker-once", help="Claim and process one item.")
    _add_queue_worker_args(worker_parser)

    loop_parser = subparsers.add_parser("worker-loop", help="Run a long-lived queue worker.")
    _add_queue_worker_args(loop_parser)
    loop_parser.add_argument("--poll-interval-seconds", type=float, default=1.0)

    cancel_parser = subparsers.add_parser("cancel", help="Cancel a queued or running item.")
    _add_queue_storage_args(cancel_parser)
    cancel_parser.add_argument("--queue-id", required=True)

    retry_parser = subparsers.add_parser("retry", help="Retry a terminal queue item.")
    _add_queue_storage_args(retry_parser)
    retry_parser.add_argument("--queue-id", required=True)
    retry_parser.add_argument("--scheduled-at")
    retry_parser.add_argument("--idempotency-key")
    retry_parser.add_argument("--max-attempts", type=int)

    args = parser.parse_args(argv)

    artifacts = JsonArtifactStore(args.artifact_root)
    with open_runtime_store_session(
        mode=args.storage_mode,
        database_url=args.database_url,
    ) as storage:
        manager = RuntimeQueueManager(store=storage.store, artifacts=artifacts)

        if args.command == "enqueue":
            context_response = (
                _load_json(Path(args.composition_context_file))
                if args.composition_context_file
                else None
            )
            queue_item = manager.enqueue(
                _load_json(Path(args.task_file)),
                composition_context_response=context_response,
                priority=args.priority,
                scheduled_at=args.scheduled_at,
                max_attempts=args.max_attempts,
                idempotency_key=args.idempotency_key,
            )
            print(json.dumps({"queue_item": queue_item}, indent=2, sort_keys=True))
            return 0

        if args.command in {"worker-once", "worker-loop"}:
            control_plane_client = (
                ControlPlaneClient(args.control_plane_url, api_token=args.control_plane_token)
                if args.control_plane_url
                else None
            )
            worker = RuntimeQueueWorker(
                worker_id=args.worker_id,
                store=storage.store,
                artifacts=artifacts,
                repository_root=args.repository_root,
                control_plane_client=control_plane_client,
                config=RuntimeQueueConfig(
                    lease_seconds=args.lease_seconds,
                    max_attempts=args.max_attempts,
                    retry_delay_seconds=args.retry_delay_seconds,
                    global_running_limit=args.global_running_limit,
                    tenant_running_limits=_parse_tenant_running_limits(
                        args.tenant_running_limit
                    ),
                    tenant_token_limits_per_minute=_parse_tenant_running_limits(
                        args.tenant_token_limit_per_minute
                    ),
                    tenant_tool_call_limits_per_minute=_parse_tenant_running_limits(
                        args.tenant_tool_call_limit_per_minute
                    ),
                    allowed_tenant_ids=tuple(args.allowed_tenant_id),
                    disabled_tenant_ids=tuple(args.disabled_tenant_id),
                    queue_name=args.queue_name,
                ),
            )
            if args.command == "worker-loop":
                worker.run_forever(poll_interval_seconds=args.poll_interval_seconds)
                return 0
            result = worker.process_one()
            print(
                json.dumps(
                    {"processed": result.__dict__ if result is not None else None},
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "cancel":
            queue_item = manager.mark_cancelled(args.queue_id)
            print(json.dumps({"queue_item": queue_item}, indent=2, sort_keys=True))
            return 0

        if args.command == "retry":
            queue_item = manager.retry(
                args.queue_id,
                scheduled_at=args.scheduled_at,
                idempotency_key=args.idempotency_key,
                max_attempts=args.max_attempts,
            )
            print(json.dumps({"queue_item": queue_item}, indent=2, sort_keys=True))
            return 0

    raise RuntimeEntryPointError(f"Unsupported queue command: {args.command}.")


def _retention_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Plan or apply SCAS runtime retention.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Plan retention cleanup.")
    _add_retention_common_args(plan_parser)

    apply_parser = subparsers.add_parser("apply", help="Apply retention cleanup.")
    _add_retention_common_args(apply_parser)
    apply_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Delete expired artifacts. Without this flag apply runs as a dry-run.",
    )
    apply_parser.add_argument(
        "--strict-missing",
        action="store_true",
        help="Treat missing expired artifacts as cleanup errors instead of warnings.",
    )
    apply_parser.add_argument(
        "--no-report",
        action="store_true",
        help="Do not persist a cleanup report artifact.",
    )

    args = parser.parse_args(argv)
    policy = RuntimeRetentionPolicy(
        succeeded_run_artifact_days=args.succeeded_run_artifact_days,
        failed_run_artifact_days=args.failed_run_artifact_days,
        cancelled_run_artifact_days=args.cancelled_run_artifact_days,
        cleanup_report_artifact_days=args.cleanup_report_artifact_days,
    )
    recordset = _load_runtime_recordset(args)
    plan = RuntimeRetentionPlanner(policy).plan(recordset)

    if args.command == "plan":
        print(retention_plan_to_json(plan))
        return 0

    artifacts = JsonArtifactStore(args.artifact_root)
    executor = RuntimeRetentionExecutor(
        RuntimeArtifactUriResolver(args.artifact_root),
        policy=policy,
        report_artifacts=artifacts,
    )
    report = executor.apply(
        plan,
        dry_run=not args.confirm,
        strict_missing=args.strict_missing,
        persist_report=not args.no_report,
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 1 if report.has_errors else 0


def _add_retention_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--recordset-file",
        help="Runtime plane recordset JSON fixture. If omitted, storage is read directly.",
    )
    parser.add_argument(
        "--artifact-root",
        default=".scas-runtime",
        help="Runtime artifact root used to resolve hetzner://runtime URIs.",
    )
    parser.add_argument(
        "--environment",
        default="dev",
        choices=("dev", "staging", "prod"),
        help="Runtime environment label for recordset reads.",
    )
    parser.add_argument(
        "--storage-mode",
        default="memory",
        choices=("memory", "postgres"),
        help="Runtime storage backend. Use postgres for the Hetzner Runtime Plane.",
    )
    parser.add_argument(
        "--database-url",
        help=(
            "PostgreSQL connection URL for --storage-mode postgres. "
            "Defaults to SCAS_RUNTIME_DATABASE_URL."
        ),
    )
    parser.add_argument("--succeeded-run-artifact-days", type=int, default=30)
    parser.add_argument("--failed-run-artifact-days", type=int, default=90)
    parser.add_argument("--cancelled-run-artifact-days", type=int, default=30)
    parser.add_argument("--cleanup-report-artifact-days", type=int, default=180)


def _add_queue_storage_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--artifact-root",
        default=".scas-runtime",
        help="Artifact root for queued payloads and runtime traces.",
    )
    parser.add_argument(
        "--storage-mode",
        default="memory",
        choices=("memory", "postgres"),
        help="Runtime storage backend. Use postgres for the Hetzner Runtime Plane.",
    )
    parser.add_argument(
        "--database-url",
        help=(
            "PostgreSQL connection URL for --storage-mode postgres. "
            "Defaults to SCAS_RUNTIME_DATABASE_URL."
        ),
    )


def _add_queue_worker_args(parser: argparse.ArgumentParser) -> None:
    _add_queue_storage_args(parser)
    parser.add_argument(
        "--repository-root",
        default=".",
        help="Repository root used by profile-scoped read tools.",
    )
    parser.add_argument(
        "--control-plane-url",
        help="Control Plane base URL. Used when queued items have no composition fixture.",
    )
    parser.add_argument(
        "--control-plane-token",
        default=os.getenv("SCAS_CONTROL_API_TOKEN"),
        help="Bearer token for Control Plane requests. Defaults to SCAS_CONTROL_API_TOKEN.",
    )
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--lease-seconds", type=int, default=300)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--retry-delay-seconds", type=int, default=30)
    parser.add_argument("--global-running-limit", type=int)
    parser.add_argument(
        "--tenant-running-limit",
        action="append",
        default=[],
        metavar="TENANT_ID=LIMIT",
        help="Per-tenant concurrent claiming/running limit. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--tenant-token-limit-per-minute",
        action="append",
        default=[],
        metavar="TENANT_ID=LIMIT",
    )
    parser.add_argument(
        "--tenant-tool-call-limit-per-minute",
        action="append",
        default=[],
        metavar="TENANT_ID=LIMIT",
    )
    parser.add_argument("--allowed-tenant-id", action="append", default=[])
    parser.add_argument("--disabled-tenant-id", action="append", default=[])
    parser.add_argument("--queue-name", default="default")


def _load_runtime_recordset(args: argparse.Namespace) -> Mapping[str, Any]:
    if args.recordset_file:
        return _load_json(Path(args.recordset_file))

    with open_runtime_store_session(
        mode=args.storage_mode,
        database_url=args.database_url,
    ) as storage:
        return storage.store.as_runtime_plane_recordset(environment=args.environment)


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return parsed


def _env_bool(name: str) -> bool:
    value = os.getenv(name, "").strip().casefold()
    return value in {"1", "true", "yes", "on"}


def _parse_tenant_running_limits(raw_limits: list[str]) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for raw_limit in raw_limits:
        tenant_id, separator, limit = raw_limit.partition("=")
        if not separator or not tenant_id or not limit:
            raise ValueError(
                "--tenant-running-limit must use TENANT_ID=LIMIT syntax."
            )
        parsed[tenant_id] = int(limit)
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
