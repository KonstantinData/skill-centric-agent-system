from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from skill_centric_agent_system.runtime.invariant_assertions import (
    assert_fail_closed_on_unknowns,
    assert_immutable_profile_after_seal,
    assert_mandatory_validators_per_change_type,
    assert_no_self_granting,
    assert_scope_monotonicity,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_FIXTURES = REPO_ROOT / "examples" / "profiles"
REPLAY_CASES_PATH = (
    REPO_ROOT / "examples" / "evaluations" / "formal-safety-invariant-replay-cases.json"
)
EXPECTED_INVARIANTS = {
    "fail_closed_on_unknowns",
    "no_self_granting",
    "mandatory_validators_per_change_type",
    "scope_monotonicity",
    "immutable_profile_after_seal",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_profile_fixture(name: str) -> dict[str, Any]:
    return load_json(PROFILE_FIXTURES / name)


def apply_mutations(payload: dict[str, Any], mutations: list[dict[str, Any]]) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    for mutation in mutations:
        assert mutation["op"] == "set"
        path = mutation["path"].split(".")
        cursor: dict[str, Any] = mutated
        for key in path[:-1]:
            child = cursor.get(key)
            if not isinstance(child, dict):
                child = {}
                cursor[key] = child
            cursor = child
        cursor[path[-1]] = mutation["value"]
    return mutated


def evaluate_case(case: dict[str, Any]) -> bool:
    invariant_id = case["invariant_id"]
    if case["mode"] == "single-profile":
        profile = apply_mutations(
            load_profile_fixture(case["profile_fixture"]),
            case["mutations"],
        )
        if invariant_id == "fail_closed_on_unknowns":
            findings = assert_fail_closed_on_unknowns(profile)
        elif invariant_id == "no_self_granting":
            findings = assert_no_self_granting(profile)
        elif invariant_id == "mandatory_validators_per_change_type":
            findings = assert_mandatory_validators_per_change_type(profile)
        elif invariant_id == "immutable_profile_after_seal":
            findings = assert_immutable_profile_after_seal(profile)
        else:
            raise AssertionError(f"Unsupported invariant for single-profile mode: {invariant_id}")
    elif case["mode"] == "profile-pair":
        parent = apply_mutations(
            load_profile_fixture(case["parent_profile_fixture"]),
            case["parent_mutations"],
        )
        current = apply_mutations(
            load_profile_fixture(case["current_profile_fixture"]),
            case["current_mutations"],
        )
        findings = assert_scope_monotonicity(parent, current)
    else:
        raise AssertionError(f"Unsupported case mode: {case['mode']}")

    return bool(findings)


def test_replay_fixture_corpus_covers_all_invariants_and_case_types() -> None:
    cases = load_json(REPLAY_CASES_PATH)
    seen_invariants: set[str] = set()
    case_type_map: dict[str, set[str]] = {}

    for case in cases:
        invariant_id = case["invariant_id"]
        seen_invariants.add(invariant_id)
        case_type_map.setdefault(invariant_id, set()).add(case["case_type"])

    assert seen_invariants == EXPECTED_INVARIANTS
    for invariant_id in EXPECTED_INVARIANTS:
        assert case_type_map[invariant_id] == {"positive", "near-miss", "violation"}


def test_replay_fixture_corpus_matches_expected_violation_outcomes() -> None:
    cases = load_json(REPLAY_CASES_PATH)

    for case in cases:
        actual_violation = evaluate_case(case)
        assert actual_violation is case["expected_violation"], case["name"]
