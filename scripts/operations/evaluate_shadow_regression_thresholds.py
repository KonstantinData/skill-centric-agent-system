from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _require_number(value: Any, field: str) -> float:
    if not isinstance(value, int | float):
        raise ValueError(f"{field} must be numeric.")
    return float(value)


def evaluate(policy: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    thresholds = policy.get("delta_thresholds")
    if not isinstance(thresholds, dict):
        raise ValueError("policy.delta_thresholds must be an object.")

    drift_policy = policy.get("selection_drift_policy")
    if not isinstance(drift_policy, dict):
        raise ValueError("policy.selection_drift_policy must be an object.")

    metrics = report.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError("shadow report metrics must be an object.")

    abstention = metrics.get("abstention_rate")
    mixed_profile = metrics.get("mixed_profile_rate")
    safety_false_negative = metrics.get("safety_false_negative_rate")
    selection_drift = metrics.get("selection_drift_by_change_type")

    if not isinstance(abstention, dict):
        raise ValueError("metrics.abstention_rate must be an object.")
    if not isinstance(mixed_profile, dict):
        raise ValueError("metrics.mixed_profile_rate must be an object.")
    if not isinstance(safety_false_negative, dict):
        raise ValueError("metrics.safety_false_negative_rate must be an object.")
    if not isinstance(selection_drift, dict):
        raise ValueError("metrics.selection_drift_by_change_type must be an object.")

    abstention_delta = _require_number(abstention.get("delta"), "abstention delta")
    mixed_delta = _require_number(mixed_profile.get("delta"), "mixed profile delta")
    safety_delta = _require_number(
        safety_false_negative.get("delta"),
        "safety false-negative delta",
    )
    decision_change_rate = _require_number(
        metrics.get("decision_change_rate"),
        "decision_change_rate",
    )

    threshold_checks = {
        "abstention_delta_max_abs": {
            "actual": abs(abstention_delta),
            "threshold": _require_number(
                thresholds.get("abstention_delta_max_abs"),
                "abstention_delta_max_abs",
            ),
        },
        "mixed_profile_rate_delta_max_abs": {
            "actual": abs(mixed_delta),
            "threshold": _require_number(
                thresholds.get("mixed_profile_rate_delta_max_abs"),
                "mixed_profile_rate_delta_max_abs",
            ),
        },
        "safety_false_negative_delta_max": {
            "actual": safety_delta,
            "threshold": _require_number(
                thresholds.get("safety_false_negative_delta_max"),
                "safety_false_negative_delta_max",
            ),
        },
        "decision_change_rate_max": {
            "actual": decision_change_rate,
            "threshold": _require_number(
                thresholds.get("decision_change_rate_max"),
                "decision_change_rate_max",
            ),
        },
    }

    for check in threshold_checks.values():
        check["passed"] = bool(check["actual"] <= check["threshold"])

    default_thresholds = drift_policy.get("default_thresholds")
    if not isinstance(default_thresholds, dict):
        raise ValueError("selection_drift_policy.default_thresholds must be an object.")
    per_change_thresholds = drift_policy.get("by_change_type")
    if not isinstance(per_change_thresholds, dict):
        raise ValueError("selection_drift_policy.by_change_type must be an object.")
    fail_closed = bool(drift_policy.get("fail_closed_on_missing_change_type", True))

    selection_checks: dict[str, Any] = {}
    missing_threshold_change_types: list[str] = []

    for change_type, drift_values in sorted(selection_drift.items()):
        if not isinstance(drift_values, dict):
            raise ValueError(f"{change_type} drift values must be an object.")
        precision = drift_values.get("precision")
        recall = drift_values.get("recall")
        if not isinstance(precision, dict) or not isinstance(recall, dict):
            raise ValueError(f"{change_type} precision/recall must be objects.")

        configured_thresholds = per_change_thresholds.get(change_type, default_thresholds)
        if change_type not in per_change_thresholds and fail_closed:
            missing_threshold_change_types.append(change_type)
        if not isinstance(configured_thresholds, dict):
            raise ValueError(f"{change_type} thresholds must be an object.")

        precision_delta_min = _require_number(
            configured_thresholds.get("precision_delta_min"),
            f"{change_type} precision_delta_min",
        )
        recall_delta_min = _require_number(
            configured_thresholds.get("recall_delta_min"),
            f"{change_type} recall_delta_min",
        )
        precision_delta = _require_number(
            precision.get("delta"),
            f"{change_type} precision delta",
        )
        recall_delta = _require_number(recall.get("delta"), f"{change_type} recall delta")

        selection_checks[change_type] = {
            "precision_delta": precision_delta,
            "precision_delta_min": precision_delta_min,
            "precision_passed": precision_delta >= precision_delta_min,
            "recall_delta": recall_delta,
            "recall_delta_min": recall_delta_min,
            "recall_passed": recall_delta >= recall_delta_min,
            "threshold_source": "by_change_type"
            if change_type in per_change_thresholds
            else "default_thresholds",
        }

    if missing_threshold_change_types:
        for change_type in missing_threshold_change_types:
            selection_checks[change_type]["missing_explicit_threshold"] = True

    selection_passed = all(
        check["precision_passed"] and check["recall_passed"]
        for check in selection_checks.values()
    )
    threshold_passed = all(
        bool(check["passed"]) for check in threshold_checks.values()
    )
    missing_thresholds_passed = not missing_threshold_change_types
    overall_passed = threshold_passed and selection_passed and missing_thresholds_passed

    return {
        "status": "passed" if overall_passed else "failed",
        "threshold_checks": threshold_checks,
        "selection_checks": selection_checks,
        "missing_explicit_threshold_change_types": missing_threshold_change_types,
        "summary": {
            "threshold_passed": threshold_passed,
            "selection_passed": selection_passed,
            "missing_thresholds_passed": missing_thresholds_passed,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate shadow regression thresholds against a shadow report.",
    )
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-failed", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = evaluate(load_json(args.policy), load_json(args.report))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")

    if args.fail_on_failed and result["status"] != "passed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
