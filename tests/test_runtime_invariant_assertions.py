from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skill_centric_agent_system.runtime.invariant_assertions import (
    assert_profile_sealing_invariants,
    assert_scope_monotonicity,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_FIXTURES = REPO_ROOT / "examples" / "profiles"


def load_profile(name: str) -> dict[str, Any]:
    return json.loads((PROFILE_FIXTURES / name).read_text(encoding="utf-8"))


def test_profile_invariant_assertions_pass_for_current_profile_fixtures() -> None:
    for profile_name in (
        "code-review-profile.json",
        "human-review-required-profile.json",
    ):
        findings = assert_profile_sealing_invariants(load_profile(profile_name))
        assert findings == [], profile_name


def test_fail_closed_on_unknowns_detects_unselected_module_version_pin() -> None:
    profile = load_profile("code-review-profile.json")
    profile["module_versions"]["unexpected-capability"] = "0.1.0"

    findings = assert_profile_sealing_invariants(profile)

    assert any(
        finding.invariant_id == "fail_closed_on_unknowns"
        and "unexpected module version pins" in finding.message
        for finding in findings
    )


def test_no_self_granting_detects_unselected_runtime_skill() -> None:
    profile = load_profile("code-review-profile.json")
    profile["skill_execution_roles"]["runtime_skills"].append("task-execution-planning")

    findings = assert_profile_sealing_invariants(profile)

    assert any(
        finding.invariant_id == "no_self_granting"
        and "unselected skills" in finding.message
        for finding in findings
    )


def test_scope_monotonicity_detects_scope_widening() -> None:
    parent = load_profile("code-review-profile.json")
    current = load_profile("code-review-profile.json")
    current["tools"].append("filesystem-list")

    findings = assert_scope_monotonicity(parent, current)

    assert any(
        finding.invariant_id == "scope_monotonicity"
        and "tools widened" in finding.message
        for finding in findings
    )
