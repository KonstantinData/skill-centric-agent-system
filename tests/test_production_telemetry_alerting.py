from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scripts.operations.evaluate_telemetry_alerts import main as telemetry_cli_main
from skill_centric_agent_system.operations import evaluate_telemetry_snapshot

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_SCHEMA_PATH = REPO_ROOT / "schemas" / "production-telemetry-policy.schema.json"
SNAPSHOT_SCHEMA_PATH = REPO_ROOT / "schemas" / "production-telemetry-snapshot.schema.json"
POLICY_PATH = REPO_ROOT / "examples" / "operations" / "production-telemetry-policy.json"
SNAPSHOT_PATH = REPO_ROOT / "examples" / "operations" / "production-telemetry-snapshot.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_production_telemetry_policy_and_snapshot_match_schemas() -> None:
    policy_schema = load_json(POLICY_SCHEMA_PATH)
    snapshot_schema = load_json(SNAPSHOT_SCHEMA_PATH)

    Draft202012Validator.check_schema(policy_schema)
    Draft202012Validator.check_schema(snapshot_schema)
    Draft202012Validator(policy_schema).validate(load_json(POLICY_PATH))
    Draft202012Validator(snapshot_schema).validate(load_json(SNAPSHOT_PATH))


def test_telemetry_evaluator_passes_clean_snapshot() -> None:
    result = evaluate_telemetry_snapshot(
        load_json(POLICY_PATH),
        load_json(SNAPSHOT_PATH),
        evaluated_at="2026-05-24T18:30:00Z",
    )

    assert result["status"] == "passed"
    assert result["alerts"] == []
    assert result["raw_data_policy"] == "aggregate_metadata_only"
    assert "runtime.failure_rate" in result["signals_evaluated"]


def test_telemetry_evaluator_emits_critical_alert_for_threshold_breach() -> None:
    snapshot = deepcopy(load_json(SNAPSHOT_PATH))
    snapshot["signals"]["runtime.failure_rate"]["value"] = 0.08

    result = evaluate_telemetry_snapshot(load_json(POLICY_PATH), snapshot)

    assert result["status"] == "critical"
    alert = result["alerts"][0]
    assert alert["rule_id"] == "runtime-failure-rate-critical"
    assert alert["severity"] == "critical"
    assert alert["value"] == 0.08
    assert alert["runbook"] == "docs/runbooks/operations-runbook.md#telemetry-alerts"


def test_telemetry_evaluator_fails_closed_on_missing_required_signal() -> None:
    snapshot = deepcopy(load_json(SNAPSHOT_PATH))
    del snapshot["signals"]["control.ai_gateway_error_rate"]

    result = evaluate_telemetry_snapshot(load_json(POLICY_PATH), snapshot)

    assert result["status"] == "critical"
    assert any(
        alert["rule_id"] == "ai-gateway-error-rate-critical"
        and alert["operator"] == "exists"
        for alert in result["alerts"]
    )


def test_telemetry_cli_writes_evidence_and_fails_on_alert(tmp_path: Path) -> None:
    snapshot = deepcopy(load_json(SNAPSHOT_PATH))
    snapshot["signals"]["runtime.retention_cleanup_missing_count"]["value"] = 2
    snapshot_path = tmp_path / "snapshot.json"
    output_path = tmp_path / "telemetry-alerts.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

    exit_code = telemetry_cli_main(
        [
            "--policy",
            str(POLICY_PATH),
            "--snapshot",
            str(snapshot_path),
            "--output",
            str(output_path),
            "--fail-on-alert",
        ]
    )

    assert exit_code == 1
    result = load_json(output_path)
    assert result["status"] == "warning"
    assert result["alerts"][0]["rule_id"] == "retention-cleanup-missing-count-warning"

