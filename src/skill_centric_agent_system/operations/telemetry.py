from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

CONTRACT_VERSION = "0.1.0"
SEVERITY_RANK = {"info": 0, "warning": 1, "critical": 2}


class TelemetryEvaluationError(ValueError):
    """Raised when telemetry policy or snapshot data is not evaluable."""


def evaluate_telemetry_snapshot(
    policy: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    *,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """Evaluate aggregate telemetry signals against alert rules."""

    policy_environment = _required_string(policy, "environment")
    snapshot_environment = _required_string(snapshot, "environment")
    if policy_environment != snapshot_environment:
        raise TelemetryEvaluationError(
            f"Telemetry policy environment {policy_environment!r} does not match "
            f"snapshot environment {snapshot_environment!r}."
        )

    signals = snapshot.get("signals")
    if not isinstance(signals, Mapping):
        raise TelemetryEvaluationError("Telemetry snapshot must include signals object.")

    alerts: list[dict[str, Any]] = []
    rules = policy.get("rules")
    if not isinstance(rules, list) or not rules:
        raise TelemetryEvaluationError("Telemetry policy must include at least one rule.")

    for rule in rules:
        if not isinstance(rule, Mapping):
            raise TelemetryEvaluationError("Telemetry rule must be an object.")
        signal_name = _required_string(rule, "signal")
        signal = signals.get(signal_name)
        if not isinstance(signal, Mapping):
            missing_severity = str(rule.get("missing_data_severity", "critical"))
            alerts.append(_missing_signal_alert(rule, missing_severity))
            continue

        value = signal.get("value")
        if not isinstance(value, int | float):
            raise TelemetryEvaluationError(
                f"Telemetry signal {signal_name!r} requires numeric value."
            )

        threshold = rule.get("threshold")
        if not isinstance(threshold, int | float):
            raise TelemetryEvaluationError(
                f"Telemetry rule {rule.get('id')!r} requires numeric threshold."
            )

        operator = _required_string(rule, "operator")
        if _compare(float(value), operator, float(threshold)):
            alerts.append(_threshold_alert(rule, signal, float(value), float(threshold)))

    status = _status_from_alerts(alerts)
    return {
        "contract_version": CONTRACT_VERSION,
        "policy_id": _required_string(policy, "policy_id"),
        "policy_version": _required_string(policy, "version"),
        "environment": policy_environment,
        "evaluated_at": evaluated_at or datetime.now(UTC).isoformat(),
        "status": status,
        "alerts": alerts,
        "signals_evaluated": sorted(str(name) for name in signals),
        "raw_data_policy": "aggregate_metadata_only",
    }


def _threshold_alert(
    rule: Mapping[str, Any],
    signal: Mapping[str, Any],
    value: float,
    threshold: float,
) -> dict[str, Any]:
    return {
        "rule_id": _required_string(rule, "id"),
        "severity": _required_string(rule, "severity"),
        "plane": _required_string(rule, "plane"),
        "signal": _required_string(rule, "signal"),
        "operator": _required_string(rule, "operator"),
        "threshold": threshold,
        "value": value,
        "unit": str(signal.get("unit") or rule.get("unit") or ""),
        "window": _required_string(rule, "window"),
        "source": _required_string(rule, "source"),
        "runbook": _required_string(rule, "runbook"),
        "message": _required_string(rule, "description"),
    }


def _missing_signal_alert(rule: Mapping[str, Any], severity: str) -> dict[str, Any]:
    return {
        "rule_id": _required_string(rule, "id"),
        "severity": severity,
        "plane": _required_string(rule, "plane"),
        "signal": _required_string(rule, "signal"),
        "operator": "exists",
        "threshold": None,
        "value": None,
        "unit": str(rule.get("unit") or ""),
        "window": _required_string(rule, "window"),
        "source": _required_string(rule, "source"),
        "runbook": _required_string(rule, "runbook"),
        "message": f"Telemetry signal is missing: {_required_string(rule, 'signal')}.",
    }


def _status_from_alerts(alerts: list[dict[str, Any]]) -> str:
    max_rank = max(
        (SEVERITY_RANK.get(str(alert.get("severity")), 2) for alert in alerts),
        default=0,
    )
    if max_rank >= SEVERITY_RANK["critical"]:
        return "critical"
    if max_rank >= SEVERITY_RANK["warning"]:
        return "warning"
    return "passed"


def _compare(value: float, operator: str, threshold: float) -> bool:
    if operator == ">=":
        return value >= threshold
    if operator == ">":
        return value > threshold
    if operator == "<=":
        return value <= threshold
    if operator == "<":
        return value < threshold
    if operator == "==":
        return value == threshold
    raise TelemetryEvaluationError(f"Unsupported telemetry operator: {operator}")


def _required_string(data: Mapping[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value:
        raise TelemetryEvaluationError(f"Telemetry data requires string field: {field}")
    return value
