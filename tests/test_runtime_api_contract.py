from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_API_SCHEMA_PATH = REPO_ROOT / "schemas" / "runtime-api.schema.json"
RUNTIME_API_EXAMPLES_DIR = REPO_ROOT / "examples" / "runtime-api"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_runtime_api_examples_match_schema() -> None:
    schema = load_json(RUNTIME_API_SCHEMA_PATH)
    validator = Draft202012Validator(schema)

    for example_path in sorted(RUNTIME_API_EXAMPLES_DIR.glob("*.json")):
        validator.validate(load_json(example_path))


def test_runtime_api_postgres_storage_requires_secret_reference() -> None:
    schema = load_json(RUNTIME_API_SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    request = load_json(RUNTIME_API_EXAMPLES_DIR / "start-run-request.json")
    request["storage"] = {"mode": "postgres"}

    errors = list(validator.iter_errors(request))

    assert errors
    assert any("not valid under any of the given schemas" in error.message for error in errors)


def test_runtime_api_contract_documents_required_commands() -> None:
    contract = (REPO_ROOT / "docs" / "reference" / "runtime-api.md").read_text(
        encoding="utf-8"
    )
    for command in (
        "start run",
        "get status",
        "get result",
        "cancel run",
        "retry run",
    ):
        assert command in contract


def test_runtime_contract_keeps_recomposition_controlled() -> None:
    contract = (REPO_ROOT / "docs" / "policies" / "runtime-contract.md").read_text(
        encoding="utf-8"
    )
    assert "must never mutate the active profile" in contract
    assert "must not self-grant tools" in contract
