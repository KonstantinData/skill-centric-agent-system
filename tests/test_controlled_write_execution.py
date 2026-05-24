from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_SCHEMA_PATH = REPO_ROOT / "schemas" / "write-approval-policy.schema.json"
POLICY_PATH = REPO_ROOT / "policies" / "runtime" / "write-approval-required.json"
PROFILE_SCHEMA_PATH = REPO_ROOT / "schemas" / "runtime-profile.schema.json"
PROFILE_PATH = REPO_ROOT / "examples" / "profiles" / "controlled-write-profile.json"
ACTION_PLAN_PATH = REPO_ROOT / "examples" / "runtime" / "controlled-write-action-plan.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_write_approval_policy_schema_and_policy_are_valid() -> None:
    schema = load_json(POLICY_SCHEMA_PATH)
    policy = load_json(POLICY_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)


def test_controlled_write_profile_matches_runtime_profile_schema() -> None:
    Draft202012Validator(load_json(PROFILE_SCHEMA_PATH)).validate(load_json(PROFILE_PATH))


def test_controlled_write_example_is_structured_not_shell() -> None:
    action_plan = load_json(ACTION_PLAN_PATH)
    payload = action_plan["payload"]

    assert action_plan["tool"] == "filesystem-write"
    assert payload["operation"] == "write_text_file"
    assert "command" not in payload
    assert "shell" not in payload
    assert payload["approval"]["policy_id"] == "write-approval-required"
    assert payload["rollback"]["strategy"] == "delete_created_file"
