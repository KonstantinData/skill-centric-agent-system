from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_SCHEMA_PATH = REPO_ROOT / "schemas" / "module.schema.json"
PROFILE_SCHEMA_PATH = REPO_ROOT / "schemas" / "runtime-profile.schema.json"
MODULE_EXAMPLE_PATH = REPO_ROOT / "examples" / "modules" / "git-diff-analysis.json"
PROFILE_EXAMPLE_PATH = REPO_ROOT / "examples" / "profiles" / "code-review-profile.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def module_schema() -> dict[str, Any]:
    schema = load_json(MODULE_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture(scope="module")
def profile_schema() -> dict[str, Any]:
    schema = load_json(PROFILE_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture
def module_example() -> dict[str, Any]:
    return load_json(MODULE_EXAMPLE_PATH)


@pytest.fixture
def profile_example() -> dict[str, Any]:
    return load_json(PROFILE_EXAMPLE_PATH)


def assert_valid(schema: dict[str, Any], instance: dict[str, Any]) -> None:
    Draft202012Validator(schema).validate(instance)


def assert_invalid(schema: dict[str, Any], instance: dict[str, Any], message_part: str) -> None:
    with pytest.raises(ValidationError, match=message_part):
        Draft202012Validator(schema).validate(instance)


def selected_profile_modules(profile: dict[str, Any]) -> set[str]:
    selected: set[str] = set()
    for field in (
        "instructions",
        "skills",
        "tools",
        "knowledge_scopes",
        "data_scopes",
        "memory_scopes",
        "policies",
        "validators",
    ):
        selected.update(profile[field])
    return selected


def assert_profile_version_pins_selected_modules(profile: dict[str, Any]) -> None:
    selected = selected_profile_modules(profile)
    pinned = set(profile["module_versions"])
    missing = selected - pinned
    extra = pinned - selected
    assert not missing, f"missing version pins: {sorted(missing)}"
    assert not extra, f"unselected version pins: {sorted(extra)}"


def test_module_example_matches_schema(
    module_schema: dict[str, Any],
    module_example: dict[str, Any],
) -> None:
    assert_valid(module_schema, module_example)


def test_runtime_profile_example_matches_schema_and_version_contract(
    profile_schema: dict[str, Any],
    profile_example: dict[str, Any],
) -> None:
    assert_valid(profile_schema, profile_example)
    assert_profile_version_pins_selected_modules(profile_example)


@pytest.mark.parametrize(
    ("mutator", "message_part"),
    [
        (
            lambda module: module.pop("selection"),
            "'selection' is a required property",
        ),
        (
            lambda module: module.__setitem__("kind", "agent"),
            "'agent' is not one of",
        ),
        (
            lambda module: module.__setitem__("version", "v1"),
            "'v1' does not match",
        ),
        (
            lambda module: module["selection"]["score_modifiers"][0].__setitem__("weight", 2),
            "2 is greater than the maximum of 1",
        ),
        (
            lambda module: module.pop("task_signals"),
            "'task_signals' is a required property",
        ),
    ],
)
def test_invalid_module_metadata_is_rejected(
    module_schema: dict[str, Any],
    module_example: dict[str, Any],
    mutator: Any,
    message_part: str,
) -> None:
    invalid_module = deepcopy(module_example)
    mutator(invalid_module)

    assert_invalid(module_schema, invalid_module, message_part)


def test_keyword_only_module_metadata_is_rejected(
    module_schema: dict[str, Any],
    module_example: dict[str, Any],
) -> None:
    keyword_only_module = {
        key: value
        for key, value in module_example.items()
        if key not in {"capability_class", "domain_tags", "task_signals", "selection"}
    }

    assert_invalid(module_schema, keyword_only_module, "'capability_class' is a required property")


@pytest.mark.parametrize(
    ("mutator", "message_part"),
    [
        (
            lambda profile: profile.pop("module_versions"),
            "'module_versions' is a required property",
        ),
        (
            lambda profile: profile.__setitem__("risk_level", "severe"),
            "'severe' is not one of",
        ),
        (
            lambda profile: profile["limits"].pop("max_tokens"),
            "'max_tokens' is a required property",
        ),
        (
            lambda profile: profile["failure_policy"].__setitem__(
                "on_policy_denial",
                "continue_anyway",
            ),
            "'continue_anyway' is not one of",
        ),
    ],
)
def test_invalid_runtime_profiles_are_rejected_by_schema(
    profile_schema: dict[str, Any],
    profile_example: dict[str, Any],
    mutator: Any,
    message_part: str,
) -> None:
    invalid_profile = deepcopy(profile_example)
    mutator(invalid_profile)

    assert_invalid(profile_schema, invalid_profile, message_part)


def test_runtime_profile_rejects_missing_version_pin(
    profile_schema: dict[str, Any],
    profile_example: dict[str, Any],
) -> None:
    invalid_profile = deepcopy(profile_example)
    invalid_profile["module_versions"].pop("git-diff-analysis")

    assert_valid(profile_schema, invalid_profile)
    with pytest.raises(AssertionError, match="missing version pins"):
        assert_profile_version_pins_selected_modules(invalid_profile)


def test_runtime_profile_rejects_unselected_version_pin(
    profile_schema: dict[str, Any],
    profile_example: dict[str, Any],
) -> None:
    invalid_profile = deepcopy(profile_example)
    invalid_profile["module_versions"]["unselected-module"] = "0.1.0"

    assert_valid(profile_schema, invalid_profile)
    with pytest.raises(AssertionError, match="unselected version pins"):
        assert_profile_version_pins_selected_modules(invalid_profile)
