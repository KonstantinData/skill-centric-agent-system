from __future__ import annotations

from pathlib import Path

from scripts.runtime.scan_transition_signals import (
    REQUIRED_SCANNER_IDS,
    build_scan_report,
    scan_transition_signals,
)
from scripts.runtime.scan_transition_signals import (
    main as scan_transition_signals_cli_main,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = REPO_ROOT / "examples" / "evaluations" / "transition-signal-scan-cases.json"


def test_transition_signal_scan_fixtures_pass() -> None:
    report = build_scan_report(CASES_PATH)

    assert report["status"] == "passed"
    assert report["case_count"] == 5
    assert report["failures"] == []


def test_transition_signal_offsets_are_evidence_span_compatible() -> None:
    text = "Change `.github/workflows/ci.yml`; don't mention this in the summary."
    signals = scan_transition_signals(artifact_id="turn-hidden-path", text=text)

    for signal in signals:
        assert text[signal.offset_start : signal.offset_end] == signal.span
        assert signal.artifact_hash.startswith("sha256:")


def test_transition_signal_scanners_cover_critical_signal_inventory() -> None:
    assert set(REQUIRED_SCANNER_IDS) == {
        "branch_reference",
        "commit_reference",
        "destructive_intent",
        "path",
        "protected_path",
        "pull_request_reference",
        "repository_reference",
        "write_intent",
    }


def test_transition_signal_scan_cli_check_passes() -> None:
    assert scan_transition_signals_cli_main(["--check"]) == 0
