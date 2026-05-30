from __future__ import annotations

# ruff: noqa: E402
import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from skill_centric_agent_system.operations.shadow_evaluation import (
    ShadowEvaluationError,
    evaluate_shadow_snapshot,
)


def load_snapshot(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ShadowEvaluationError(f"{path} must contain a JSON object.")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run shadow evaluation for candidate descriptor/policy versions "
            "against a trace snapshot."
        ),
    )
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-failed", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = evaluate_shadow_snapshot(load_snapshot(args.snapshot))
    except (OSError, json.JSONDecodeError, ShadowEvaluationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")

    if args.fail_on_failed and result["status"] != "passed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
