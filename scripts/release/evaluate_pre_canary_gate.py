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


def evaluate(
    invariant_report: dict[str, Any],
    shadow_threshold_report: dict[str, Any],
) -> dict[str, Any]:
    failure_reasons: list[str] = []
    remediation_paths: list[str] = []

    invariant_status = str(invariant_report.get("status") or "").lower()
    invariant_mismatch_count = int(invariant_report.get("mismatch_count", 0))
    invariant_passed = invariant_status == "passed" and invariant_mismatch_count == 0

    if not invariant_passed:
        failure_reasons.append(
            "Invariant replay gate failed: status must be passed and mismatch_count must be 0."
        )
        remediation_paths.append(
            "Fix invariant replay mismatches and rerun "
            "`python scripts/runtime/invariant_check.py --print-json --output-json <path>`."
        )

    shadow_status = str(shadow_threshold_report.get("status") or "").lower()
    shadow_passed = shadow_status == "passed"
    threshold_failures: list[str] = []
    selection_failures: list[str] = []
    missing_threshold_types: list[str] = []

    threshold_checks = shadow_threshold_report.get("threshold_checks")
    if isinstance(threshold_checks, dict):
        for check_name, details in threshold_checks.items():
            if not isinstance(details, dict):
                continue
            if bool(details.get("passed")):
                continue
            threshold_failures.append(
                f"{check_name}: actual={details.get('actual')!r}, "
                f"threshold={details.get('threshold')!r}"
            )

    selection_checks = shadow_threshold_report.get("selection_checks")
    if isinstance(selection_checks, dict):
        for change_type, details in selection_checks.items():
            if not isinstance(details, dict):
                continue
            precision_passed = bool(details.get("precision_passed"))
            recall_passed = bool(details.get("recall_passed"))
            if precision_passed and recall_passed:
                continue
            selection_failures.append(
                f"{change_type}: precision_delta={details.get('precision_delta')!r} "
                f"(min={details.get('precision_delta_min')!r}), "
                f"recall_delta={details.get('recall_delta')!r} "
                f"(min={details.get('recall_delta_min')!r})"
            )

    missing = shadow_threshold_report.get("missing_explicit_threshold_change_types")
    if isinstance(missing, list):
        missing_threshold_types = [item for item in missing if isinstance(item, str)]

    if not shadow_passed:
        failure_reasons.append("Shadow regression threshold gate failed.")
        if threshold_failures:
            failure_reasons.append(
                "Threshold failures: " + "; ".join(threshold_failures)
            )
        if selection_failures:
            failure_reasons.append(
                "Selection drift failures: " + "; ".join(selection_failures)
            )
        if missing_threshold_types:
            failure_reasons.append(
                "Missing explicit thresholds for change types: "
                + ", ".join(sorted(missing_threshold_types))
            )
        remediation_paths.append(
            "Adjust `policies/runtime/shadow-regression-thresholds.json` and rerun "
            "`python scripts/operations/evaluate_shadow_regression_thresholds.py "
            "--policy <policy> --report <report> --fail-on-failed`."
        )

    overall_passed = invariant_passed and shadow_passed

    return {
        "status": "passed" if overall_passed else "failed",
        "gates": {
            "invariant_check": {
                "passed": invariant_passed,
                "status": invariant_status,
                "mismatch_count": invariant_mismatch_count,
            },
            "shadow_regression_thresholds": {
                "passed": shadow_passed,
                "status": shadow_status,
                "threshold_failures": threshold_failures,
                "selection_failures": selection_failures,
                "missing_explicit_threshold_change_types": missing_threshold_types,
            },
        },
        "failure_reasons": failure_reasons,
        "required_remediation_paths": remediation_paths,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the pre-canary safety gate by combining invariant-check "
            "and shadow-regression-threshold reports."
        ),
    )
    parser.add_argument("--invariant-report", type=Path, required=True)
    parser.add_argument("--shadow-threshold-report", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-failed", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = evaluate(
            load_json(args.invariant_report),
            load_json(args.shadow_threshold_report),
        )
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
