from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.operations.evaluate_shadow_profile_versions import (
    main as shadow_eval_cli_main,
)
from skill_centric_agent_system.operations.shadow_evaluation import (
    ShadowEvaluationError,
    evaluate_shadow_snapshot,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = REPO_ROOT / "examples" / "operations" / "shadow-eval-trace-snapshot.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_shadow_evaluation_harness_emits_expected_drift_metrics() -> None:
    result = evaluate_shadow_snapshot(load_json(SNAPSHOT_PATH))
    metrics = result["metrics"]

    assert result["status"] == "passed"
    assert result["event_count"] == 6
    assert result["evaluation_error_count"] == 0
    assert metrics["decision_change_rate"] == pytest.approx(0.5)
    assert metrics["abstention_rate"]["delta"] == pytest.approx(1.0 / 6.0)
    assert metrics["mixed_profile_rate"]["delta"] == pytest.approx(0.0)
    assert metrics["safety_false_negative_rate"]["delta"] == pytest.approx(0.5)

    code_review = metrics["selection_drift_by_change_type"]["code-review"]
    assert code_review["precision"]["delta"] == pytest.approx(-0.2)
    assert code_review["recall"]["delta"] == pytest.approx(0.25)

    policy_change = metrics["selection_drift_by_change_type"]["policy-change"]
    assert policy_change["recall"]["delta"] == pytest.approx(-0.5)


def test_shadow_evaluation_harness_fails_closed_on_invalid_event_shape() -> None:
    snapshot = load_json(SNAPSHOT_PATH)
    snapshot["trace_events"][0]["candidate"]["abstained"] = "nope"
    result = evaluate_shadow_snapshot(snapshot)

    assert result["status"] == "failed"
    assert result["evaluation_error_count"] > 0
    assert result["evaluation_errors"]


def test_shadow_evaluation_harness_rejects_non_list_trace_events() -> None:
    snapshot = load_json(SNAPSHOT_PATH)
    snapshot["trace_events"] = {"bad": "shape"}
    with pytest.raises(ShadowEvaluationError):
        evaluate_shadow_snapshot(snapshot)


def test_shadow_evaluation_cli_writes_json_output(tmp_path: Path) -> None:
    output = tmp_path / "shadow-evidence" / "shadow-eval.json"
    exit_code = shadow_eval_cli_main(
        [
            "--snapshot",
            str(SNAPSHOT_PATH),
            "--output",
            str(output),
            "--fail-on-failed",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert payload["event_count"] == 6


def test_shadow_evaluation_harness_is_wired_into_docs_and_queue() -> None:
    docs_index = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    invariant_policy = (
        REPO_ROOT / "docs" / "policies" / "formal-safety-invariants.md"
    ).read_text(encoding="utf-8")
    queue = (REPO_ROOT / "docs" / "roadmap" / "scas-execution-queue.md").read_text(
        encoding="utf-8"
    )

    assert "shadow-evaluation-harness.md" in docs_index
    assert "shadow-evaluation-harness.md" in invariant_policy
    assert "FSG-12 Publish ADR for Formal Safety Guarantees" in queue
