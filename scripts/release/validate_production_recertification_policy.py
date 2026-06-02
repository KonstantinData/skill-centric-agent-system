from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

CONTRACT_VERSION = "0.1.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = REPO_ROOT / "policies" / "runtime" / "production-recertification-policy.json"
DEFAULT_SCHEMA = REPO_ROOT / "schemas" / "production-recertification-policy.schema.json"

REQUIRED_ENVIRONMENTS = {
    "dev": {
        "max_evidence_age_days": 30,
        "required_certification_mode": "evidence-only",
        "release_claim": "initial-productive-core",
    },
    "staging": {
        "max_evidence_age_days": 45,
        "required_certification_mode": "certify",
        "release_claim": "staging-ready",
    },
    "prod": {
        "max_evidence_age_days": 90,
        "required_certification_mode": "certify",
        "release_claim": "production-ready",
    },
}
REQUIRED_TRIGGERS = {
    "release_scope_change",
    "target_environment_change",
    "runtime_or_control_plane_change",
    "production_skill_or_handler_change",
    "policy_schema_or_gate_change",
    "security_or_data_governance_change",
    "branch_protection_or_ci_change",
    "live_infrastructure_change",
    "incident_or_gate_failure",
    "evidence_expired",
}
REQUIRED_RELEASE_FIELDS = {
    "release_commit",
    "target_environment",
    "release_scope",
    "certification_mode",
    "gate_results",
    "external_evidence",
    "open_release_gaps",
    "waivers",
    "owner",
    "completed_at",
    "next_review_due_at",
    "recertification_triggers",
}
FORBIDDEN_EVIDENCE_CONTENT = {
    "secret_values",
    "private_keys",
    "bearer_tokens",
    "raw_runtime_traces",
    "raw_tool_outputs",
    "confidential_customer_data",
}
REQUIRED_WAIVER_FIELDS = {
    "gate",
    "risk",
    "owner",
    "expiry_condition",
    "compensating_control",
}


class RecertificationPolicyError(ValueError):
    """Raised when the production recertification policy is invalid."""


def validate_policy(
    policy: Mapping[str, Any],
    *,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    schema = _load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)

    violations = _policy_violations(policy)
    report = {
        "contract_version": CONTRACT_VERSION,
        "status": "passed" if not violations else "failed",
        "summary": {
            "environment_count": len(policy["environment_cadence"]),
            "trigger_count": len(policy["mandatory_recertification_triggers"]),
            "required_release_field_count": len(
                policy["release_decision_requirements"]["required_fields"]
            ),
        },
        "violations": violations,
    }
    if violations:
        raise RecertificationPolicyError(
            "production recertification policy failed validation: "
            + "; ".join(violations)
        )
    return report


def assert_policy_current(
    *,
    policy_path: Path = DEFAULT_POLICY,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    return validate_policy(_load_json(policy_path), schema_path=schema_path)


def recertification_summary(
    *,
    target_environment: str,
    policy_path: Path = DEFAULT_POLICY,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    policy = _load_json(policy_path)
    validate_policy(policy, schema_path=schema_path)
    cadence = _cadence_for_environment(policy, target_environment)
    triggers = [
        {
            "id": str(trigger["id"]),
            "scope": str(trigger["scope"]),
            "required_action": str(trigger["required_action"]),
        }
        for trigger in policy["mandatory_recertification_triggers"]
    ]
    return {
        "policy_id": policy["policy_id"],
        "contract_version": policy["contract_version"],
        "status": policy["status"],
        "required_certification_mode": cadence["required_certification_mode"],
        "max_evidence_age_days": cadence["max_evidence_age_days"],
        "recertification_cadence": cadence["recertification_cadence"],
        "release_claim": cadence["release_claim"],
        "next_review_anchor": cadence["next_review_anchor"],
        "mandatory_triggers": triggers,
        "stale_evidence_outcome": policy["release_decision_requirements"][
            "stale_evidence_outcome"
        ],
        "waiver_max_duration_days": policy["waiver_policy"]["max_duration_days"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the SCAS production recertification policy.",
    )
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = assert_policy_current(policy_path=args.policy, schema_path=args.schema)
    except (OSError, json.JSONDecodeError, RecertificationPolicyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1 if args.check else 2

    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True), end="\n")
    return 0


def _policy_violations(policy: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []

    cadences = list(policy["environment_cadence"])
    environments = [str(cadence["environment"]) for cadence in cadences]
    duplicate_environments = sorted(
        {environment for environment in environments if environments.count(environment) > 1}
    )
    missing_environments = set(REQUIRED_ENVIRONMENTS) - set(environments)
    unexpected_environments = set(environments) - set(REQUIRED_ENVIRONMENTS)
    if duplicate_environments:
        violations.append(
            "duplicate environment cadence entries: "
            + ", ".join(duplicate_environments)
        )
    if missing_environments:
        violations.append(
            "missing environment cadence entries: "
            + ", ".join(sorted(missing_environments))
        )
    if unexpected_environments:
        violations.append(
            "unexpected environment cadence entries: "
            + ", ".join(sorted(unexpected_environments))
        )

    for cadence in cadences:
        environment = str(cadence["environment"])
        expected = REQUIRED_ENVIRONMENTS.get(environment)
        if expected is None:
            continue
        for field, expected_value in expected.items():
            if cadence[field] != expected_value:
                violations.append(
                    f"{environment} {field} must be {expected_value!r}, "
                    f"got {cadence[field]!r}"
                )

    trigger_ids = [
        str(trigger["id"]) for trigger in policy["mandatory_recertification_triggers"]
    ]
    duplicate_triggers = sorted(
        {trigger_id for trigger_id in trigger_ids if trigger_ids.count(trigger_id) > 1}
    )
    missing_triggers = REQUIRED_TRIGGERS - set(trigger_ids)
    unexpected_triggers = set(trigger_ids) - REQUIRED_TRIGGERS
    if duplicate_triggers:
        violations.append(
            "duplicate recertification triggers: " + ", ".join(duplicate_triggers)
        )
    if missing_triggers:
        violations.append(
            "missing recertification triggers: " + ", ".join(sorted(missing_triggers))
        )
    if unexpected_triggers:
        violations.append(
            "unexpected recertification triggers: "
            + ", ".join(sorted(unexpected_triggers))
        )
    for trigger in policy["mandatory_recertification_triggers"]:
        if trigger["required_action"] != "rerun_production_readiness_evidence":
            violations.append(f"{trigger['id']} must rerun production readiness evidence")
        if not trigger["evidence_required"]:
            violations.append(f"{trigger['id']} must require evidence")

    release_requirements = policy["release_decision_requirements"]
    release_fields = set(release_requirements["required_fields"])
    missing_release_fields = REQUIRED_RELEASE_FIELDS - release_fields
    if missing_release_fields:
        violations.append(
            "missing release decision fields: "
            + ", ".join(sorted(missing_release_fields))
        )

    forbidden_content = set(release_requirements["forbidden_evidence_content"])
    missing_forbidden_content = FORBIDDEN_EVIDENCE_CONTENT - forbidden_content
    if missing_forbidden_content:
        violations.append(
            "missing forbidden evidence content: "
            + ", ".join(sorted(missing_forbidden_content))
        )

    waiver_policy = policy["waiver_policy"]
    waiver_fields = set(waiver_policy["required_fields"])
    missing_waiver_fields = REQUIRED_WAIVER_FIELDS - waiver_fields
    if missing_waiver_fields:
        violations.append(
            "missing waiver fields: " + ", ".join(sorted(missing_waiver_fields))
        )
    if int(waiver_policy["max_duration_days"]) > 14:
        violations.append("waiver max_duration_days must be 14 or less")
    if "missing_production_readiness_evidence" not in waiver_policy["forbidden_for"]:
        violations.append("waivers must be forbidden for missing production evidence")

    return violations


def _cadence_for_environment(
    policy: Mapping[str, Any],
    target_environment: str,
) -> Mapping[str, Any]:
    for cadence in policy["environment_cadence"]:
        if cadence["environment"] == target_environment:
            return cadence
    raise RecertificationPolicyError(
        f"missing recertification cadence for target environment {target_environment!r}"
    )


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise RecertificationPolicyError(f"{_repo_path(path)} must contain a JSON object")
    return parsed


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
