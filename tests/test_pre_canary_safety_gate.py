from __future__ import annotations

import json
from pathlib import Path

from scripts.release.evaluate_pre_canary_gate import evaluate
from scripts.release.evaluate_pre_canary_gate import main as pre_canary_cli_main

REPO_ROOT = Path(__file__).resolve().parents[1]
INVARIANT_REPORT_PATH = (
    REPO_ROOT / "examples" / "operations" / "invariant-check-report-snapshot.json"
)
SHADOW_THRESHOLD_REPORT_PATH = (
    REPO_ROOT / "examples" / "operations" / "shadow-regression-threshold-evaluation.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_pre_canary_safety_gate_passes_for_reference_reports() -> None:
    result = evaluate(
        load_json(INVARIANT_REPORT_PATH),
        load_json(SHADOW_THRESHOLD_REPORT_PATH),
    )

    assert result["status"] == "passed"
    assert result["gates"]["invariant_check"]["passed"] is True
    assert result["gates"]["shadow_regression_thresholds"]["passed"] is True
    assert result["failure_reasons"] == []


def test_pre_canary_safety_gate_fails_with_remediation_when_thresholds_fail() -> None:
    shadow_report = load_json(SHADOW_THRESHOLD_REPORT_PATH)
    shadow_report["status"] = "failed"
    shadow_report["threshold_checks"]["safety_false_negative_delta_max"]["passed"] = False
    shadow_report["threshold_checks"]["safety_false_negative_delta_max"]["actual"] = 0.9

    result = evaluate(load_json(INVARIANT_REPORT_PATH), shadow_report)

    assert result["status"] == "failed"
    assert any(
        "Shadow regression threshold gate failed" in item
        for item in result["failure_reasons"]
    )
    assert result["required_remediation_paths"]


def test_pre_canary_safety_gate_cli_exits_zero_for_reference_reports(tmp_path: Path) -> None:
    output = tmp_path / "production-evidence" / "pre-canary-safety-gate.json"
    exit_code = pre_canary_cli_main(
        [
            "--invariant-report",
            str(INVARIANT_REPORT_PATH),
            "--shadow-threshold-report",
            str(SHADOW_THRESHOLD_REPORT_PATH),
            "--output",
            str(output),
            "--fail-on-failed",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
