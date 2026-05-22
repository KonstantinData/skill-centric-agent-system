from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from skill_centric_agent_system.composition import ControlPlaneClient
from skill_centric_agent_system.runtime import (
    JsonArtifactStore,
    MinimalRuntimeLoop,
    RuntimeEntryPoint,
    open_runtime_store_session,
)

DEFAULT_CONTROL_API_URL = "https://scas-control-api-dev.still-butterfly-bbff.workers.dev"


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
    args = parser.parse_args(argv)

    if not args.database_url:
        raise SystemExit("SCAS_RUNTIME_DATABASE_URL or --database-url is required.")
    if not args.control_plane_token:
        raise SystemExit("SCAS_CONTROL_API_TOKEN or --control-plane-token is required.")

    task = _load_json(Path(args.task_file))
    control_plane_client = ControlPlaneClient(
        args.control_plane_url,
        api_token=args.control_plane_token,
    )
    artifacts = JsonArtifactStore(args.artifact_root)

    with open_runtime_store_session(
        mode="postgres",
        database_url=args.database_url,
    ) as storage:
        runtime = RuntimeEntryPoint(
            store=storage.store,
            artifacts=artifacts,
            control_plane_client=control_plane_client,
            environment="dev",
        )
        start_result = runtime.start(task)
        loop_result = MinimalRuntimeLoop(
            store=storage.store,
            artifacts=artifacts,
            repository_root=args.repository_root,
            control_plane_client=control_plane_client,
        ).run(start_result)
        run_record = storage.store.get_runtime_run(start_result.run_id)
        events = storage.store.events_for_run(start_result.run_id)
        checkpoints = storage.store.checkpoints_for_run(start_result.run_id)

    print(
        json.dumps(
            {
                "status": "passed" if loop_result.status == "succeeded" else "failed",
                "run_id": start_result.run_id,
                "profile_id": start_result.profile["id"],
                "profile_version": start_result.profile["profile_version"],
                "run_status": run_record["status"] if run_record else None,
                "stop_reason": run_record["stop_reason"] if run_record else None,
                "composition_status": start_result.composition_context_response.get(
                    "composition_status"
                ),
                "event_count": len(events),
                "checkpoint_count": len(checkpoints),
                "artifact_root_uri": run_record["artifact_root_uri"] if run_record else None,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
