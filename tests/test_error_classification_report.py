from __future__ import annotations

import json
from pathlib import Path

from scripts.operations.error_classification_report import build_report
from scripts.operations.error_classification_report import main as report_cli_main

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = (
    REPO_ROOT / "examples" / "operations" / "error-classification-report-snapshot.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_error_classification_report_aggregates_counts() -> None:
    report = build_report(load_json(SNAPSHOT_PATH))
    assert report["total_rows"] == 3
    assert report["class_counts"]["F1_INEFFICIENCY_PATH"] == 1
    assert report["class_counts"]["R8_POLICY_CONFLICT_CONTEXT_CONTAMINATION"] == 1
    assert report["by_environment"]["dev"]["NONE"] == 1


def test_error_classification_report_cli_writes_output(tmp_path: Path) -> None:
    output_path = tmp_path / "report.json"
    exit_code = report_cli_main(
        [
            "--snapshot",
            str(SNAPSHOT_PATH),
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0
    payload = load_json(output_path)
    assert payload["total_rows"] == 3
