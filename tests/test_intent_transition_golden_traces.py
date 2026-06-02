from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from scripts.runtime.evaluate_intent_transition_traces import (
    IntentTransitionTraceError,
    assert_traces_current,
    evaluate_intent_transition_traces,
)
from scripts.runtime.evaluate_intent_transition_traces import (
    main as intent_transition_trace_cli_main,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TRACES_PATH = REPO_ROOT / "examples" / "evaluations" / "intent-transition-golden-traces.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_intent_transition_golden_traces_pass() -> None:
    report = assert_traces_current(TRACES_PATH)

    assert report["status"] == "passed"
    assert report["summary"]["case_count"] == 7
    assert report["summary"]["false_allow_count"] == 0
    assert report["summary"]["unnecessary_clarification_count"] == 0
    assert report["summary"]["missed_path_reference_count"] == 0
    assert report["summary"]["evidence_coverage_rate"] == 1.0


def test_intent_transition_golden_traces_cover_required_cases() -> None:
    traces = load_json(TRACES_PATH)
    case_ids = {case["case_id"] for case in traces["cases"]}

    assert {
        "research-to-research-safe",
        "research-to-task-execution-apply-fix",
        "read-only-to-write-capable",
        "protected-path-change",
        "destructive-request",
        "ambiguous-that-file",
        "ambiguous-safe-option",
    } <= case_ids


def test_intent_transition_golden_traces_include_metamorphic_apply_variants() -> None:
    traces = load_json(TRACES_PATH)
    apply_variants = {
        case["raw_turn"]
        for case in traces["cases"]
        if case.get("metamorphic_group") == "apply-fix"
    }

    assert "Apply the fix to src/foo.ts in this repo." in apply_variants
    assert "Apply that fix to that file." in apply_variants
    assert "Apply the safe option." in apply_variants


def test_intent_transition_golden_traces_reject_false_allow() -> None:
    traces = deepcopy(load_json(TRACES_PATH))
    case = next(c for c in traces["cases"] if c["case_id"] == "destructive-request")
    case["expected_decision"] = "allowed"

    with pytest.raises(IntentTransitionTraceError, match="expected decision"):
        evaluate_intent_transition_traces(traces)


def test_intent_transition_golden_trace_cli_check_passes() -> None:
    assert intent_transition_trace_cli_main(["--check"]) == 0
