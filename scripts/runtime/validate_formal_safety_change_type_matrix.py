"""Validate the formal safety change-type matrix policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_POLICY_PATH = Path("policies/runtime/formal-safety-change-type-matrix.json")
REQUIRED_CHANGE_TYPES = {
    "contract-change",
    "runtime-logic",
    "governance-doc",
    "security-gate",
    "scope-or-policy-change",
}
REQUIRED_INVARIANTS = {
    "fail_closed_on_unknowns",
    "no_self_granting",
    "mandatory_validators_per_change_type",
    "scope_monotonicity",
    "immutable_profile_after_seal",
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def validate_matrix(path: Path) -> list[str]:
    matrix = load_json(path)
    failures: list[str] = []

    if matrix.get("matrix_id") != "fsg-02-invariant-change-type-matrix":
        failures.append("matrix_id must be fsg-02-invariant-change-type-matrix")
    if matrix.get("invariant_source") != "docs/policies/formal-safety-invariants.md":
        failures.append("invariant_source must reference docs/policies/formal-safety-invariants.md")

    change_types = matrix.get("change_types")
    if not isinstance(change_types, list):
        failures.append("change_types must be an array")
        return failures

    seen_ids: set[str] = set()
    invariant_coverage: set[str] = set()
    for item in change_types:
        if not isinstance(item, dict):
            failures.append("each change type entry must be an object")
            continue

        entry_id = str(item.get("id", ""))
        if not entry_id:
            failures.append("change type entry must include id")
            continue
        if entry_id in seen_ids:
            failures.append(f"duplicate change type id: {entry_id}")
        seen_ids.add(entry_id)

        invariants = item.get("mandatory_invariants")
        if not isinstance(invariants, list) or not invariants:
            failures.append(f"{entry_id}: mandatory_invariants must be a non-empty array")
        else:
            for invariant in invariants:
                if isinstance(invariant, str):
                    invariant_coverage.add(invariant)

        for field in (
            "mandatory_runtime_validators",
            "mandatory_repo_validators",
            "required_ci_checks",
        ):
            value = item.get(field)
            if not isinstance(value, list) or not value:
                failures.append(f"{entry_id}: {field} must be a non-empty array")

        if item.get("enforcement_mode") != "blocking":
            failures.append(f"{entry_id}: enforcement_mode must be blocking")

    missing_types = sorted(REQUIRED_CHANGE_TYPES - seen_ids)
    if missing_types:
        failures.append("missing change types: " + ", ".join(missing_types))

    missing_invariants = sorted(REQUIRED_INVARIANTS - invariant_coverage)
    if missing_invariants:
        failures.append("missing invariant coverage: " + ", ".join(missing_invariants))

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    args = parser.parse_args()

    failures = validate_matrix(args.policy)
    if failures:
        print("Formal safety change-type matrix validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Formal safety change-type matrix validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
