from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scripts.runtime.evaluate_intent_transition_shadow_metrics import (
    _threshold_violations,
    assert_shadow_metrics_current,
)
from scripts.runtime.evaluate_intent_transition_shadow_metrics import (
    main as intent_transition_shadow_metrics_cli_main,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "policies" / "runtime" / "intent-transition-shadow-thresholds.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "intent-transition-shadow-thresholds.schema.json"
TRACES_PATH = REPO_ROOT / "examples" / "evaluations" / "intent-transition-golden-traces.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_intent_transition_shadow_thresholds_match_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    policy = load_json(POLICY_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)


def test_intent_transition_shadow_metrics_pass_current_thresholds() -> None:
    report = assert_shadow_metrics_current(
        policy_path=POLICY_PATH,
        traces_path=TRACES_PATH,
        schema_path=SCHEMA_PATH,
    )

    assert report["status"] == "passed"
    assert report["shadow_mode"]["can_compose_profiles"] is False
    assert report["shadow_mode"]["can_grant_capabilities"] is False
    assert report["metrics"]["false_allow_rate"] == 0
    assert report["metrics"]["evidence_coverage_rate"] == 1.0
    assert report["metrics"]["unknown_to_block_conversion_rate"] == 1.0
    assert report["metrics"]["protected_path_escalation_rate"] == 1.0


def test_intent_transition_shadow_metrics_reject_threshold_violation() -> None:
    policy = deepcopy(load_json(POLICY_PATH))
    metrics = {
        "false_allow_rate": 0.1,
        "unnecessary_clarification_rate": 0.0,
        "missed_protected_path_reference_rate": 0.0,
        "evidence_coverage_rate": 1.0,
        "unknown_to_block_conversion_rate": 1.0,
        "protected_path_escalation_rate": 1.0,
    }

    violations = _threshold_violations(policy, metrics)

    assert any("false_allow_rate" in violation for violation in violations)


def test_intent_transition_shadow_metrics_cli_check_passes() -> None:
    assert intent_transition_shadow_metrics_cli_main(["--check"]) == 0
