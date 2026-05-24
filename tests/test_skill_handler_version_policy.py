from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from skill_centric_agent_system.runtime import (
    ProfileEnforcementError,
    RuntimeProfileEnforcer,
    SkillHandler,
    SkillHandlerRegistry,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "policies" / "runtime" / "skill-handler-version-policy.json"
POLICY_SCHEMA_PATH = REPO_ROOT / "schemas" / "skill-handler-version-policy.schema.json"
COVERAGE_MANIFEST_PATH = (
    REPO_ROOT / "examples" / "runtime" / "skill-handler-coverage.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_skill_handler_version_policy_matches_schema() -> None:
    policy = load_json(POLICY_PATH)
    schema = load_json(POLICY_SCHEMA_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)


def test_skill_handler_version_policy_defines_required_controls() -> None:
    policy = load_json(POLICY_PATH)
    rule_ids = {rule["rule_id"] for rule in policy["compatibility_rules"]}

    assert {
        "exact-version-binding",
        "side-by-side-upgrades",
        "deprecated-handlers-stay-registered",
        "no-in-place-profile-mutation",
    } <= rule_ids
    assert policy["release_evidence"]["requires_static_coverage_manifest"] is True
    assert policy["release_evidence"]["requires_live_handler_binding_evidence_for_certify"] is True
    assert policy["rollback_policy"]["profile_policy"] == (
        "compose-new-runtime-profile-with-previous-version-pin"
    )


def test_skill_handler_coverage_manifest_records_lifecycle_status() -> None:
    manifest = load_json(COVERAGE_MANIFEST_PATH)

    assert manifest["skills"]
    assert {skill["lifecycle_status"] for skill in manifest["skills"]} == {"active"}


def test_skill_handler_registry_supports_side_by_side_upgrade_versions() -> None:
    registry = SkillHandlerRegistry(
        (
            _handler("example-skill", "0.1.0", lifecycle_status="deprecated"),
            _handler("example-skill", "0.2.0"),
        )
    )
    profile = _profile("0.2.0")

    plan = registry.build_plan(profile, enforcer=RuntimeProfileEnforcer(profile))

    assert plan.skill_handlers == (
        {
            "name": "example-skill",
            "version": "0.2.0",
            "handler_id": "example-skill@0.2.0",
        },
    )
    assert [handler.lifecycle_status for handler in registry.handlers()] == [
        "deprecated",
        "active",
    ]


def test_skill_handler_rollback_uses_previous_registered_version_pin() -> None:
    registry = SkillHandlerRegistry((_handler("example-skill", "0.1.0"),))
    removed_version_profile = _profile("0.2.0")
    rollback_profile = _profile("0.1.0")

    with pytest.raises(ProfileEnforcementError) as exc_info:
        registry.build_plan(
            removed_version_profile,
            enforcer=RuntimeProfileEnforcer(removed_version_profile),
        )

    assert exc_info.value.code == "skill_handler_version_mismatch"
    rollback_plan = registry.build_plan(
        rollback_profile,
        enforcer=RuntimeProfileEnforcer(rollback_profile),
    )
    assert rollback_plan.skill_handlers[0]["handler_id"] == "example-skill@0.1.0"


def _handler(
    skill_name: str,
    skill_version: str,
    *,
    lifecycle_status: str = "active",
) -> SkillHandler:
    return SkillHandler(
        skill_name=skill_name,
        skill_version=skill_version,
        strategy=f"{skill_name}-{skill_version}",
        output_contract="example-output-contract",
        build_actions=lambda profile: (),
        test_coverage=("tests/test_skill_handler_version_policy.py",),
        lifecycle_status=lifecycle_status,  # type: ignore[arg-type]
    )


def _profile(skill_version: str) -> dict[str, Any]:
    return {
        "profile_generation": 1,
        "skills": ["example-skill"],
        "module_versions": {"example-skill": skill_version},
    }
