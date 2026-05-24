"""Validate the versioned GitHub main-branch ruleset desired state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_RULE_TYPES = {
    "deletion",
    "non_fast_forward",
    "required_signatures",
    "pull_request",
    "required_status_checks",
}
REQUIRED_STATUS_CHECKS = {
    "Contract tests",
    "Cloudflare Worker",
    "Repository governance gates",
    "Secret scanning",
    "Dependency audit",
    "policy-as-code-gate",
    "dependency-review",
}


def load_ruleset(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rule_by_type(ruleset: dict[str, Any], rule_type: str) -> dict[str, Any] | None:
    for rule in ruleset.get("rules", []):
        if isinstance(rule, dict) and rule.get("type") == rule_type:
            return rule
    return None


def validate_ruleset(path: Path) -> list[str]:
    ruleset = load_ruleset(path)
    failures: list[str] = []

    if ruleset.get("name") != "main-protection":
        failures.append("ruleset name must be main-protection")
    if ruleset.get("target") != "branch":
        failures.append("ruleset target must be branch")
    if ruleset.get("enforcement") != "active":
        failures.append("ruleset enforcement must be active")

    include = ruleset.get("conditions", {}).get("ref_name", {}).get("include", [])
    if "~DEFAULT_BRANCH" not in include:
        failures.append("ruleset must include ~DEFAULT_BRANCH")

    rule_types = {rule.get("type") for rule in ruleset.get("rules", []) if isinstance(rule, dict)}
    missing_rules = REQUIRED_RULE_TYPES - rule_types
    if missing_rules:
        failures.append("ruleset missing rules: " + ", ".join(sorted(missing_rules)))

    pull_request = rule_by_type(ruleset, "pull_request") or {}
    pr_params = pull_request.get("parameters", {})
    if pr_params.get("required_approving_review_count", 0) < 2:
        failures.append("pull request rule must require at least two approvals")
    if pr_params.get("require_code_owner_review") is not True:
        failures.append("pull request rule must require code-owner review")
    if pr_params.get("required_review_thread_resolution") is not True:
        failures.append("pull request rule must require review thread resolution")

    status_checks = rule_by_type(ruleset, "required_status_checks") or {}
    status_params = status_checks.get("parameters", {})
    if status_params.get("strict_required_status_checks_policy") is not True:
        failures.append("required status checks must be strict")
    contexts = {
        item.get("context")
        for item in status_params.get("required_status_checks", [])
        if isinstance(item, dict)
    }
    missing_contexts = REQUIRED_STATUS_CHECKS - contexts
    if missing_contexts:
        failures.append("ruleset missing status checks: " + ", ".join(sorted(missing_contexts)))

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        type=Path,
        default=Path(".github/rulesets/main-protection.json"),
    )
    args = parser.parse_args()

    failures = validate_ruleset(args.path)
    if failures:
        print("Ruleset validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Ruleset validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
