from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from skill_centric_agent_system.runtime.invariant_replay import (
    load_replay_cases,
    run_replay_cases,
    validate_replay_corpus_shape,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES_PATH = (
    REPO_ROOT / "examples" / "evaluations" / "formal-safety-invariant-replay-cases.json"
)
DEFAULT_PROFILES_DIR = REPO_ROOT / "examples" / "profiles"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run formal safety invariant replay fixtures and fail on mismatches.",
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--profiles-dir", type=Path, default=DEFAULT_PROFILES_DIR)
    parser.add_argument("--print-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cases = load_replay_cases(args.cases)
    shape_failures = validate_replay_corpus_shape(cases)
    if shape_failures:
        print("Invariant replay corpus validation failed:", file=sys.stderr)
        for failure in shape_failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    results = run_replay_cases(cases=cases, profiles_dir=args.profiles_dir)
    mismatches = [result for result in results if not result.passed]

    summary = {
        "cases_path": str(args.cases),
        "profiles_dir": str(args.profiles_dir),
        "total_cases": len(results),
        "mismatch_count": len(mismatches),
        "status": "passed" if not mismatches else "failed",
        "results": [
            {
                "name": result.name,
                "invariant_id": result.invariant_id,
                "case_type": result.case_type,
                "expected_violation": result.expected_violation,
                "actual_violation": result.actual_violation,
                "passed": result.passed,
            }
            for result in results
        ],
    }

    if args.print_json:
        print(json.dumps(summary, indent=2))
    else:
        print(
            "Invariant replay check: "
            f"{summary['status']} ({summary['total_cases']} cases, "
            f"{summary['mismatch_count']} mismatches)"
        )
        if mismatches:
            for mismatch in mismatches:
                print(
                    "- "
                    f"{mismatch.name}: expected_violation={mismatch.expected_violation} "
                    f"actual_violation={mismatch.actual_violation}"
                )

    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
