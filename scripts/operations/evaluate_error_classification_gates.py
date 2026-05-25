from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def evaluate(policy: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    thresholds = policy.get("thresholds", {})
    metrics = snapshot.get("metrics", {})
    required = ("r8_rate_max", "f2_unresolved_max", "f1_efficiency_budget_max")
    for key in required:
        if key not in thresholds:
            raise ValueError(f"Missing policy threshold: {key}")
        if key not in metrics:
            raise ValueError(f"Missing snapshot metric: {key}")

    checks = {
        "r8_rate_max": float(metrics["r8_rate_max"]) <= float(thresholds["r8_rate_max"]),
        "f2_unresolved_max": float(metrics["f2_unresolved_max"])
        <= float(thresholds["f2_unresolved_max"]),
        "f1_efficiency_budget_max": float(metrics["f1_efficiency_budget_max"])
        <= float(thresholds["f1_efficiency_budget_max"]),
    }
    status = "passed" if all(checks.values()) else "failed"
    return {
        "status": status,
        "checks": checks,
        "thresholds": thresholds,
        "metrics": metrics,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate error-taxonomy CI gates.")
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-failed", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = evaluate(load_json(args.policy), load_json(args.snapshot))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")

    if args.fail_on_failed and result["status"] != "passed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
