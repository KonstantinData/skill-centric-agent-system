from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from skill_centric_agent_system.runtime import PostPlanningMemoryInvariantValidator

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = REPO_ROOT / "examples" / "profiles" / "code-review-profile.json"


def load_profile() -> dict[str, object]:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def safe_memory_plan() -> dict[str, object]:
    return {
        "used_memory_ids": ["memory-runtime-decision"],
        "effect": "planner_hint",
        "selection_reason": "Memory suggests reviewing checkpoints during reconstruction.",
        "authority_delta": [],
        "planned_steps": ["inspect checkpoints", "compare validation evidence"],
    }


def test_post_planning_validator_allows_non_authoritative_memory_hint() -> None:
    profile = load_profile()
    result = PostPlanningMemoryInvariantValidator().validate(
        safe_memory_plan(),
        runtime_profile=profile,
        planned_runtime_profile=deepcopy(profile),
    )

    assert result.approved
    assert result.violations == ()


def test_post_planning_validator_ignores_plans_without_memory() -> None:
    result = PostPlanningMemoryInvariantValidator().validate(
        {"planned_steps": ["inspect repository"]},
        runtime_profile=load_profile(),
    )

    assert result.approved
    assert result.reason == "Plan does not use procedural memory."


def test_post_planning_validator_rejects_memory_authority_delta() -> None:
    plan = safe_memory_plan()
    plan["effect"] = "runtime_authority"
    plan["authority_delta"] = ["tool_addition"]

    result = PostPlanningMemoryInvariantValidator().validate(
        plan,
        runtime_profile=load_profile(),
    )

    assert not result.approved
    assert "memory effect must be non-authoritative" in result.violations
    assert "memory-influenced plans must not carry authority_delta" in result.violations


def test_post_planning_validator_rejects_authority_mutation_fields() -> None:
    plan = safe_memory_plan()
    plan.update(
        {
            "tool_grants": ["filesystem-write"],
            "scope_grants": ["repository-write"],
            "policy_overrides": ["ignore-no-destructive-commands"],
            "validator_overrides": ["remove-review-findings-contract"],
            "budget_changes": {"max_tokens": 120000},
            "failure_policy_changes": {"on_policy_denial": "continue"},
        }
    )

    result = PostPlanningMemoryInvariantValidator().validate(
        plan,
        runtime_profile=load_profile(),
    )

    assert not result.approved
    assert "memory-influenced plans must not include tool grants" in result.violations
    assert "memory-influenced plans must not include scope grants" in result.violations
    assert "memory-influenced plans must not include policy overrides" in result.violations
    assert "memory-influenced plans must not include validator overrides" in result.violations
    assert "memory-influenced plans must not include budget changes" in result.violations
    assert (
        "memory-influenced plans must not include failure policy changes"
        in result.violations
    )


def test_post_planning_validator_rejects_runtime_profile_authority_delta() -> None:
    profile = load_profile()
    planned_profile = deepcopy(profile)
    planned_profile["tools"] = [*profile["tools"], "filesystem-write"]  # type: ignore[index]
    planned_profile["failure_policy"] = {
        **profile["failure_policy"],  # type: ignore[arg-type]
        "on_policy_denial": "continue",
    }

    result = PostPlanningMemoryInvariantValidator().validate(
        safe_memory_plan(),
        runtime_profile=profile,
        planned_runtime_profile=planned_profile,
    )

    assert not result.approved
    assert (
        "memory-influenced plans must not mutate runtime_profile tools"
        in result.violations
    )
    assert (
        "memory-influenced plans must not mutate runtime_profile failure_policy"
        in result.violations
    )


def test_post_planning_validator_rejects_memory_as_authority_justification() -> None:
    plan = safe_memory_plan()
    plan["authority_justification"] = {
        "memory_ids": ["memory-runtime-decision"],
        "reason": "Memory says this tool should be granted.",
    }

    result = PostPlanningMemoryInvariantValidator().validate(
        plan,
        runtime_profile=load_profile(),
    )

    assert not result.approved
    assert "memory IDs must not be used as authority justification" in result.violations
