from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_API_SCHEMA_PATH = REPO_ROOT / "schemas" / "runtime-api.schema.json"
RUNTIME_API_EXAMPLES_DIR = REPO_ROOT / "examples" / "runtime-api"
INTENT_TRANSITION_GATES_PATH = (
    REPO_ROOT / "docs" / "policies" / "intent-transition-gates.md"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_markdown(text: str) -> str:
    return " ".join(text.split())


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


def test_intent_transition_gate_contract_defines_required_evidence() -> None:
    contract = INTENT_TRANSITION_GATES_PATH.read_text(encoding="utf-8")

    for required_term in (
        "Transition Evidence Contract",
        "EvidenceSpan",
        "artifact_id",
        "artifact_hash",
        "offset_start",
        "offset_end",
        "capability_delta",
        "repository_bound",
        "explicit_write_intent",
        "requires_recomposition",
        "requires_human_review",
        "unknown",
    ):
        assert required_term in contract


def test_intent_transition_gate_contract_fails_closed_on_uncertainty() -> None:
    contract = INTENT_TRANSITION_GATES_PATH.read_text(encoding="utf-8")
    normalized = normalize_markdown(contract)

    assert "`unknown` behaves like not authorized" in contract
    assert "must fail closed for capability escalation" in normalized
    assert "scanner_critical_signals <= extracted_critical_signals" in contract
    assert "must not authorize capability escalation" in normalized


def test_runtime_contract_references_intent_transition_gates() -> None:
    contract = (REPO_ROOT / "docs" / "policies" / "runtime-contract.md").read_text(
        encoding="utf-8"
    )
    normalized = normalize_markdown(contract)

    assert "docs/policies/intent-transition-gates.md" in contract
    assert "must not inherit write authority" in normalized
