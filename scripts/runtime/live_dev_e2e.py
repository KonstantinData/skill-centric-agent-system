from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

from skill_centric_agent_system.composition import ControlPlaneClient
from skill_centric_agent_system.runtime import (
    JsonArtifactStore,
    MinimalRuntimeLoop,
    RuntimeEntryPoint,
    open_runtime_store_session,
)

DEFAULT_CONTROL_API_URL = "https://scas-control-api-dev.still-butterfly-bbff.workers.dev"
TARGET_ENVIRONMENTS = ("dev", "staging", "prod")
GENERIC_TASK_SUITE = (
    ("code-review", "examples/tasks/code-review-task.json"),
    ("research", "examples/tasks/research-task.json"),
    ("task-execution", "examples/tasks/task-execution-task.json"),
    ("general-task", "examples/tasks/general-task.json"),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the live dev E2E gate across Cloudflare and Hetzner.",
    )
    parser.add_argument(
        "--task-file",
        default="examples/tasks/code-review-task.json",
        help="Task intake JSON file.",
    )
    parser.add_argument(
        "--task-suite",
        choices=("single", "generic"),
        default="single",
        help=(
            "Run only --task-file or run the generic suite covering code-review, "
            "research, task-execution, and general-task."
        ),
    )
    parser.add_argument(
        "--control-plane-url",
        default=os.getenv("SCAS_CONTROL_API_URL", DEFAULT_CONTROL_API_URL),
        help="Cloudflare Control API base URL.",
    )
    parser.add_argument(
        "--control-plane-token",
        default=os.getenv("SCAS_CONTROL_API_TOKEN"),
        help="Control API bearer token. Defaults to SCAS_CONTROL_API_TOKEN.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("SCAS_RUNTIME_DATABASE_URL"),
        help="Hetzner PostgreSQL URL. Defaults to SCAS_RUNTIME_DATABASE_URL.",
    )
    parser.add_argument(
        "--artifact-root",
        default=os.getenv("SCAS_RUNTIME_ARTIFACT_ROOT", "/opt/scas/runtime"),
        help="Hetzner runtime artifact root.",
    )
    parser.add_argument(
        "--repository-root",
        default=os.getenv("SCAS_REPOSITORY_ROOT", "."),
        help="Repository root used by profile-scoped tools.",
    )
    parser.add_argument(
        "--environment",
        choices=TARGET_ENVIRONMENTS,
        default=os.getenv("TARGET_ENVIRONMENT", "dev"),
        help="Runtime environment label for run metadata and policy routing.",
    )
    args = parser.parse_args(argv)

    if not args.database_url:
        raise SystemExit("SCAS_RUNTIME_DATABASE_URL or --database-url is required.")
    if not args.control_plane_token:
        raise SystemExit("SCAS_CONTROL_API_TOKEN or --control-plane-token is required.")

    task_cases = (
        tuple((label, Path(path)) for label, path in GENERIC_TASK_SUITE)
        if args.task_suite == "generic"
        else (("single", Path(args.task_file)),)
    )
    control_plane_client = ControlPlaneClient(
        args.control_plane_url,
        api_token=args.control_plane_token,
    )
    artifacts = JsonArtifactStore(args.artifact_root)
    run_suffix = os.getenv("GITHUB_RUN_ID") or uuid4().hex[:12]
    configured_artifact_root_uri = (
        "hetzner://runtime/" + Path(args.artifact_root).as_posix().lstrip("/")
    )

    with open_runtime_store_session(
        mode="postgres",
        database_url=args.database_url,
    ) as storage:
        results = []
        for label, task_path in task_cases:
            task = _load_json(task_path)
            runtime = RuntimeEntryPoint(
                store=storage.store,
                artifacts=artifacts,
                control_plane_client=control_plane_client,
                environment=args.environment,
            )
            start_result = runtime.start(task, run_id=f"run-live-{run_suffix}-{label}")
            loop_result = MinimalRuntimeLoop(
                store=storage.store,
                artifacts=artifacts,
                repository_root=args.repository_root,
                control_plane_client=control_plane_client,
            ).run(start_result)
            run_record = storage.store.get_runtime_run(start_result.run_id)
            events = storage.store.events_for_run(start_result.run_id)
            checkpoints = storage.store.checkpoints_for_run(start_result.run_id)
            handler_evidence = handler_binding_evidence_from_checkpoints(
                checkpoints,
                artifact_root=Path(args.artifact_root),
            )
            case_status = (
                "passed"
                if loop_result.status == "succeeded"
                and handler_evidence["handler_binding_status"] == "passed"
                else "failed"
            )
            results.append(
                {
                    "case": label,
                    "environment": args.environment,
                    "status": case_status,
                    "run_id": start_result.run_id,
                    "task_type": start_result.profile["task_type"],
                    "profile_id": start_result.profile["id"],
                    "profile_version": start_result.profile["profile_version"],
                    "handler_binding_status": handler_evidence["handler_binding_status"],
                    "planner_checkpoint_uri": handler_evidence["planner_checkpoint_uri"],
                    "skill_handlers": handler_evidence["skill_handlers"],
                    "run_status": run_record["status"] if run_record else None,
                    "stop_reason": run_record["stop_reason"] if run_record else None,
                    "composition_status": start_result.composition_context_response.get(
                        "composition_status"
                    ),
                    "event_count": len(events),
                    "checkpoint_count": len(checkpoints),
                    "artifact_root_uri": configured_artifact_root_uri,
                    "runtime_record_artifact_root_uri": (
                        run_record["artifact_root_uri"] if run_record else None
                    ),
                    "runtime_output_task_type": loop_result.response["runtime_output"][
                        "task_type"
                    ],
                }
            )

    print(
        json.dumps(
            {
                "environment": args.environment,
                "status": (
                    "passed"
                    if all(result["status"] == "passed" for result in results)
                    else "failed"
                ),
                "handler_binding_status": (
                    "passed"
                    if all(
                        result["handler_binding_status"] == "passed" for result in results
                    )
                    else "failed"
                ),
                "task_suite": args.task_suite,
                "case_count": len(results),
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def handler_binding_evidence_from_checkpoints(
    checkpoints: tuple[Mapping[str, Any], ...],
    *,
    artifact_root: Path,
) -> dict[str, Any]:
    planner_checkpoint = next(
        (checkpoint for checkpoint in checkpoints if checkpoint.get("phase") == "planner"),
        None,
    )
    if planner_checkpoint is None:
        return {
            "handler_binding_status": "failed",
            "planner_checkpoint_uri": "",
            "skill_handlers": [],
        }

    state_uri = str(planner_checkpoint.get("state_uri", ""))
    planner_payload = _load_runtime_artifact(artifact_root, state_uri)
    skill_handlers = planner_payload.get("skill_handlers", [])
    if not isinstance(skill_handlers, list):
        skill_handlers = []

    sanitized_handlers = [
        {
            "handler_id": str(handler.get("handler_id", "")),
            "name": str(handler.get("name", "")),
            "version": str(handler.get("version", "")),
        }
        for handler in skill_handlers
        if isinstance(handler, Mapping)
    ]
    return {
        "handler_binding_status": (
            "passed" if _handler_bindings_are_valid(sanitized_handlers) else "failed"
        ),
        "planner_checkpoint_uri": state_uri,
        "skill_handlers": sanitized_handlers,
    }


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return parsed


def _load_runtime_artifact(artifact_root: Path, uri: str) -> dict[str, Any]:
    relative = uri.removeprefix("hetzner://runtime/").strip("/")
    return _load_json(artifact_root / Path(relative))


def _handler_bindings_are_valid(skill_handlers: list[dict[str, str]]) -> bool:
    if not skill_handlers:
        return False
    return all(
        handler["handler_id"] == f"{handler['name']}@{handler['version']}"
        and handler["name"]
        and handler["version"]
        for handler in skill_handlers
    )


if __name__ == "__main__":
    raise SystemExit(main())
