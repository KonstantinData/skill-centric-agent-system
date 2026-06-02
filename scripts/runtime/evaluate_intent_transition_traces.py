from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.runtime.scan_transition_signals import scan_transition_signals  # noqa: E402

DEFAULT_TRACES = REPO_ROOT / "examples" / "evaluations" / "intent-transition-golden-traces.json"


class IntentTransitionTraceError(ValueError):
    """Raised when intent-transition golden trace evaluation fails."""


def evaluate_intent_transition_traces(
    traces: Mapping[str, Any],
) -> dict[str, Any]:
    cases = []
    false_allow_count = 0
    unnecessary_clarification_count = 0
    missed_path_reference_count = 0
    expected_signal_count = 0
    matched_signal_count = 0
    failed_cases: list[str] = []

    for case in traces["cases"]:
        signals = [
            signal.to_dict()
            for signal in scan_transition_signals(
                artifact_id=f"turn-{case['case_id']}",
                text=str(case["raw_turn"]),
            )
        ]
        actual_decision = _decide(case, signals)
        expected_decision = str(case["expected_decision"])
        matched_signals, missed_signals = _signal_coverage(case["expected_signals"], signals)

        expected_signal_count += len(case["expected_signals"])
        matched_signal_count += matched_signals
        if expected_decision != "allowed" and actual_decision == "allowed":
            false_allow_count += 1
        if (
            expected_decision != "clarification_required"
            and actual_decision == "clarification_required"
        ):
            unnecessary_clarification_count += 1
        missed_path_reference_count += sum(
            1 for signal in missed_signals if signal["signal_kind"] == "path_reference"
        )

        failures = []
        if actual_decision != expected_decision:
            failures.append(
                f"expected decision {expected_decision}, got {actual_decision}"
            )
        if missed_signals:
            failures.append(
                "missed expected signals: "
                + ", ".join(_signal_label(s) for s in missed_signals)
            )
        if failures:
            failed_cases.append(f"{case['case_id']}: " + "; ".join(failures))

        cases.append(
            {
                "case_id": case["case_id"],
                "expected_decision": expected_decision,
                "actual_decision": actual_decision,
                "metamorphic_group": case.get("metamorphic_group"),
                "signal_count": len(signals),
                "matched_expected_signals": matched_signals,
                "missed_expected_signals": missed_signals,
            }
        )

    evidence_coverage_rate = (
        1.0 if expected_signal_count == 0 else matched_signal_count / expected_signal_count
    )
    report = {
        "suite_id": traces["suite_id"],
        "version": traces["version"],
        "status": "passed" if not failed_cases else "failed",
        "summary": {
            "case_count": len(traces["cases"]),
            "false_allow_count": false_allow_count,
            "unnecessary_clarification_count": unnecessary_clarification_count,
            "missed_path_reference_count": missed_path_reference_count,
            "evidence_coverage_rate": evidence_coverage_rate,
        },
        "failed_cases": failed_cases,
        "cases": cases,
    }
    if failed_cases:
        raise IntentTransitionTraceError(
            "intent-transition golden traces failed: " + "; ".join(failed_cases)
        )
    return report


def assert_traces_current(traces_path: Path = DEFAULT_TRACES) -> dict[str, Any]:
    return evaluate_intent_transition_traces(_load_json(traces_path))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate SCAS intent-transition golden traces.",
    )
    parser.add_argument("--traces", type=Path, default=DEFAULT_TRACES)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = assert_traces_current(args.traces)
    except (OSError, json.JSONDecodeError, IntentTransitionTraceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1 if args.check else 2

    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True), end="\n")
    return 0


def _decide(case: Mapping[str, Any], signals: Iterable[Mapping[str, Any]]) -> str:
    requested = set(str(item) for item in case["requested_capability_classes"])
    signal_kinds = {str(signal["signal_kind"]) for signal in signals}

    if "destructive_intent" in signal_kinds:
        return "human_review_required"
    if "protected-path-write" in requested or "protected_path_reference" in signal_kinds:
        return "human_review_required"
    if "repo-write" in requested:
        if "write_intent" not in signal_kinds:
            return "clarification_required"
        if "path_reference" not in signal_kinds or "repository_reference" not in signal_kinds:
            return "clarification_required"
        return "recomposition_required"
    return "allowed"


def _signal_coverage(
    expected_signals: Iterable[Mapping[str, Any]],
    actual_signals: Iterable[Mapping[str, Any]],
) -> tuple[int, list[Mapping[str, Any]]]:
    actual = list(actual_signals)
    matched = 0
    missed = []
    for expected in expected_signals:
        if any(
            signal["signal_kind"] == expected["signal_kind"]
            and signal["span"] == expected["span"]
            for signal in actual
        ):
            matched += 1
        else:
            missed.append(expected)
    return matched, missed


def _signal_label(signal: Mapping[str, Any]) -> str:
    return f"{signal['signal_kind']} {signal['span']!r}"


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise IntentTransitionTraceError(f"{path} must contain a JSON object")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
