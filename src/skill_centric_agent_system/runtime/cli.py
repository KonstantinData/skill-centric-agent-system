from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from skill_centric_agent_system.composition import ControlPlaneClient
from skill_centric_agent_system.runtime import (
    InMemoryRuntimeStore,
    JsonArtifactStore,
    RuntimeEntryPoint,
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
        "--artifact-root",
        default=".scas-runtime",
        help="Local artifact root for runtime dry-run artifacts.",
    )
    parser.add_argument(
        "--environment",
        default="dev",
        choices=("dev", "staging", "prod"),
        help="Composition environment.",
    )
    args = parser.parse_args(argv)

    task = _load_json(Path(args.task_file))
    context_response = (
        _load_json(Path(args.composition_context_file))
        if args.composition_context_file
        else None
    )
    control_plane_client = (
        ControlPlaneClient(args.control_plane_url) if args.control_plane_url else None
    )
    store = InMemoryRuntimeStore()
    runtime = RuntimeEntryPoint(
        store=store,
        artifacts=JsonArtifactStore(args.artifact_root),
        control_plane_client=control_plane_client,
        environment=args.environment,
    )
    result = runtime.start(task, composition_context_response=context_response)
    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "task_id": result.analyzed_task.task_id,
                "profile_id": result.profile["id"],
                "profile_version": result.profile["profile_version"],
                "status": store.runtime_runs[result.run_id]["status"],
                "artifact_root_uri": store.runtime_runs[result.run_id][
                    "artifact_root_uri"
                ],
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
