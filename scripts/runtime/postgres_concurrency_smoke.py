from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from skill_centric_agent_system.runtime import (
    FlightRecorder,
    JsonArtifactStore,
    open_runtime_store_session,
)

DEFAULT_PROFILE_PATH = "examples/profiles/code-review-profile.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-test concurrent Flight Recorder event writes against PostgreSQL.",
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
        "--profile-file",
        default=DEFAULT_PROFILE_PATH,
        help="Runtime profile JSON used to create the smoke-test run.",
    )
    parser.add_argument(
        "--events",
        type=int,
        default=20,
        help="Number of concurrent events to write.",
    )
    parser.add_argument(
        "--run-id",
        help="Optional run ID. Defaults to a timestamped smoke-test run ID.",
    )
    args = parser.parse_args(argv)

    if not args.database_url:
        raise SystemExit("SCAS_RUNTIME_DATABASE_URL or --database-url is required.")
    if args.events < 2:
        raise SystemExit("--events must be at least 2.")

    profile = _load_json(Path(args.profile_file))
    artifacts = JsonArtifactStore(args.artifact_root)
    run_id = args.run_id or (
        "run-postgres-concurrency-smoke-" + datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    )
    task_id = "task-postgres-concurrency-smoke"

    with open_runtime_store_session(
        mode="postgres",
        database_url=args.database_url,
    ) as storage:
        FlightRecorder(storage.store, artifacts).start_run(
            task_id=task_id,
            profile=profile,
            run_id=run_id,
        )

    def write_event(index: int) -> int:
        with open_runtime_store_session(
            mode="postgres",
            database_url=args.database_url,
        ) as storage:
            event = FlightRecorder(storage.store, artifacts).record_event(
                run_id=run_id,
                event_type="runtime_started",
                actor_role="composer",
                result={"smoke_event": index},
                idempotency_key=f"{run_id}:event:{index}",
            )
            return int(event["event_index"])

    with ThreadPoolExecutor(max_workers=min(args.events, 8)) as executor:
        returned_indices = list(executor.map(write_event, range(args.events)))

    with open_runtime_store_session(
        mode="postgres",
        database_url=args.database_url,
    ) as storage:
        events = storage.store.events_for_run(run_id)

    persisted_indices = sorted(int(event["event_index"]) for event in events)
    expected_indices = list(range(args.events))
    status = "passed" if persisted_indices == expected_indices else "failed"

    print(
        json.dumps(
            {
                "status": status,
                "run_id": run_id,
                "event_count": len(events),
                "returned_event_indices": sorted(returned_indices),
                "persisted_event_indices": persisted_indices,
                "expected_event_indices": expected_indices,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if status == "passed" else 1


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
