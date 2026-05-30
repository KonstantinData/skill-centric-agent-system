from __future__ import annotations

import json
from pathlib import Path

from scripts.runtime.run_incident_locked_regressions import (
    main as incident_cli_main,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
INCIDENTS_PATH = (
    REPO_ROOT / "examples" / "evaluations" / "incident-locked-regression-cases.json"
)
MATRIX_PATH = (
    REPO_ROOT / "policies" / "runtime" / "formal-safety-change-type-matrix.json"
)
PROFILES_DIR = REPO_ROOT / "examples" / "profiles"


def test_incident_locked_regressions_pass_for_reference_cases(tmp_path: Path) -> None:
    output = tmp_path / "ci-evidence" / "incident-locked-regressions.json"
    exit_code = incident_cli_main(
        [
            "--incidents",
            str(INCIDENTS_PATH),
            "--matrix-policy",
            str(MATRIX_PATH),
            "--profiles-dir",
            str(PROFILES_DIR),
            "--output-json",
            str(output),
            "--fail-on-failed",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert payload["binding_failure_count"] == 0
    assert payload["replay_mismatch_count"] == 0
    assert payload["incident_count"] >= 3


def test_incident_locked_regressions_fail_on_change_type_binding_violation(tmp_path: Path) -> None:
    incidents = json.loads(INCIDENTS_PATH.read_text(encoding="utf-8"))
    incidents[0]["change_type"] = "governance-doc"
    invalid_incidents_path = tmp_path / "invalid-incidents.json"
    invalid_incidents_path.write_text(json.dumps(incidents, indent=2), encoding="utf-8")

    output = tmp_path / "invalid-output.json"
    exit_code = incident_cli_main(
        [
            "--incidents",
            str(invalid_incidents_path),
            "--matrix-policy",
            str(MATRIX_PATH),
            "--profiles-dir",
            str(PROFILES_DIR),
            "--output-json",
            str(output),
            "--fail-on-failed",
        ]
    )

    assert exit_code == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["binding_failure_count"] > 0


def test_incident_locked_regressions_are_wired_into_docs_and_queue() -> None:
    docs_index = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    invariant_policy = (
        REPO_ROOT / "docs" / "policies" / "formal-safety-invariants.md"
    ).read_text(encoding="utf-8")
    queue = (REPO_ROOT / "docs" / "roadmap" / "scas-execution-queue.md").read_text(
        encoding="utf-8"
    )

    assert "incident-locked-regressions.md" in docs_index
    assert "incident-locked-regressions.md" in invariant_policy
    assert "FSG-12 Publish ADR for Formal Safety Guarantees" in queue
