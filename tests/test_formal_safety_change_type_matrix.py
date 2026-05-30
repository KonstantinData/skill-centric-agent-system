from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SCRIPTS = REPO_ROOT / "scripts" / "runtime"
sys.path.insert(0, str(RUNTIME_SCRIPTS))

import validate_formal_safety_change_type_matrix  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "schemas" / "formal-safety-change-type-matrix.schema.json"
POLICY_PATH = REPO_ROOT / "policies" / "runtime" / "formal-safety-change-type-matrix.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_formal_safety_change_type_matrix_schema_and_policy() -> None:
    schema = load_json(SCHEMA_PATH)
    policy = load_json(POLICY_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)
    assert validate_formal_safety_change_type_matrix.validate_matrix(POLICY_PATH) == []


def test_formal_safety_change_type_matrix_wired_in_docs() -> None:
    docs_index = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    policy_doc = (
        REPO_ROOT / "docs" / "policies" / "formal-safety-invariants.md"
    ).read_text(encoding="utf-8")
    queue = (REPO_ROOT / "docs" / "roadmap" / "scas-execution-queue.md").read_text(
        encoding="utf-8"
    )

    assert "formal-safety-change-type-matrix.md" in docs_index
    assert "formal-safety-change-type-matrix.md" in policy_doc
    assert "FSG-04 Build Positive/Negative Replay Fixture Corpus" in queue
