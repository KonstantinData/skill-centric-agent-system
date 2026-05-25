from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def build_report(snapshot: dict[str, Any]) -> dict[str, Any]:
    rows = snapshot.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("snapshot.rows must be a list.")

    class_counts: Counter[str] = Counter()
    by_task_type: dict[str, Counter[str]] = defaultdict(Counter)
    by_module_version: dict[str, Counter[str]] = defaultdict(Counter)
    by_environment: dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
        if not isinstance(row, dict):
            continue
        error_class = str(row.get("error_class", "NONE"))
        class_counts[error_class] += 1
        by_task_type[str(row.get("task_type", "unknown"))][error_class] += 1
        by_module_version[str(row.get("module_version", "unknown"))][error_class] += 1
        by_environment[str(row.get("environment", "unknown"))][error_class] += 1

    return {
        "total_rows": sum(class_counts.values()),
        "class_counts": dict(class_counts),
        "by_task_type": {key: dict(value) for key, value in by_task_type.items()},
        "by_module_version": {key: dict(value) for key, value in by_module_version.items()},
        "by_environment": {key: dict(value) for key, value in by_environment.items()},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build error classification trend report.")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(load_json(args.snapshot))
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
