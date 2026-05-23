from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_OUTPUT_SCHEMA_PATH = REPO_ROOT / "schemas" / "runtime-output.schema.json"
RUNTIME_OUTPUT_EXAMPLES_DIR = REPO_ROOT / "examples" / "runtime-outputs"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_runtime_output_examples_match_schema() -> None:
    schema = load_json(RUNTIME_OUTPUT_SCHEMA_PATH)
    validator = Draft202012Validator(schema)

    for example_path in sorted(RUNTIME_OUTPUT_EXAMPLES_DIR.glob("*.json")):
        validator.validate(load_json(example_path))


@pytest.mark.parametrize(
    ("example_name", "mutator", "message_part"),
    [
        (
            "code-review-output.json",
            lambda output: output["details"].pop("findings"),
            "'findings' is a required property",
        ),
        (
            "research-output.json",
            lambda output: output["details"].__setitem__("key_points", []),
            "should be non-empty",
        ),
        (
            "task-execution-output.json",
            lambda output: output["details"].pop("planned_changes"),
            "'planned_changes' is a required property",
        ),
        (
            "general-task-output.json",
            lambda output: output.__setitem__("task_type", "freeform"),
            "'freeform' is not one of",
        ),
    ],
)
def test_invalid_runtime_outputs_are_rejected(
    example_name: str,
    mutator: Any,
    message_part: str,
) -> None:
    schema = load_json(RUNTIME_OUTPUT_SCHEMA_PATH)
    output = deepcopy(load_json(RUNTIME_OUTPUT_EXAMPLES_DIR / example_name))
    mutator(output)

    with pytest.raises(ValidationError, match=message_part):
        Draft202012Validator(schema).validate(output)
