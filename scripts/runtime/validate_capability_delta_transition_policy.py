from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

POLICY_VERSION = "0.1.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = REPO_ROOT / "policies" / "runtime" / "capability-delta-transition-policy.json"
DEFAULT_SCHEMA = REPO_ROOT / "schemas" / "capability-delta-transition-policy.schema.json"
MODULES_DIR = REPO_ROOT / "registry" / "modules"

REQUIRED_CAPABILITY_CLASSES = {
    "research",
    "read-only",
    "repo-read",
    "repo-write",
    "protected-path-write",
    "production-change",
    "secrets-sensitive",
    "unknown",
}
REQUIRED_RULE_IDS = {
    "research-to-research",
    "research-to-repo-write",
    "repo-read-to-repo-write",
    "repo-write-to-protected-path-write",
    "protected-path-write-to-production-change",
    "any-to-secrets-sensitive",
}
KNOWN_EVIDENCE_FIELDS = {
    "repository_bound",
    "explicit_write_intent",
    "explicit_destructive_intent",
    "protected_path_reference",
    "mentioned_paths",
    "scan_coverage",
    "raw_artifact_hash_verified",
    "previous_profile_authority_verified",
}
ESCALATION_DECISIONS = {
    "require_recomposition",
    "require_clarification",
    "require_human_review",
    "deny",
}


class CapabilityDeltaPolicyError(ValueError):
    """Raised when the capability-delta policy is invalid."""


def validate_capability_delta_policy(
    policy: Mapping[str, Any],
    *,
    schema_path: Path = DEFAULT_SCHEMA,
    modules_dir: Path = MODULES_DIR,
    today: date | None = None,
) -> dict[str, Any]:
    schema = _load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)

    violations = _policy_violations(policy, modules_dir=modules_dir, today=today or date.today())
    report = {
        "policy_version": POLICY_VERSION,
        "status": "passed" if not violations else "failed",
        "summary": {
            "capability_class_count": len(policy["capability_classes"]),
            "transition_rule_count": len(policy["transition_rules"]),
            "module_mapping_count": len(policy["module_capability_mappings"]),
            "scope_mapping_count": len(policy["scope_mappings"]),
            "exception_count": len(policy["exceptions"]),
        },
        "violations": violations,
    }
    if violations:
        raise CapabilityDeltaPolicyError(
            "capability-delta transition policy failed validation: "
            + "; ".join(violations)
        )
    return report


def assert_policy_current(
    *,
    policy_path: Path = DEFAULT_POLICY,
    schema_path: Path = DEFAULT_SCHEMA,
    modules_dir: Path = MODULES_DIR,
) -> dict[str, Any]:
    return validate_capability_delta_policy(
        _load_json(policy_path),
        schema_path=schema_path,
        modules_dir=modules_dir,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate SCAS capability-delta transition policy.",
    )
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--modules-dir", type=Path, default=MODULES_DIR)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = assert_policy_current(
            policy_path=args.policy,
            schema_path=args.schema,
            modules_dir=args.modules_dir,
        )
    except (OSError, json.JSONDecodeError, CapabilityDeltaPolicyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1 if args.check else 2

    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True), end="\n")
    return 0


def _policy_violations(
    policy: Mapping[str, Any],
    *,
    modules_dir: Path,
    today: date,
) -> list[str]:
    violations: list[str] = []
    capability_classes = set(policy["capability_classes"])

    if capability_classes != REQUIRED_CAPABILITY_CLASSES:
        violations.append("capability_classes must match transition-evidence capability classes")

    rule_ids = {str(rule["id"]) for rule in policy["transition_rules"]}
    missing_rules = REQUIRED_RULE_IDS - rule_ids
    if missing_rules:
        violations.append("missing transition rules: " + ", ".join(sorted(missing_rules)))

    for rule in policy["transition_rules"]:
        violations.extend(_transition_rule_violations(rule, capability_classes))

    violations.extend(_module_mapping_violations(policy, modules_dir))
    violations.extend(_exception_violations(policy, today))
    return violations


def _transition_rule_violations(
    rule: Mapping[str, Any],
    capability_classes: set[str],
) -> list[str]:
    violations: list[str] = []
    rule_id = str(rule["id"])
    from_classes = set(rule["from_capability_classes"])
    to_classes = set(rule["to_capability_classes"])
    evidence_fields = set(rule["required_evidence"])

    if not from_classes <= capability_classes:
        violations.append(f"{rule_id} uses unknown from_capability_classes")
    if not to_classes <= capability_classes:
        violations.append(f"{rule_id} uses unknown to_capability_classes")
    if not evidence_fields <= KNOWN_EVIDENCE_FIELDS:
        violations.append(f"{rule_id} uses unknown required_evidence fields")

    decision = str(rule["decision"])
    unknown_handling = str(rule["unknown_handling"])
    if decision in ESCALATION_DECISIONS and unknown_handling == "allow_only_when_no_escalation":
        violations.append(f"{rule_id} must fail closed or gate unknown escalation values")

    if decision in {"require_recomposition", "require_human_review"} and not rule[
        "requires_recomposition"
    ]:
        violations.append(f"{rule_id} must require recomposition")
    if decision == "require_human_review" and not rule["requires_human_review"]:
        violations.append(f"{rule_id} must require human review")
    if "repo-write" in to_classes and "explicit_write_intent" not in evidence_fields:
        violations.append(f"{rule_id} repo-write transition requires explicit_write_intent")
    if "protected-path-write" in to_classes and "protected_path_reference" not in evidence_fields:
        violations.append(f"{rule_id} protected-path transition requires protected_path_reference")
    if "production-change" in to_classes and "production_readiness" not in rule["required_gates"]:
        violations.append(f"{rule_id} production transition requires production_readiness gate")

    return violations


def _module_mapping_violations(policy: Mapping[str, Any], modules_dir: Path) -> list[str]:
    violations: list[str] = []
    module_mappings = policy["module_capability_mappings"]
    scope_mappings = policy["scope_mappings"]

    for module_path in sorted(modules_dir.rglob("module.json")):
        module = _load_json(module_path)
        if module.get("kind") != "skill":
            continue
        module_name = str(module["name"])
        capability_class = str(module["capability_class"])
        if capability_class not in module_mappings:
            violations.append(f"{module_name} capability_class {capability_class} is unmapped")
            continue
        if not module_mappings[capability_class]["transition_capability_classes"]:
            violations.append(f"{module_name} maps to no transition capability classes")
        for data_scope in module.get("data_scopes", []):
            if data_scope not in scope_mappings:
                violations.append(f"{module_name} data_scope {data_scope} is unmapped")
    return violations


def _exception_violations(policy: Mapping[str, Any], today: date) -> list[str]:
    violations: list[str] = []
    for exception in policy["exceptions"]:
        expires = date.fromisoformat(str(exception["expires"]))
        if expires < today:
            violations.append(f"{exception['id']} exception expired on {expires.isoformat()}")
    return violations


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise CapabilityDeltaPolicyError(f"{_repo_path(path)} must contain a JSON object")
    return parsed


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
