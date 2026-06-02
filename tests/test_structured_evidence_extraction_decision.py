from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from scripts.runtime.validate_structured_evidence_extraction_decision import (
    StructuredEvidenceDecisionError,
    assert_decision_current,
    validate_structured_evidence_decision,
)
from scripts.runtime.validate_structured_evidence_extraction_decision import (
    main as structured_evidence_decision_cli_main,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = REPO_ROOT / "policies" / "runtime" / "structured-evidence-extraction-decision.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "structured-evidence-extraction-decision.schema.json"
ADR_PATH = REPO_ROOT / "docs" / "adr" / "0008-structured-outputs-evidence-span-extraction.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_structured_evidence_decision_matches_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    decision = load_json(DECISION_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(decision)


def test_structured_evidence_decision_is_current() -> None:
    report = assert_decision_current(decision_path=DECISION_PATH, schema_path=SCHEMA_PATH)

    assert report["status"] == "passed"
    assert report["summary"]["recommendation"] == "defer_runtime_adoption"


def test_structured_evidence_decision_rejects_runtime_adoption_without_subset_schema() -> None:
    decision = deepcopy(load_json(DECISION_PATH))
    decision["recommendation"] = "adopt_with_guardrails"
    decision["status"] = "accepted"

    with pytest.raises(StructuredEvidenceDecisionError, match="runtime adoption"):
        validate_structured_evidence_decision(decision, schema_path=SCHEMA_PATH)


def test_structured_evidence_decision_documents_provider_boundary() -> None:
    adr = ADR_PATH.read_text(encoding="utf-8")
    decision = load_json(DECISION_PATH)

    assert "Structured Outputs is treated as a format-quality optimization" in adr
    assert "deterministic_scanners_authoritative" in decision["required_guardrails"]
    assert "no_provider_output_can_grant_authority" in decision["required_guardrails"]


def test_structured_evidence_decision_cli_check_passes() -> None:
    assert structured_evidence_decision_cli_main(["--check"]) == 0
