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
    RuntimeEntryPointError,
    open_runtime_store_session,
)


def main(argv: list[str] | None = None) -> int:
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
    args = parser.parse_args(argv)

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


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
