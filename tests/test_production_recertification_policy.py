from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from scripts.release.validate_production_recertification_policy import (
    RecertificationPolicyError,
    assert_policy_current,
    recertification_summary,
    validate_policy,
)
from scripts.release.validate_production_recertification_policy import (
    main as recertification_cli_main,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "policies" / "runtime" / "production-recertification-policy.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "production-recertification-policy.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_production_recertification_policy_matches_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    policy = load_json(POLICY_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)


def test_production_recertification_policy_is_current() -> None:
    report = assert_policy_current(policy_path=POLICY_PATH, schema_path=SCHEMA_PATH)

    assert report["status"] == "passed"
    assert report["summary"]["environment_count"] == 3
    assert report["summary"]["trigger_count"] == 10


def test_production_recertification_policy_requires_prod_certify_mode() -> None:
    policy = deepcopy(load_json(POLICY_PATH))
    prod = next(
        cadence
        for cadence in policy["environment_cadence"]
        if cadence["environment"] == "prod"
    )
    prod["required_certification_mode"] = "evidence-only"

    with pytest.raises(RecertificationPolicyError, match="prod"):
        validate_policy(policy, schema_path=SCHEMA_PATH)


def test_production_recertification_policy_requires_trigger_inventory() -> None:
    policy = deepcopy(load_json(POLICY_PATH))
    policy["mandatory_recertification_triggers"] = [
        trigger
        for trigger in policy["mandatory_recertification_triggers"]
        if trigger["id"] != "evidence_expired"
    ]

    with pytest.raises(RecertificationPolicyError, match="evidence_expired"):
        validate_policy(policy, schema_path=SCHEMA_PATH)


def test_recertification_summary_selects_target_environment() -> None:
    summary = recertification_summary(
        target_environment="prod",
        policy_path=POLICY_PATH,
        schema_path=SCHEMA_PATH,
    )

    assert summary["required_certification_mode"] == "certify"
    assert summary["max_evidence_age_days"] == 90
    assert summary["release_claim"] == "production-ready"


def test_production_recertification_policy_cli_check_passes() -> None:
    assert recertification_cli_main(["--check"]) == 0
