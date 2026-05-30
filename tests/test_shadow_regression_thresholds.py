from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.operations.evaluate_shadow_regression_thresholds import (
    evaluate,
)
from scripts.operations.evaluate_shadow_regression_thresholds import (
    main as thresholds_cli_main,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "shadow-regression-thresholds.schema.json"
POLICY_PATH = REPO_ROOT / "policies" / "runtime" / "shadow-regression-thresholds.json"
REPORT_PATH = REPO_ROOT / "examples" / "operations" / "shadow-eval-report-snapshot.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_shadow_regression_threshold_policy_schema_and_policy() -> None:
    schema = load_json(SCHEMA_PATH)
    policy = load_json(POLICY_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)


def test_shadow_regression_thresholds_pass_for_reference_report() -> None:
    result = evaluate(load_json(POLICY_PATH), load_json(REPORT_PATH))

    assert result["status"] == "passed"
    assert result["summary"]["threshold_passed"] is True
    assert result["summary"]["selection_passed"] is True
    assert result["summary"]["missing_thresholds_passed"] is True


def test_shadow_regression_thresholds_fail_for_safety_regression() -> None:
    report = load_json(REPORT_PATH)
    report["metrics"]["safety_false_negative_rate"]["delta"] = 0.9
    result = evaluate(load_json(POLICY_PATH), report)

    assert result["status"] == "failed"
    assert result["threshold_checks"]["safety_false_negative_delta_max"]["passed"] is False


def test_shadow_regression_threshold_cli_fails_on_failed_report() -> None:
    exit_code = thresholds_cli_main(
        [
            "--policy",
            str(POLICY_PATH),
            "--report",
            str(REPORT_PATH),
            "--fail-on-failed",
        ]
    )
    assert exit_code == 0


def test_shadow_regression_thresholds_are_wired_into_docs() -> None:
    docs_index = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    invariants = (
        REPO_ROOT / "docs" / "policies" / "formal-safety-invariants.md"
    ).read_text(encoding="utf-8")
    threshold_doc = (
        REPO_ROOT / "docs" / "policies" / "shadow-regression-thresholds.md"
    ).read_text(encoding="utf-8")

    assert "shadow-regression-thresholds.md" in docs_index
    assert "shadow-regression-thresholds.md" in invariants
    assert "shadow-regression-thresholds.json" in threshold_doc
