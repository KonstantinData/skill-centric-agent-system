from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.release.evaluate_automatic_rollback_rules import evaluate
from scripts.release.evaluate_automatic_rollback_rules import (
    main as rollback_cli_main,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "automatic-rollback-rules.schema.json"
POLICY_PATH = REPO_ROOT / "policies" / "runtime" / "automatic-rollback-rules.json"
PRE_CANARY_REPORT_PATH = (
    REPO_ROOT / "examples" / "operations" / "pre-canary-safety-gate-snapshot.json"
)
ROLLOUT_METADATA_PATH = (
    REPO_ROOT / "examples" / "operations" / "rollout-metadata-snapshot.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_automatic_rollback_policy_schema_and_policy() -> None:
    schema = load_json(SCHEMA_PATH)
    policy = load_json(POLICY_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)


def test_automatic_rollback_rules_pass_when_pre_canary_passes() -> None:
    result = evaluate(
        load_json(POLICY_PATH),
        load_json(PRE_CANARY_REPORT_PATH),
        load_json(ROLLOUT_METADATA_PATH),
    )

    assert result["status"] == "passed"
    assert result["rollback_required"] is False
    assert result["rollback_allowed"] is True


def test_automatic_rollback_rules_require_verified_lkg_on_failed_pre_canary() -> None:
    pre_canary = load_json(PRE_CANARY_REPORT_PATH)
    pre_canary["status"] = "failed"
    pre_canary["failure_reasons"] = ["simulated safety regression"]

    rollout = load_json(ROLLOUT_METADATA_PATH)
    rollout["last_known_good_versions"]["signature_verified"] = False
    result = evaluate(load_json(POLICY_PATH), pre_canary, rollout)

    assert result["status"] == "failed"
    assert result["rollback_required"] is True
    assert result["rollback_allowed"] is False
    assert result["required_remediation_paths"]


def test_automatic_rollback_cli_exits_zero_for_reference_inputs(tmp_path: Path) -> None:
    output = tmp_path / "production-evidence" / "automatic-rollback.json"
    exit_code = rollback_cli_main(
        [
            "--policy",
            str(POLICY_PATH),
            "--pre-canary-report",
            str(PRE_CANARY_REPORT_PATH),
            "--rollout-metadata",
            str(ROLLOUT_METADATA_PATH),
            "--output",
            str(output),
            "--fail-on-failed",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"


def test_automatic_rollback_rules_are_wired_into_docs() -> None:
    docs_index = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    invariant_policy = (
        REPO_ROOT / "docs" / "policies" / "formal-safety-invariants.md"
    ).read_text(encoding="utf-8")
    prod_readiness = (
        REPO_ROOT / "docs" / "policies" / "production-readiness.md"
    ).read_text(encoding="utf-8")

    assert "automatic-rollback-rules.md" in docs_index
    assert "automatic-rollback-rules.md" in invariant_policy
    assert "automatic-rollback-evaluation.json" in prod_readiness
