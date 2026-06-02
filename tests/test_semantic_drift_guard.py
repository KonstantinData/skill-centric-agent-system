from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SCRIPTS = REPO_ROOT / "scripts" / "runtime"
sys.path.insert(0, str(RUNTIME_SCRIPTS))

import validate_semantic_drift_guard  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "schemas" / "contrastive-pair.schema.json"
POLICY_PATH = REPO_ROOT / "policies" / "runtime" / "semantic-drift-guard.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_semantic_drift_guard_schema_and_policy() -> None:
    schema = load_json(SCHEMA_PATH)
    policy = load_json(POLICY_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)
    assert validate_semantic_drift_guard.validate_guard(POLICY_PATH) == []


def test_semantic_drift_guard_rejects_authority_delta_free_pair() -> None:
    schema = load_json(SCHEMA_PATH)
    invalid_policy = deepcopy(load_json(POLICY_PATH))
    invalid_policy["contrastive_pairs"][0]["forbidden_generalization"][
        "authority_delta"
    ] = []

    with pytest.raises(ValidationError, match="should be non-empty"):
        Draft202012Validator(schema).validate(invalid_policy)


def test_staging_budget_gap_does_not_auto_generalize_to_prod() -> None:
    guard = load_json(POLICY_PATH)
    analyzer_prior = {
        "source_context": {
            "environment": "staging",
            "risk_level": "medium",
            "workflow_id": "runtime-preflight-required",
            "principal_role": "repository-maintainer",
            "task_type": "production-preflight",
        },
        "target_context": {
            "environment": "prod",
            "risk_level": "high",
            "workflow_id": "runtime-preflight-required",
            "principal_role": "repository-maintainer",
            "task_type": "production-preflight",
        },
        "authority_delta": ["budget_increase"],
    }

    assert validate_semantic_drift_guard.matching_contrastive_pairs(
        guard,
        analyzer_prior,
    ) == [
        {
            "pair_id": "staging-budget-gap-must-not-generalize-to-prod",
            "decision": "needs_human_review",
        }
    ]


def test_ranking_only_prior_does_not_match_authority_boundary() -> None:
    guard = load_json(POLICY_PATH)
    analyzer_prior = {
        "source_context": {
            "environment": "staging",
            "risk_level": "medium",
            "workflow_id": "runtime-preflight-required",
            "principal_role": "repository-maintainer",
            "task_type": "production-preflight",
        },
        "target_context": {
            "environment": "prod",
            "risk_level": "high",
            "workflow_id": "runtime-preflight-required",
            "principal_role": "repository-maintainer",
            "task_type": "production-preflight",
        },
        "authority_delta": [],
    }

    assert validate_semantic_drift_guard.matching_contrastive_pairs(
        guard,
        analyzer_prior,
    ) == []


def test_semantic_drift_guard_wired_into_docs() -> None:
    contracts = (REPO_ROOT / "docs" / "policies" / "contracts.md").read_text(
        encoding="utf-8"
    )
    invariants = (
        REPO_ROOT / "docs" / "policies" / "formal-safety-invariants.md"
    ).read_text(encoding="utf-8")
    adr = (
        REPO_ROOT / "docs" / "adr" / "0007-learned-context-authority-boundary.md"
    ).read_text(encoding="utf-8")

    assert "semantic-drift-guard.md" in contracts
    assert "`learned_context_not_authority`" in invariants
    assert "schemas/contrastive-pair.schema.json" in adr
