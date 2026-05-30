"""Replay fixture runner for formal safety invariant checks."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skill_centric_agent_system.runtime.invariant_assertions import (
    assert_fail_closed_on_unknowns,
    assert_immutable_profile_after_seal,
    assert_mandatory_validators_per_change_type,
    assert_no_self_granting,
    assert_scope_monotonicity,
)

EXPECTED_INVARIANTS = {
    "fail_closed_on_unknowns",
    "no_self_granting",
    "mandatory_validators_per_change_type",
    "scope_monotonicity",
    "immutable_profile_after_seal",
}


@dataclass(frozen=True)
class ReplayCaseResult:
    name: str
    invariant_id: str
    case_type: str
    expected_violation: bool
    actual_violation: bool

    @property
    def passed(self) -> bool:
        return self.expected_violation is self.actual_violation


def load_replay_cases(path: Path) -> list[dict[str, Any]]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, list):
        raise ValueError(f"{path} must contain a JSON array.")
    return parsed


def validate_replay_corpus_shape(cases: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    seen_invariants: set[str] = set()
    case_type_map: dict[str, set[str]] = {}
    for case in cases:
        invariant_id = str(case.get("invariant_id", ""))
        case_type = str(case.get("case_type", ""))
        if not invariant_id:
            failures.append("case is missing invariant_id")
            continue
        if case_type not in {"positive", "near-miss", "violation"}:
            failures.append(f"{invariant_id}: unsupported case_type '{case_type}'")
        seen_invariants.add(invariant_id)
        case_type_map.setdefault(invariant_id, set()).add(case_type)

    if seen_invariants != EXPECTED_INVARIANTS:
        missing = sorted(EXPECTED_INVARIANTS - seen_invariants)
        extras = sorted(seen_invariants - EXPECTED_INVARIANTS)
        if missing:
            failures.append("missing invariants in replay corpus: " + ", ".join(missing))
        if extras:
            failures.append("unknown invariants in replay corpus: " + ", ".join(extras))

    for invariant_id in EXPECTED_INVARIANTS.intersection(seen_invariants):
        expected_case_types = {"positive", "near-miss", "violation"}
        actual_case_types = case_type_map[invariant_id]
        if actual_case_types != expected_case_types:
            failures.append(
                f"{invariant_id}: expected case types {sorted(expected_case_types)} but got "
                f"{sorted(actual_case_types)}"
            )
    return failures


def run_replay_cases(
    *,
    cases: list[dict[str, Any]],
    profiles_dir: Path,
) -> list[ReplayCaseResult]:
    return [evaluate_case(case, profiles_dir=profiles_dir) for case in cases]


def evaluate_case(case: Mapping[str, Any], *, profiles_dir: Path) -> ReplayCaseResult:
    invariant_id = str(case["invariant_id"])
    case_type = str(case["case_type"])
    expected_violation = bool(case["expected_violation"])
    mode = str(case["mode"])

    if mode == "single-profile":
        profile = apply_mutations(
            load_profile_fixture(profiles_dir, str(case["profile_fixture"])),
            list(case["mutations"]),
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
            raise ValueError(f"Unsupported invariant for single-profile mode: {invariant_id}")
    elif mode == "profile-pair":
        parent = apply_mutations(
            load_profile_fixture(profiles_dir, str(case["parent_profile_fixture"])),
            list(case["parent_mutations"]),
        )
        current = apply_mutations(
            load_profile_fixture(profiles_dir, str(case["current_profile_fixture"])),
            list(case["current_mutations"]),
        )
        findings = assert_scope_monotonicity(parent, current)
    else:
        raise ValueError(f"Unsupported replay case mode: {mode}")

    return ReplayCaseResult(
        name=str(case["name"]),
        invariant_id=invariant_id,
        case_type=case_type,
        expected_violation=expected_violation,
        actual_violation=bool(findings),
    )


def load_profile_fixture(profiles_dir: Path, name: str) -> dict[str, Any]:
    payload = json.loads((profiles_dir / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"profile fixture {name} must contain a JSON object")
    return payload


def apply_mutations(payload: dict[str, Any], mutations: list[dict[str, Any]]) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    for mutation in mutations:
        if mutation.get("op") != "set":
            raise ValueError("only mutation op='set' is supported")
        path = str(mutation["path"]).split(".")
        cursor: dict[str, Any] = mutated
        for key in path[:-1]:
            child = cursor.get(key)
            if not isinstance(child, dict):
                child = {}
                cursor[key] = child
            cursor = child
        cursor[path[-1]] = mutation["value"]
    return mutated
