"""Validate the versioned GitHub main-branch ruleset desired state."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY = "KonstantinData/skill-centric-agent-system"
RULESET_NAME = "main-protection"
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
    "analyze",
}
DRIFT_CONTRACT_VERSION = "0.1.0"


@dataclass(frozen=True)
class DriftFinding:
    field: str
    desired: object
    live: object
    severity: str
    confidence: str
    remediation_class: str
    recommended_action: str

    def as_dict(self) -> dict[str, object]:
        return {
            "field": self.field,
            "desired": self.desired,
            "live": self.live,
            "severity": self.severity,
            "confidence": self.confidence,
            "remediation_class": self.remediation_class,
            "recommended_action": self.recommended_action,
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

    if ruleset.get("name") != RULESET_NAME:
        failures.append(f"ruleset name must be {RULESET_NAME}")
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
    if pr_params.get("required_approving_review_count", 0) < 1:
        failures.append("pull request rule must require at least one approval")
    if pr_params.get("require_code_owner_review") is not False:
        failures.append("pull request rule must disable code-owner review")
    if pr_params.get("require_last_push_approval") is not False:
        failures.append("pull request rule must not require last-push approval")
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


def compare_rulesets(
    desired: dict[str, Any],
    live: dict[str, Any],
) -> list[DriftFinding]:
    findings: list[DriftFinding] = []

    for field in ("name", "target", "enforcement", "conditions"):
        if desired.get(field) != live.get(field):
            findings.append(
                DriftFinding(
                    field=field,
                    desired=desired.get(field),
                    live=live.get(field),
                    severity="high" if field == "enforcement" else "medium",
                    confidence="confirmed",
                    remediation_class="manual_github_fix",
                    recommended_action=(
                        "Update the live GitHub ruleset to match the versioned "
                        "desired-state file, or change the desired state by PR if the "
                        "live value is intentionally stronger."
                    ),
                )
            )

    desired_rule_types = _rule_types(desired)
    live_rule_types = _rule_types(live)
    missing_live_rules = sorted(desired_rule_types - live_rule_types)
    extra_live_rules = sorted(live_rule_types - desired_rule_types)
    if missing_live_rules:
        findings.append(
            DriftFinding(
                field="rules.types",
                desired=sorted(desired_rule_types),
                live=sorted(live_rule_types),
                severity="critical",
                confidence="confirmed",
                remediation_class="manual_github_fix",
                recommended_action=(
                    "Restore missing live branch-protection rules: "
                    + ", ".join(missing_live_rules)
                ),
            )
        )
    if extra_live_rules:
        findings.append(
            DriftFinding(
                field="rules.types.extra",
                desired=sorted(desired_rule_types),
                live=sorted(live_rule_types),
                severity="low",
                confidence="confirmed",
                remediation_class="repo_pr_fix",
                recommended_action=(
                    "Review extra live rules and either record them in desired state "
                    "or remove them manually if they are unintended."
                ),
            )
        )

    findings.extend(_compare_pull_request_rule(desired, live))
    findings.extend(_compare_required_status_checks(desired, live))
    return findings


def build_drift_evidence(
    *,
    desired: dict[str, Any],
    live: dict[str, Any] | None,
    findings: list[DriftFinding],
    repository: str = REPOSITORY,
    source: str,
    error: str | None = None,
) -> dict[str, object]:
    if error:
        status = "permission_missing" if _looks_like_permission_error(error) else "failed"
        confidence = "permission_missing" if status == "permission_missing" else "partial"
        evidence_findings: list[dict[str, object]] = [
            DriftFinding(
                field="github.ruleset.live_fetch",
                desired=desired.get("name"),
                live=None,
                severity="high",
                confidence=confidence,
                remediation_class="permission_setup",
                recommended_action=(
                    "Configure a read-only GitHub App or token with repository "
                    "Administration: read permission for live governance drift detection."
                ),
            ).as_dict()
        ]
    else:
        status = "passed" if not findings else "failed"
        evidence_findings = [finding.as_dict() for finding in findings]

    return {
        "contract_version": DRIFT_CONTRACT_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "repository": repository,
        "ruleset_name": desired.get("name", RULESET_NAME),
        "source": source,
        "status": status,
        "summary": {
            "finding_count": len(evidence_findings),
            "critical_count": sum(
                1 for finding in evidence_findings if finding["severity"] == "critical"
            ),
            "high_count": sum(
                1 for finding in evidence_findings if finding["severity"] == "high"
            ),
        },
        "desired": _ruleset_summary(desired),
        "live": _ruleset_summary(live) if live is not None else None,
        "findings": evidence_findings,
    }


def fetch_live_ruleset(
    *,
    repository: str = REPOSITORY,
    ruleset_name: str = RULESET_NAME,
) -> dict[str, Any]:
    list_result = _run_gh_api(f"repos/{repository}/rulesets")
    rulesets = json.loads(list_result.stdout)
    if not isinstance(rulesets, list):
        raise RuntimeError("GitHub rulesets API returned a non-list response")

    ruleset_id = None
    for ruleset in rulesets:
        if isinstance(ruleset, dict) and ruleset.get("name") == ruleset_name:
            ruleset_id = ruleset.get("id")
            break
    if ruleset_id is None:
        raise RuntimeError(f"live GitHub ruleset not found: {ruleset_name}")

    detail_result = _run_gh_api(f"repos/{repository}/rulesets/{ruleset_id}")
    parsed = json.loads(detail_result.stdout)
    if not isinstance(parsed, dict):
        raise RuntimeError("GitHub ruleset detail API returned a non-object response")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        type=Path,
        default=Path(".github/rulesets/main-protection.json"),
    )
    parser.add_argument("--live-path", type=Path)
    parser.add_argument("--fetch-live", action="store_true")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", REPOSITORY))
    parser.add_argument("--ruleset-name", default=RULESET_NAME)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()

    desired = load_ruleset(args.path)
    failures = validate_ruleset(args.path)
    if failures:
        print("Ruleset validation failed:")
        for failure in failures:
            print(f"- {failure}")
        if args.output_json:
            evidence = build_drift_evidence(
                desired=desired,
                live=None,
                findings=[],
                repository=args.repository,
                source="local",
                error="local desired-state validation failed: " + "; ".join(failures),
            )
            _write_json(args.output_json, evidence)
        return 1

    live: dict[str, Any] | None = None
    source = "local"
    live_error: str | None = None
    if args.live_path is not None:
        live = load_ruleset(args.live_path)
        source = "fixture"
    elif args.fetch_live:
        source = "github-api"
        try:
            live = fetch_live_ruleset(
                repository=args.repository,
                ruleset_name=args.ruleset_name,
            )
        except (OSError, RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            live_error = str(exc)

    findings = compare_rulesets(desired, live) if live is not None else []
    if args.output_json or live is not None or live_error is not None:
        evidence = build_drift_evidence(
            desired=desired,
            live=live,
            findings=findings,
            repository=args.repository,
            source=source,
            error=live_error,
        )
        if args.output_json:
            _write_json(args.output_json, evidence)
        if evidence["status"] != "passed":
            print("GitHub governance drift validation failed:")
            for finding in evidence["findings"]:
                print(f"- {finding['field']}: {finding['recommended_action']}")
            return 1

    print("Ruleset validation passed.")
    return 0


def _compare_pull_request_rule(
    desired: dict[str, Any],
    live: dict[str, Any],
) -> list[DriftFinding]:
    desired_params = (rule_by_type(desired, "pull_request") or {}).get("parameters", {})
    live_params = (rule_by_type(live, "pull_request") or {}).get("parameters", {})
    findings: list[DriftFinding] = []

    desired_reviews = int(desired_params.get("required_approving_review_count", 0))
    live_reviews = int(live_params.get("required_approving_review_count", 0))
    if desired_reviews != live_reviews:
        findings.append(
            DriftFinding(
                field="rules.pull_request.required_approving_review_count",
                desired=desired_reviews,
                live=live_reviews,
                severity="critical" if live_reviews < desired_reviews else "medium",
                confidence="confirmed",
                remediation_class="manual_github_fix"
                if live_reviews < desired_reviews
                else "repo_pr_fix",
                recommended_action=(
                    "Set the live main-protection ruleset approval count to "
                    f"{desired_reviews}; current live value is {live_reviews}."
                    if live_reviews < desired_reviews
                    else "Review whether the stronger live approval count should be "
                    "committed to the desired-state ruleset."
                ),
            )
        )

    for field in (
        "require_code_owner_review",
        "dismiss_stale_reviews_on_push",
        "require_last_push_approval",
        "required_review_thread_resolution",
        "allowed_merge_methods",
    ):
        if desired_params.get(field) != live_params.get(field):
            findings.append(
                DriftFinding(
                    field=f"rules.pull_request.{field}",
                    desired=desired_params.get(field),
                    live=live_params.get(field),
                    severity="high",
                    confidence="confirmed",
                    remediation_class="manual_github_fix",
                    recommended_action=(
                        "Align the live pull-request protection rule with the "
                        "versioned desired-state ruleset."
                    ),
                )
            )
    return findings


def _compare_required_status_checks(
    desired: dict[str, Any],
    live: dict[str, Any],
) -> list[DriftFinding]:
    desired_params = (rule_by_type(desired, "required_status_checks") or {}).get(
        "parameters", {}
    )
    live_params = (rule_by_type(live, "required_status_checks") or {}).get(
        "parameters", {}
    )
    findings: list[DriftFinding] = []

    desired_strict = desired_params.get("strict_required_status_checks_policy")
    live_strict = live_params.get("strict_required_status_checks_policy")
    if desired_strict != live_strict:
        findings.append(
            DriftFinding(
                field="rules.required_status_checks.strict_required_status_checks_policy",
                desired=desired_strict,
                live=live_strict,
                severity=(
                    "critical"
                    if desired_strict is True and live_strict is not True
                    else "medium"
                ),
                confidence="confirmed",
                remediation_class="manual_github_fix",
                recommended_action=(
                    "Align live strict required-status-check policy with desired state."
                ),
            )
        )

    desired_checks = _required_status_check_contexts(desired)
    live_checks = _required_status_check_contexts(live)
    missing_live = sorted(desired_checks - live_checks)
    extra_live = sorted(live_checks - desired_checks)
    if missing_live:
        findings.append(
            DriftFinding(
                field="rules.required_status_checks.contexts.missing_live",
                desired=sorted(desired_checks),
                live=sorted(live_checks),
                severity="critical",
                confidence="confirmed",
                remediation_class="manual_github_fix",
                recommended_action=(
                    "Restore missing live required status checks: "
                    + ", ".join(missing_live)
                ),
            )
        )
    if extra_live:
        findings.append(
            DriftFinding(
                field="rules.required_status_checks.contexts.extra_live",
                desired=sorted(desired_checks),
                live=sorted(live_checks),
                severity="low",
                confidence="confirmed",
                remediation_class="repo_pr_fix",
                recommended_action=(
                    "Review extra live required checks and commit them to desired "
                    "state if intentional: "
                    + ", ".join(extra_live)
                ),
            )
        )
    return findings


def _rule_types(ruleset: dict[str, Any]) -> set[str]:
    return {rule.get("type") for rule in ruleset.get("rules", []) if isinstance(rule, dict)}


def _required_status_check_contexts(ruleset: dict[str, Any]) -> set[str]:
    status_checks = rule_by_type(ruleset, "required_status_checks") or {}
    status_params = status_checks.get("parameters", {})
    return {
        item.get("context")
        for item in status_params.get("required_status_checks", [])
        if isinstance(item, dict) and isinstance(item.get("context"), str)
    }


def _ruleset_summary(ruleset: dict[str, Any] | None) -> dict[str, object] | None:
    if ruleset is None:
        return None
    pull_request = (rule_by_type(ruleset, "pull_request") or {}).get("parameters", {})
    status_checks = (rule_by_type(ruleset, "required_status_checks") or {}).get(
        "parameters", {}
    )
    return {
        "name": ruleset.get("name"),
        "target": ruleset.get("target"),
        "enforcement": ruleset.get("enforcement"),
        "rule_types": sorted(_rule_types(ruleset)),
        "required_approving_review_count": pull_request.get(
            "required_approving_review_count"
        ),
        "required_status_checks": sorted(_required_status_check_contexts(ruleset)),
        "strict_required_status_checks_policy": status_checks.get(
            "strict_required_status_checks_policy"
        ),
    }


def _looks_like_permission_error(error: str) -> bool:
    lowered = error.lower()
    return any(
        marker in lowered
        for marker in (
            "permission",
            "resource not accessible",
            "requires authentication",
            "not found",
            "403",
            "404",
        )
    )


def _run_gh_api(endpoint: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["gh", "api", endpoint],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        error = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(error or f"gh api failed for endpoint {endpoint}")
    return result


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
