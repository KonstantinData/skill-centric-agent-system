from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.runtime.evaluate_intent_transition_traces import (  # noqa: E402
    DEFAULT_TRACES,
    evaluate_intent_transition_traces,
)

DEFAULT_POLICY = REPO_ROOT / "policies" / "runtime" / "intent-transition-shadow-thresholds.json"
DEFAULT_SCHEMA = REPO_ROOT / "schemas" / "intent-transition-shadow-thresholds.schema.json"


class IntentTransitionShadowMetricError(ValueError):
    """Raised when shadow metrics violate thresholds."""


def evaluate_shadow_metrics(
    *,
    policy: dict[str, Any],
    traces: dict[str, Any],
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    schema = _load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)

    trace_report = evaluate_intent_transition_traces(traces)
    case_count = int(trace_report["summary"]["case_count"])
    metrics = _metrics(trace_report, traces, case_count)
    violations = _threshold_violations(policy, metrics)
    report = {
        "policy_id": policy["policy_id"],
        "policy_version": policy["version"],
        "status": "passed" if not violations else "failed",
        "shadow_mode": policy["shadow_mode"],
        "metrics": metrics,
        "violations": violations,
        "source_trace_suite": traces["suite_id"],
    }
    if violations:
        raise IntentTransitionShadowMetricError(
            "intent-transition shadow metrics failed thresholds: "
            + "; ".join(violations)
        )
    return report


def assert_shadow_metrics_current(
    *,
    policy_path: Path = DEFAULT_POLICY,
    traces_path: Path = DEFAULT_TRACES,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    return evaluate_shadow_metrics(
        policy=_load_json(policy_path),
        traces=_load_json(traces_path),
        schema_path=schema_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate SCAS intent-transition shadow metrics.",
    )
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--traces", type=Path, default=DEFAULT_TRACES)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = assert_shadow_metrics_current(
            policy_path=args.policy,
            traces_path=args.traces,
            schema_path=args.schema,
        )
    except (OSError, json.JSONDecodeError, IntentTransitionShadowMetricError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1 if args.check else 2

    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True), end="\n")
    return 0


def _metrics(
    trace_report: dict[str, Any],
    traces: dict[str, Any],
    case_count: int,
) -> dict[str, float]:
    protected_cases = [
        case
        for case in trace_report["cases"]
        if case["expected_decision"] == "human_review_required"
    ]
    ambiguous_cases = [
        case
        for case in trace_report["cases"]
        if case["expected_decision"] == "clarification_required"
    ]
    protected_successes = sum(
        1 for case in protected_cases if case["actual_decision"] == "human_review_required"
    )
    unknown_blocks = sum(
        1 for case in ambiguous_cases if case["actual_decision"] == "clarification_required"
    )
    missed_protected_paths = _missed_protected_paths(trace_report, traces)

    return {
        "false_allow_rate": trace_report["summary"]["false_allow_count"] / case_count,
        "unnecessary_clarification_rate": (
            trace_report["summary"]["unnecessary_clarification_count"] / case_count
        ),
        "missed_protected_path_reference_rate": missed_protected_paths
        / max(len(protected_cases), 1),
        "evidence_coverage_rate": trace_report["summary"]["evidence_coverage_rate"],
        "unknown_to_block_conversion_rate": unknown_blocks / max(len(ambiguous_cases), 1),
        "protected_path_escalation_rate": protected_successes / max(len(protected_cases), 1),
    }


def _missed_protected_paths(trace_report: dict[str, Any], traces: dict[str, Any]) -> int:
    protected_case_ids = {
        case["case_id"]
        for case in traces["cases"]
        if any(
            signal["signal_kind"] == "protected_path_reference"
            for signal in case["expected_signals"]
        )
    }
    return sum(
        1
        for case in trace_report["cases"]
        if case["case_id"] in protected_case_ids and case["missed_expected_signals"]
    )


def _threshold_violations(policy: dict[str, Any], metrics: dict[str, float]) -> list[str]:
    violations: list[str] = []
    thresholds = policy["metrics"]
    for metric_name, metric_value in metrics.items():
        threshold = thresholds[metric_name]
        if "maximum" in threshold and metric_value > threshold["maximum"]:
            violations.append(
                f"{metric_name} {metric_value:.3f} exceeds maximum {threshold['maximum']:.3f}"
            )
        if "minimum" in threshold and metric_value < threshold["minimum"]:
            violations.append(
                f"{metric_name} {metric_value:.3f} below minimum {threshold['minimum']:.3f}"
            )
    return violations


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise IntentTransitionShadowMetricError(f"{path} must contain a JSON object")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
