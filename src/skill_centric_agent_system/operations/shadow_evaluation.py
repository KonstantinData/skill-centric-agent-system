"""Shadow-evaluate candidate descriptor/policy versions against trace snapshots."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class ShadowEvaluationError(ValueError):
    """Raised when shadow-evaluation input is malformed."""


def _as_bool(value: Any, field: str, errors: list[str], trace_id: str) -> bool:
    if not isinstance(value, bool):
        errors.append(f"{trace_id}: {field} must be a boolean.")
        return False
    return value


def _as_str(value: Any, field: str, errors: list[str], trace_id: str) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{trace_id}: {field} must be a non-empty string.")
        return ""
    return value


def _as_str_list(value: Any, field: str, errors: list[str], trace_id: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        errors.append(f"{trace_id}: {field} must be a list of strings.")
        return []
    return value


def evaluate_shadow_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    trace_events = snapshot.get("trace_events")
    if not isinstance(trace_events, list):
        raise ShadowEvaluationError("snapshot.trace_events must be a list.")

    errors: list[str] = []
    decision_changes = 0

    baseline_abstentions = 0
    candidate_abstentions = 0
    baseline_mixed_profile = 0
    candidate_mixed_profile = 0

    baseline_expected_safety = 0
    candidate_expected_safety = 0
    baseline_false_negatives = 0
    candidate_false_negatives = 0

    selection_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "baseline_tp": 0,
            "baseline_selected": 0,
            "baseline_expected": 0,
            "candidate_tp": 0,
            "candidate_selected": 0,
            "candidate_expected": 0,
        }
    )

    for index, event in enumerate(trace_events):
        trace_id = f"trace[{index}]"
        if isinstance(event, dict):
            trace_id = str(event.get("trace_id") or trace_id)
        else:
            errors.append(f"{trace_id}: event must be an object.")
            continue

        change_type = _as_str(event.get("change_type"), "change_type", errors, trace_id)
        expected_safety_violation = _as_bool(
            event.get("expected_safety_violation"),
            "expected_safety_violation",
            errors,
            trace_id,
        )
        expected_selection_ids = _as_str_list(
            event.get("expected_selection_ids"),
            "expected_selection_ids",
            errors,
            trace_id,
        )

        baseline = event.get("baseline")
        candidate = event.get("candidate")
        if not isinstance(baseline, dict):
            errors.append(f"{trace_id}: baseline must be an object.")
            baseline = {}
        if not isinstance(candidate, dict):
            errors.append(f"{trace_id}: candidate must be an object.")
            candidate = {}

        baseline_abstained = _as_bool(
            baseline.get("abstained"),
            "baseline.abstained",
            errors,
            trace_id,
        )
        candidate_abstained = _as_bool(
            candidate.get("abstained"),
            "candidate.abstained",
            errors,
            trace_id,
        )
        baseline_mixed = _as_bool(
            baseline.get("mixed_profile"),
            "baseline.mixed_profile",
            errors,
            trace_id,
        )
        candidate_mixed = _as_bool(
            candidate.get("mixed_profile"),
            "candidate.mixed_profile",
            errors,
            trace_id,
        )
        baseline_detected = _as_bool(
            baseline.get("safety_violation_detected"),
            "baseline.safety_violation_detected",
            errors,
            trace_id,
        )
        candidate_detected = _as_bool(
            candidate.get("safety_violation_detected"),
            "candidate.safety_violation_detected",
            errors,
            trace_id,
        )
        baseline_selected = _as_str_list(
            baseline.get("selected_module_ids"),
            "baseline.selected_module_ids",
            errors,
            trace_id,
        )
        candidate_selected = _as_str_list(
            candidate.get("selected_module_ids"),
            "candidate.selected_module_ids",
            errors,
            trace_id,
        )

        if baseline_abstained:
            baseline_abstentions += 1
        if candidate_abstained:
            candidate_abstentions += 1
        if baseline_mixed:
            baseline_mixed_profile += 1
        if candidate_mixed:
            candidate_mixed_profile += 1

        if expected_safety_violation:
            baseline_expected_safety += 1
            candidate_expected_safety += 1
            if not baseline_detected:
                baseline_false_negatives += 1
            if not candidate_detected:
                candidate_false_negatives += 1

        if change_type:
            expected_set = set(expected_selection_ids)
            baseline_set = set(baseline_selected)
            candidate_set = set(candidate_selected)

            stats = selection_stats[change_type]
            stats["baseline_tp"] += len(baseline_set & expected_set)
            stats["baseline_selected"] += len(baseline_set)
            stats["baseline_expected"] += len(expected_set)
            stats["candidate_tp"] += len(candidate_set & expected_set)
            stats["candidate_selected"] += len(candidate_set)
            stats["candidate_expected"] += len(expected_set)

        baseline_signature = (
            baseline_abstained,
            baseline_mixed,
            baseline_detected,
            tuple(sorted(set(baseline_selected))),
        )
        candidate_signature = (
            candidate_abstained,
            candidate_mixed,
            candidate_detected,
            tuple(sorted(set(candidate_selected))),
        )
        if baseline_signature != candidate_signature:
            decision_changes += 1

    event_count = len(trace_events)
    denominator = float(event_count) if event_count > 0 else 1.0

    def _rate(numerator: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return numerator / float(total)

    def _precision(tp: int, selected: int) -> float:
        if selected <= 0:
            return 1.0
        return tp / float(selected)

    def _recall(tp: int, expected: int) -> float:
        if expected <= 0:
            return 1.0
        return tp / float(expected)

    selection_drift_by_change_type: dict[str, dict[str, dict[str, float] | float]] = {}
    for change_type, stats in sorted(selection_stats.items()):
        baseline_precision = _precision(stats["baseline_tp"], stats["baseline_selected"])
        candidate_precision = _precision(stats["candidate_tp"], stats["candidate_selected"])
        baseline_recall = _recall(stats["baseline_tp"], stats["baseline_expected"])
        candidate_recall = _recall(stats["candidate_tp"], stats["candidate_expected"])
        selection_drift_by_change_type[change_type] = {
            "precision": {
                "baseline": baseline_precision,
                "candidate": candidate_precision,
                "delta": candidate_precision - baseline_precision,
            },
            "recall": {
                "baseline": baseline_recall,
                "candidate": candidate_recall,
                "delta": candidate_recall - baseline_recall,
            },
            "trace_count": stats["baseline_expected"],
        }

    baseline_abstention_rate = baseline_abstentions / denominator
    candidate_abstention_rate = candidate_abstentions / denominator
    baseline_mixed_rate = baseline_mixed_profile / denominator
    candidate_mixed_rate = candidate_mixed_profile / denominator

    baseline_safety_fn_rate = _rate(baseline_false_negatives, baseline_expected_safety)
    candidate_safety_fn_rate = _rate(candidate_false_negatives, candidate_expected_safety)

    return {
        "status": "failed" if errors else "passed",
        "snapshot_contract_version": snapshot.get("contract_version"),
        "baseline_versions": snapshot.get("baseline_versions", {}),
        "candidate_versions": snapshot.get("candidate_versions", {}),
        "event_count": event_count,
        "evaluation_error_count": len(errors),
        "evaluation_errors": errors,
        "metrics": {
            "decision_change_rate": decision_changes / denominator,
            "abstention_rate": {
                "baseline": baseline_abstention_rate,
                "candidate": candidate_abstention_rate,
                "delta": candidate_abstention_rate - baseline_abstention_rate,
            },
            "mixed_profile_rate": {
                "baseline": baseline_mixed_rate,
                "candidate": candidate_mixed_rate,
                "delta": candidate_mixed_rate - baseline_mixed_rate,
            },
            "safety_false_negative_rate": {
                "baseline": baseline_safety_fn_rate,
                "candidate": candidate_safety_fn_rate,
                "delta": candidate_safety_fn_rate - baseline_safety_fn_rate,
            },
            "selection_drift_by_change_type": selection_drift_by_change_type,
        },
    }
