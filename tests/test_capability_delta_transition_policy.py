from __future__ import annotations

import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from scripts.runtime.validate_capability_delta_transition_policy import (
    CapabilityDeltaPolicyError,
    assert_policy_current,
    validate_capability_delta_policy,
)
from scripts.runtime.validate_capability_delta_transition_policy import (
    main as capability_delta_policy_cli_main,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "policies" / "runtime" / "capability-delta-transition-policy.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "capability-delta-transition-policy.schema.json"
MODULES_DIR = REPO_ROOT / "registry" / "modules"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_capability_delta_policy_matches_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    policy = load_json(POLICY_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)


def test_capability_delta_policy_fixture_is_current() -> None:
    report = assert_policy_current(
        policy_path=POLICY_PATH,
        schema_path=SCHEMA_PATH,
        modules_dir=MODULES_DIR,
    )

    assert report["status"] == "passed"
    assert report["summary"]["transition_rule_count"] == 6
    assert report["summary"]["exception_count"] == 0


def test_capability_delta_policy_defines_required_transition_rules() -> None:
    policy = load_json(POLICY_PATH)
    rule_ids = {rule["id"] for rule in policy["transition_rules"]}

    assert {
        "research-to-research",
        "research-to-repo-write",
        "repo-read-to-repo-write",
        "repo-write-to-protected-path-write",
        "protected-path-write-to-production-change",
        "any-to-secrets-sensitive",
    } <= rule_ids


def test_capability_delta_policy_covers_selectable_skill_capability_classes() -> None:
    policy = load_json(POLICY_PATH)
    mappings = policy["module_capability_mappings"]

    for module_path in MODULES_DIR.rglob("module.json"):
        module = load_json(module_path)
        if module["kind"] == "skill":
            assert module["capability_class"] in mappings


def test_capability_delta_policy_rejects_unmapped_skill_class(tmp_path: Path) -> None:
    modules_dir = tmp_path / "modules"
    module_dir = modules_dir / "common" / "skills" / "git-diff-analysis"
    module_dir.mkdir(parents=True)
    module = load_json(
        MODULES_DIR / "common" / "skills" / "git-diff-analysis" / "module.json"
    )
    module["capability_class"] = "unmapped"
    (module_dir / "module.json").write_text(
        json.dumps(module),
        encoding="utf-8",
    )

    with pytest.raises(CapabilityDeltaPolicyError, match="unmapped"):
        validate_capability_delta_policy(
            load_json(POLICY_PATH),
            schema_path=SCHEMA_PATH,
            modules_dir=modules_dir,
        )


def test_capability_delta_policy_rejects_expired_exception() -> None:
    policy = deepcopy(load_json(POLICY_PATH))
    policy["exceptions"] = [
        {
            "id": "temporary-bypass",
            "reason": "Fixture exception.",
            "expires": "2026-01-01",
            "approved_by": "@KonstantinData",
        }
    ]

    with pytest.raises(CapabilityDeltaPolicyError, match="expired"):
        validate_capability_delta_policy(
            policy,
            schema_path=SCHEMA_PATH,
            modules_dir=MODULES_DIR,
            today=date(2026, 6, 2),
        )


def test_capability_delta_policy_cli_check_passes() -> None:
    assert capability_delta_policy_cli_main(["--check"]) == 0
