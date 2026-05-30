from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ruff: noqa: E402
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from skill_centric_agent_system.runtime.invariant_replay import evaluate_case, load_replay_cases

DEFAULT_INCIDENTS_PATH = (
    REPO_ROOT / "examples" / "evaluations" / "incident-locked-regression-cases.json"
)
DEFAULT_MATRIX_POLICY_PATH = (
    REPO_ROOT / "policies" / "runtime" / "formal-safety-change-type-matrix.json"
)
DEFAULT_PROFILES_DIR = REPO_ROOT / "examples" / "profiles"


def load_matrix_policy(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def build_change_type_invariant_map(matrix_policy: dict[str, Any]) -> dict[str, set[str]]:
    change_types = matrix_policy.get("change_types")
    if not isinstance(change_types, list):
        raise ValueError("formal safety change-type matrix must contain change_types array.")

    mapping: dict[str, set[str]] = {}
    for entry in change_types:
        if not isinstance(entry, dict):
            continue
        change_type_id = str(entry.get("id") or "")
        invariants = entry.get("mandatory_invariants")
        if not change_type_id or not isinstance(invariants, list):
            continue
        mapping[change_type_id] = {
            invariant for invariant in invariants if isinstance(invariant, str)
        }
    return mapping


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run incident-locked never-again regressions and validate each case "
            "against change-type invariant expectations."
        ),
    )
    parser.add_argument("--incidents", type=Path, default=DEFAULT_INCIDENTS_PATH)
    parser.add_argument("--profiles-dir", type=Path, default=DEFAULT_PROFILES_DIR)
    parser.add_argument("--matrix-policy", type=Path, default=DEFAULT_MATRIX_POLICY_PATH)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--print-json", action="store_true")
    parser.add_argument("--fail-on-failed", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        incidents = load_replay_cases(args.incidents)
        matrix_policy = load_matrix_policy(args.matrix_policy)
        change_type_map = build_change_type_invariant_map(matrix_policy)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    binding_failures: list[str] = []
    results: list[dict[str, Any]] = []

    for incident in incidents:
        incident_id = str(incident.get("incident_id") or incident.get("name") or "unknown-incident")
        change_type = str(incident.get("change_type") or "")
        invariant_id = str(incident.get("invariant_id") or "")

        allowed_invariants = change_type_map.get(change_type)
        if not change_type:
            binding_failures.append(f"{incident_id}: missing change_type.")
        elif allowed_invariants is None:
            binding_failures.append(f"{incident_id}: unknown change_type {change_type!r}.")
        elif invariant_id not in allowed_invariants:
            binding_failures.append(
                f"{incident_id}: invariant {invariant_id!r} is not mandatory for "
                f"change_type {change_type!r}."
            )

        replay_case = dict(incident)
        replay_case.setdefault("name", incident_id)
        replay_result = evaluate_case(replay_case, profiles_dir=args.profiles_dir)
        results.append(
            {
                "incident_id": incident_id,
                "change_type": change_type,
                "invariant_id": replay_result.invariant_id,
                "expected_violation": replay_result.expected_violation,
                "actual_violation": replay_result.actual_violation,
                "passed": replay_result.passed,
            }
        )

    replay_mismatches = [result for result in results if not result["passed"]]
    status = "passed"
    if binding_failures or replay_mismatches:
        status = "failed"

    summary = {
        "status": status,
        "incident_count": len(results),
        "binding_failure_count": len(binding_failures),
        "replay_mismatch_count": len(replay_mismatches),
        "binding_failures": binding_failures,
        "results": results,
    }

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            f"{json.dumps(summary, indent=2)}\n",
            encoding="utf-8",
        )

    if args.print_json:
        print(json.dumps(summary, indent=2))
    else:
        print(
            "Incident-locked regressions: "
            f"{summary['status']} ({summary['incident_count']} incidents, "
            f"{summary['binding_failure_count']} binding failures, "
            f"{summary['replay_mismatch_count']} mismatches)"
        )
        if binding_failures:
            for failure in binding_failures:
                print(f"- binding: {failure}")
        if replay_mismatches:
            for mismatch in replay_mismatches:
                print(
                    "- mismatch: "
                    f"{mismatch['incident_id']} expected_violation="
                    f"{mismatch['expected_violation']} actual_violation="
                    f"{mismatch['actual_violation']}"
                )

    if args.fail_on_failed and status != "passed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
