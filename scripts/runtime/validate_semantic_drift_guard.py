"""Validate semantic drift guard contrastive-pair policy."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

DEFAULT_POLICY_PATH = Path("policies/runtime/semantic-drift-guard.json")
REQUIRED_INFLUENCE_CLASSES = {
    "retrieval_only",
    "planner_hint",
    "analyzer_prior",
    "composer_candidate_bias",
    "golden_workflow_proposal",
    "policy_change_proposal",
    "scoped_exception_proposal",
}
AUTHORITY_DELTAS = {
    "tool_addition",
    "scope_expansion",
    "budget_increase",
    "validator_removal",
    "failure_mode_relaxation",
    "policy_exception",
    "data_access_expansion",
    "memory_scope_expansion",
    "knowledge_scope_expansion",
}
BLOCKING_GATES = {"freeze_prior", "needs_human_review", "needs_more_evidence", "reject"}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def validate_guard(path: Path) -> list[str]:
    guard = load_json(path)
    failures: list[str] = []

    if guard.get("guard_id") != "semantic-drift-guard":
        failures.append("guard_id must be semantic-drift-guard")
    if guard.get("authority_invariant") != "learned_context_not_authority":
        failures.append("authority_invariant must be learned_context_not_authority")
    if guard.get("default_on_match") not in BLOCKING_GATES:
        failures.append("default_on_match must be a blocking gate")

    classes = guard.get("influence_classes")
    if not isinstance(classes, list):
        failures.append("influence_classes must be an array")
    else:
        seen_classes: set[str] = set()
        for item in classes:
            if not isinstance(item, dict):
                failures.append("each influence class entry must be an object")
                continue
            class_id = str(item.get("id", ""))
            seen_classes.add(class_id)
            if item.get("automatic_authority_delta_allowed") is not False:
                failures.append(f"{class_id}: automatic authority delta must be false")
        missing_classes = sorted(REQUIRED_INFLUENCE_CLASSES - seen_classes)
        if missing_classes:
            failures.append("missing influence classes: " + ", ".join(missing_classes))

    pairs = guard.get("contrastive_pairs")
    if not isinstance(pairs, list) or not pairs:
        failures.append("contrastive_pairs must be a non-empty array")
        return failures

    seen_pairs: set[str] = set()
    for pair in pairs:
        if not isinstance(pair, dict):
            failures.append("each contrastive pair must be an object")
            continue
        pair_id = str(pair.get("pair_id", ""))
        if pair_id in seen_pairs:
            failures.append(f"duplicate pair_id: {pair_id}")
        seen_pairs.add(pair_id)

        forbidden = pair.get("forbidden_generalization")
        if not isinstance(forbidden, dict):
            failures.append(f"{pair_id}: forbidden_generalization must be an object")
            continue
        deltas = forbidden.get("authority_delta")
        if not isinstance(deltas, list) or not deltas:
            failures.append(f"{pair_id}: authority_delta must be a non-empty array")
        elif any(delta not in AUTHORITY_DELTAS for delta in deltas):
            failures.append(f"{pair_id}: authority_delta contains an unknown value")
        if pair.get("expected_gate") not in BLOCKING_GATES:
            failures.append(f"{pair_id}: expected_gate must block automatic promotion")

    return failures


def matching_contrastive_pairs(
    guard: Mapping[str, Any],
    analyzer_prior: Mapping[str, Any],
) -> list[dict[str, str]]:
    source_context = _mapping(analyzer_prior.get("source_context"))
    target_context = _mapping(analyzer_prior.get("target_context"))
    authority_delta = {
        str(delta) for delta in analyzer_prior.get("authority_delta", []) if isinstance(delta, str)
    }

    matches: list[dict[str, str]] = []
    pairs = guard.get("contrastive_pairs", [])
    if not isinstance(pairs, list):
        return matches

    for pair in pairs:
        if not isinstance(pair, Mapping):
            continue
        positive_context = _mapping(pair.get("positive_context"))
        forbidden = _mapping(pair.get("forbidden_generalization"))
        forbidden_deltas = {
            str(delta) for delta in forbidden.get("authority_delta", []) if isinstance(delta, str)
        }
        forbidden_context = {
            key: value for key, value in forbidden.items() if key != "authority_delta"
        }
        if (
            _context_contains(source_context, positive_context)
            and _context_contains(target_context, forbidden_context)
            and bool(authority_delta & forbidden_deltas)
        ):
            matches.append(
                {
                    "pair_id": str(pair["pair_id"]),
                    "decision": str(pair["expected_gate"]),
                }
            )
    return matches


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _context_contains(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args(argv)

    failures = validate_guard(args.policy)
    report = {
        "policy": str(args.policy),
        "status": "failed" if failures else "passed",
        "violations": failures,
    }
    if args.print_json:
        print(json.dumps(report, indent=2))
        return 1 if failures else 0
    if failures:
        print("Semantic drift guard validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Semantic drift guard validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
