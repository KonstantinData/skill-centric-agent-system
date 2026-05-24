from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from skill_centric_agent_system.operations import (
    TelemetryEvaluationError,
    evaluate_telemetry_snapshot,
)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TelemetryEvaluationError(f"{path} must contain a JSON object.")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate production telemetry alerts.")
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--fail-on-alert",
        action="store_true",
        help="Exit non-zero when the evaluated status is warning or critical.",
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit non-zero only when the evaluated status is critical.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = evaluate_telemetry_snapshot(
            load_json(args.policy),
            load_json(args.snapshot),
        )
    except (OSError, json.JSONDecodeError, TelemetryEvaluationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")

    if args.fail_on_alert and result["status"] != "passed":
        return 1
    if args.fail_on_critical and result["status"] == "critical":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
