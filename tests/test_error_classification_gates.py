from __future__ import annotations

import json
from pathlib import Path

from scripts.operations.evaluate_error_classification_gates import (
    evaluate,
)
from scripts.operations.evaluate_error_classification_gates import (
    main as gates_cli_main,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "examples" / "operations" / "error-classification-gate-policy.json"
SNAPSHOT_PATH = REPO_ROOT / "examples" / "operations" / "error-classification-gate-snapshot.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_error_classification_gates_pass_for_clean_snapshot() -> None:
    result = evaluate(load_json(POLICY_PATH), load_json(SNAPSHOT_PATH))
    assert result["status"] == "passed"
    assert all(result["checks"].values())


def test_error_classification_gates_fail_for_r8_regression() -> None:
    snapshot = load_json(SNAPSHOT_PATH)
    snapshot["metrics"]["r8_rate_max"] = 0.08
    result = evaluate(load_json(POLICY_PATH), snapshot)
    assert result["status"] == "failed"
    assert result["checks"]["r8_rate_max"] is False


def test_error_classification_gates_cli_exits_non_zero_on_failed() -> None:
    exit_code = gates_cli_main(
        [
            "--policy",
            str(POLICY_PATH),
            "--snapshot",
            str(SNAPSHOT_PATH),
            "--fail-on-failed",
        ]
    )
    assert exit_code == 0
