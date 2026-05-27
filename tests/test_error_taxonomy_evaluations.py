from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from skill_centric_agent_system.runtime.error_taxonomy import (
    classify_runtime_failure,
    classify_runtime_success,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_CASES_PATH = REPO_ROOT / "examples" / "evaluations" / "error-taxonomy-cases.json"
CLASSIFICATION_SCHEMA_PATH = REPO_ROOT / "schemas" / "error-classification.schema.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def test_error_taxonomy_evaluation_cases_match_expected_class() -> None:
    cases = load_json(EVAL_CASES_PATH)
    schema = load_json(CLASSIFICATION_SCHEMA_PATH)
    validator = Draft202012Validator(schema)

    for case in cases:
        data = case["input"]
        if data["status"] == "succeeded":
            classification = classify_runtime_success(
                plan={"actions": [{}] * data["action_count"]},
                execution={"tool_results": [{}] * data["tool_result_count"]},
                enforcer_counters={
                    "tool_calls": data["tool_calls"],
                    "tokens_used": data["tokens_used"],
                },
                profile_limits={"max_tokens": data["max_tokens"]},
            )
        else:
            classification = classify_runtime_failure(
                error=RuntimeError(data["message"]),
                stop_reason=data["stop_reason"],
                error_code=data["error_code"],
                enforcer_counters={"tool_calls": 0, "tokens_used": 0},
            )
        payload = classification.as_dict()
        validator.validate(payload)
        assert payload["error_class"] == case["expected_error_class"], case["name"]
