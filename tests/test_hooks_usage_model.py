from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from scripts.runtime.validate_hooks_usage_model import (
    HooksUsageModelError,
    assert_policy_current,
    validate_policy,
)
from scripts.runtime.validate_hooks_usage_model import main as hooks_cli_main

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "policies" / "runtime" / "hooks-usage-model.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "hooks-usage-model.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_hooks_usage_model_matches_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    policy = load_json(POLICY_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)


def test_hooks_usage_model_policy_is_current() -> None:
    report = assert_policy_current(policy_path=POLICY_PATH, schema_path=SCHEMA_PATH)

    assert report["status"] == "passed"
    assert report["summary"]["hook_count"] == 8
    assert report["summary"]["forbidden_capability_count"] == 8


def test_hooks_usage_model_fails_closed_when_hook_can_grant_capabilities() -> None:
    policy = deepcopy(load_json(POLICY_PATH))
    hook = policy["hook_points"][0]
    hook["forbidden_effects"].remove("grant_capability")

    with pytest.raises(HooksUsageModelError, match="grant_capability"):
        validate_policy(policy, schema_path=SCHEMA_PATH)


def test_hooks_usage_model_rejects_missing_required_hook_point() -> None:
    policy = deepcopy(load_json(POLICY_PATH))
    policy["hook_points"] = [
        hook
        for hook in policy["hook_points"]
        if hook["id"] != "runtime-before-tool"
    ]

    with pytest.raises(HooksUsageModelError, match="runtime-before-tool"):
        validate_policy(policy, schema_path=SCHEMA_PATH)


def test_hooks_usage_model_cli_check_passes() -> None:
    assert hooks_cli_main(["--check"]) == 0
