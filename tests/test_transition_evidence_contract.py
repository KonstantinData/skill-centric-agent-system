from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from scripts.runtime.validate_transition_evidence import (
    TransitionEvidenceError,
    assert_evidence_current,
    validate_transition_evidence,
)
from scripts.runtime.validate_transition_evidence import (
    main as transition_evidence_cli_main,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPO_ROOT / "examples" / "evaluations" / "transition-evidence.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "transition-evidence.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_transition_evidence_matches_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    evidence = load_json(EVIDENCE_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(evidence)


def test_transition_evidence_fixture_is_current() -> None:
    report = assert_evidence_current(
        evidence_path=EVIDENCE_PATH,
        schema_path=SCHEMA_PATH,
    )

    assert report["status"] == "passed"
    assert report["summary"]["raw_artifact_count"] == 1
    assert report["summary"]["mentioned_path_count"] == 1
    assert report["summary"]["escalates_authority"] is True
    assert report["summary"]["decision"] == "recomposition_required"


def test_transition_evidence_requires_scanner_version_inventory() -> None:
    evidence = deepcopy(load_json(EVIDENCE_PATH))
    del evidence["source"]["scanner_versions"]["protected_path"]

    with pytest.raises(TransitionEvidenceError, match="scanner_versions"):
        validate_transition_evidence(evidence, schema_path=SCHEMA_PATH)


def test_transition_evidence_rejects_invalid_span_offsets() -> None:
    evidence = deepcopy(load_json(EVIDENCE_PATH))
    evidence["mentioned_paths"][0]["evidence"]["offset_start"] = 18

    with pytest.raises(TransitionEvidenceError, match="span does not match"):
        validate_transition_evidence(evidence, schema_path=SCHEMA_PATH)


def test_transition_evidence_rejects_hash_mismatch() -> None:
    evidence = deepcopy(load_json(EVIDENCE_PATH))
    evidence["raw_artifacts"][0]["text"] = "Apply the fix to src/bar.ts in this repo."

    with pytest.raises(TransitionEvidenceError, match="artifact_hash"):
        validate_transition_evidence(evidence, schema_path=SCHEMA_PATH)


def test_transition_evidence_requires_evidence_for_true_critical_fields() -> None:
    evidence = deepcopy(load_json(EVIDENCE_PATH))
    evidence["critical_fields"]["explicit_write_intent"]["evidence"] = []

    with pytest.raises(TransitionEvidenceError, match="explicit_write_intent"):
        validate_transition_evidence(evidence, schema_path=SCHEMA_PATH)


def test_transition_evidence_rejects_uncovered_scanner_path() -> None:
    evidence = deepcopy(load_json(EVIDENCE_PATH))
    evidence["mentioned_paths"] = []

    with pytest.raises(TransitionEvidenceError, match="scanner signal not covered"):
        validate_transition_evidence(evidence, schema_path=SCHEMA_PATH)


def test_transition_evidence_rejects_uncovered_scanner_write_intent() -> None:
    evidence = deepcopy(load_json(EVIDENCE_PATH))
    evidence["critical_fields"]["explicit_write_intent"]["evidence"] = [
        {
            "artifact_id": "turn-apply-ts2322-fix",
            "artifact_hash": evidence["raw_artifacts"][0]["artifact_hash"],
            "span": "src/foo.ts",
            "offset_start": 17,
            "offset_end": 27,
            "source": "scanner:path",
        }
    ]

    with pytest.raises(TransitionEvidenceError, match="scanner signal not covered"):
        validate_transition_evidence(evidence, schema_path=SCHEMA_PATH)


def test_transition_evidence_unknown_blocks_capability_escalation() -> None:
    evidence = deepcopy(load_json(EVIDENCE_PATH))
    evidence["critical_fields"]["repository_bound"] = {
        "value": "unknown",
        "evidence": [],
    }
    evidence["decision"]["unknown_fields"] = ["repository_bound"]
    evidence["decision"]["status"] = "recomposition_required"

    with pytest.raises(TransitionEvidenceError, match="unknown escalation-critical"):
        validate_transition_evidence(evidence, schema_path=SCHEMA_PATH)


def test_transition_evidence_unknown_can_request_clarification() -> None:
    evidence = deepcopy(load_json(EVIDENCE_PATH))
    raw_text = "Apply the fix."
    raw_hash = sha256(raw_text)
    evidence["raw_artifacts"][0]["text"] = raw_text
    evidence["raw_artifacts"][0]["artifact_hash"] = raw_hash
    evidence["mentioned_paths"] = []
    evidence["critical_fields"]["explicit_write_intent"]["evidence"] = [
        {
            "artifact_id": "turn-apply-ts2322-fix",
            "artifact_hash": raw_hash,
            "span": "Apply the fix",
            "offset_start": 0,
            "offset_end": 13,
            "source": "scanner:write_intent",
        }
    ]
    evidence["critical_fields"]["raw_artifact_hash_verified"]["evidence"] = [
        {
            "artifact_id": "turn-apply-ts2322-fix",
            "artifact_hash": raw_hash,
            "span": raw_text,
            "offset_start": 0,
            "offset_end": len(raw_text),
            "source": "system",
        }
    ]
    evidence["critical_fields"]["previous_profile_authority_verified"]["evidence"] = [
        {
            "artifact_id": "turn-apply-ts2322-fix",
            "artifact_hash": raw_hash,
            "span": raw_text,
            "offset_start": 0,
            "offset_end": len(raw_text),
            "source": "system",
        }
    ]
    evidence["critical_fields"]["repository_bound"] = {
        "value": "unknown",
        "evidence": [],
    }
    evidence["decision"]["unknown_fields"] = ["repository_bound"]
    evidence["decision"]["status"] = "clarification_required"
    evidence["decision"]["reason"] = "Repository binding is unknown."
    evidence["decision"]["missing_evidence"] = ["repository_bound"]

    report = validate_transition_evidence(evidence, schema_path=SCHEMA_PATH)

    assert report["status"] == "passed"
    assert report["summary"]["unknown_field_count"] == 1


def test_transition_evidence_cli_check_passes() -> None:
    assert transition_evidence_cli_main(["--check"]) == 0
