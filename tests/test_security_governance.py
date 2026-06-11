from __future__ import annotations

import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SECURITY_SCRIPTS = REPO_ROOT / "scripts" / "security"
sys.path.insert(0, str(SECURITY_SCRIPTS))

import check_no_dotenv_files  # noqa: E402
import check_workflow_hardening  # noqa: E402
import generate_actions_bom  # noqa: E402
import generate_sbom  # noqa: E402
import validate_actions_bom  # noqa: E402
import validate_codeowners_coverage  # noqa: E402
import validate_dependency_policy  # noqa: E402
import validate_ruleset_config  # noqa: E402
import validate_sbom  # noqa: E402
import validate_secret_scan  # noqa: E402
import validate_security_closure  # noqa: E402

WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
RULESET_PATH = REPO_ROOT / ".github" / "rulesets" / "main-protection.json"
QUALITY_SCHEMA_PATH = REPO_ROOT / "schemas" / "knowledge-quality-policy.schema.json"
QUALITY_EXAMPLE_PATH = REPO_ROOT / "examples" / "governance" / "knowledge-quality-policy.json"
SECURITY_CLOSURE_SCHEMA_PATH = (
    REPO_ROOT / "schemas" / "production-security-closure.schema.json"
)
SECURITY_CLOSURE_POLICY_PATH = (
    REPO_ROOT / "policies" / "security" / "production-security-closure.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_required_security_governance_files_exist() -> None:
    required_paths = (
        "SECURITY.md",
        "AGENTS.md",
        ".gitleaks.toml",
        ".bandit",
        ".pre-commit-config.yaml",
        ".github/CODEOWNERS",
        ".github/dependabot.yml",
        ".github/dependency-review-config.yml",
        ".github/workflows/security-governance.yml",
        ".github/workflows/dependency-review.yml",
        ".github/workflows/codeql.yml",
        "docs/policies/data-governance.md",
        "docs/policies/review-gates.md",
        "docs/policies/threat-model.md",
        "schemas/production-security-closure.schema.json",
        "policies/security/production-security-closure.json",
        "policies/dependencies/direct-dependency-owners.json",
        "policies/dependencies/dependency-risk-exceptions.json",
        "policies/dependencies/dependency-license-policy.json",
        "policies/rego/ci_supply_chain.rego",
    )

    for path in required_paths:
        assert (REPO_ROOT / path).exists(), path


def test_security_docs_define_secret_and_review_controls() -> None:
    security = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    review_gates = (REPO_ROOT / "docs" / "policies" / "review-gates.md").read_text(
        encoding="utf-8"
    )
    data_governance = (REPO_ROOT / "docs" / "policies" / "data-governance.md").read_text(
        encoding="utf-8"
    )

    assert "Tracked `.env` files are not allowed" in security
    assert "must not self-grant tools" in agents
    assert "CODEOWNERS ownership coverage" in review_gates
    assert "secret" in data_governance
    assert "raw runtime traces" in data_governance
    assert "Threat Model Closure" in (
        REPO_ROOT / "docs" / "policies" / "threat-model.md"
    ).read_text(encoding="utf-8")


def test_no_dotenv_guard_classifies_forbidden_and_allowed_names() -> None:
    assert check_no_dotenv_files.is_forbidden_dotenv(".env")
    assert check_no_dotenv_files.is_forbidden_dotenv("config/.env.production")
    assert not check_no_dotenv_files.is_forbidden_dotenv(".env.example")
    assert not check_no_dotenv_files.is_forbidden_dotenv("docs/env.md")


def test_secret_scan_validators_reject_findings_and_accept_clean_reports(tmp_path: Path) -> None:
    detect_report = tmp_path / "detect.json"
    detect_report.write_text(
        json.dumps({"results": {"src/app.py": [{"type": "Secret", "line_number": 1}]}}),
        encoding="utf-8",
    )
    gitleaks_report = tmp_path / "gitleaks.json"
    gitleaks_report.write_text(json.dumps([{"File": "src/app.py"}]), encoding="utf-8")

    with pytest.raises(SystemExit, match="detect-secrets found"):
        validate_secret_scan.validate_detect_secrets(detect_report)
    with pytest.raises(SystemExit, match="Gitleaks found"):
        validate_secret_scan.validate_gitleaks(gitleaks_report)

    detect_report.write_text(
        json.dumps(
            {
                "results": {
                    "policies/security/production-security-closure.json": [
                        {"type": "Secret Keyword", "line_number": 59}
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    validate_secret_scan.validate_detect_secrets(detect_report)

    detect_report.write_text(
        json.dumps(
            {
                "results": {
                    ".github/workflows/runtime-retention-cleanup.yml": [
                        {"type": "Private Key", "line_number": 1}
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="detect-secrets found"):
        validate_secret_scan.validate_detect_secrets(detect_report)

    detect_report.write_text(json.dumps({"results": {}}), encoding="utf-8")
    gitleaks_report.write_text(json.dumps([]), encoding="utf-8")
    validate_secret_scan.validate_detect_secrets(detect_report)
    validate_secret_scan.validate_gitleaks(gitleaks_report)


def test_main_ruleset_desired_state_is_valid(tmp_path: Path) -> None:
    assert validate_ruleset_config.validate_ruleset(RULESET_PATH) == []
    desired = load_json(RULESET_PATH)
    desired_contexts = validate_ruleset_config._required_status_check_contexts(desired)
    assert "analyze" in desired_contexts

    broken = load_json(RULESET_PATH)
    status_rule = next(rule for rule in broken["rules"] if rule["type"] == "required_status_checks")
    status_rule["parameters"]["required_status_checks"] = []
    broken_path = tmp_path / "main-protection.json"
    broken_path.write_text(json.dumps(broken), encoding="utf-8")

    failures = validate_ruleset_config.validate_ruleset(broken_path)
    assert any("missing status checks" in failure for failure in failures)


def test_ruleset_drift_detects_weakened_live_approval_count() -> None:
    desired = load_json(RULESET_PATH)
    live = deepcopy(desired)
    pull_request = next(rule for rule in live["rules"] if rule["type"] == "pull_request")
    pull_request["parameters"]["required_approving_review_count"] = 0

    findings = validate_ruleset_config.compare_rulesets(desired, live)

    assert any(
        finding.field == "rules.pull_request.required_approving_review_count"
        and finding.severity == "critical"
        and finding.remediation_class == "manual_github_fix"
        for finding in findings
    )


def test_ruleset_drift_evidence_records_permission_setup_path() -> None:
    desired = load_json(RULESET_PATH)

    evidence = validate_ruleset_config.build_drift_evidence(
        desired=desired,
        live=None,
        findings=[],
        repository="KonstantinData/skill-centric-agent-system",
        source="github-api",
        error="HTTP 403 resource not accessible by integration",
    )

    assert evidence["status"] == "permission_missing"
    finding = evidence["findings"][0]
    assert finding["confidence"] == "permission_missing"
    assert finding["remediation_class"] == "permission_setup"


def test_codeowners_effective_coverage_protects_policy_directory() -> None:
    failures = validate_codeowners_coverage.validate_effective_coverage(
        codeowners_path=REPO_ROOT / ".github" / "CODEOWNERS"
    )

    assert failures == []
    rules = validate_codeowners_coverage.parse_codeowners(
        REPO_ROOT / ".github" / "CODEOWNERS"
    )
    effective = validate_codeowners_coverage.effective_rule_for_path(
        "docs/policies/production-recertification-policy.md",
        rules,
    )
    assert effective is not None
    assert "@KonstantinData" in effective.owners


def test_codeowners_effective_coverage_rejects_later_conflicting_rule(tmp_path: Path) -> None:
    codeowners = tmp_path / "CODEOWNERS"
    codeowners.write_text(
        "\n".join(
            (
                "/docs/policies/ @KonstantinData",
                "/docs/policies/production-recertification-policy.md @someone-else",
            )
        ),
        encoding="utf-8",
    )

    failures = validate_codeowners_coverage.validate_effective_coverage(
        codeowners_path=codeowners,
        required_paths=("docs/policies/production-recertification-policy.md",),
    )

    assert any("do not include @KonstantinData" in failure for failure in failures)


def test_dependency_policy_covers_current_direct_dependencies() -> None:
    assert validate_dependency_policy.validate_dependency_policy(REPO_ROOT) == []


def test_dependency_policy_rejects_expired_exception() -> None:
    failures = validate_dependency_policy.validate_cve_exceptions(
        {
            "exceptions": [
                {
                    "id": "CVE-2000-0001",
                    "package": "example",
                    "ecosystem": "python",
                    "owner": "@KonstantinData",
                    "reason": "fixture",
                    "expires": "2000-01-01",
                    "accepted_risk": "fixture",
                }
            ]
        }
    )

    assert any("expired" in failure for failure in failures)


def test_workflows_are_hardened_and_actions_are_pinned(tmp_path: Path) -> None:
    assert check_workflow_hardening.check_workflow_hardening(WORKFLOW_DIR) == []

    actions_bom_path = tmp_path / "actions-bom.json"
    actions_bom = generate_actions_bom.build_actions_bom(WORKFLOW_DIR)
    actions_bom_path.write_text(json.dumps(actions_bom), encoding="utf-8")
    assert validate_actions_bom.validate_actions_bom_file(actions_bom_path) == []

    bad_bom = deepcopy(actions_bom)
    bad_bom["actions"].append(
        {
            "workflow": "bad.yml",
            "line": 1,
            "kind": "external",
            "name": "actions/checkout",
            "reference": "actions/checkout@v6",
            "pin": "v6",
            "sha_pinned": False,
            "docker_digest_pinned": True,
        }
    )
    bad_path = tmp_path / "bad-actions-bom.json"
    bad_path.write_text(json.dumps(bad_bom), encoding="utf-8")
    failures = validate_actions_bom.validate_actions_bom_file(bad_path)
    assert any("not SHA-pinned" in failure for failure in failures)


def test_workflow_hardening_rejects_unpinned_action(tmp_path: Path) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "bad.yml").write_text(
        """
name: bad
on: [pull_request]
permissions:
  contents: read
concurrency:
  group: bad
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v6
""",
        encoding="utf-8",
    )

    failures = check_workflow_hardening.check_workflow_hardening(workflow_dir)
    assert any("must be pinned" in failure for failure in failures)


def test_release_sbom_generation_and_validation(tmp_path: Path) -> None:
    sbom = generate_sbom.build_sbom(REPO_ROOT)
    sbom_path = tmp_path / "release-sbom.json"
    sbom_path.write_text(json.dumps(sbom), encoding="utf-8")

    assert validate_sbom.validate_sbom_file(sbom_path) == []
    assert {"ecosystem": "python", "name": "pytest"} in sbom["components"]
    assert {"ecosystem": "npm", "name": "wrangler"} in sbom["components"]


def test_knowledge_quality_policy_schema_and_example() -> None:
    schema = load_json(QUALITY_SCHEMA_PATH)
    example = load_json(QUALITY_EXAMPLE_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(example)

    invalid = deepcopy(example)
    invalid["ingestion_controls"]["secret_sensitivity_allowed"] = True
    with pytest.raises(Exception, match="False was expected"):
        Draft202012Validator(schema).validate(invalid)


def test_security_closure_policy_schema_and_validator() -> None:
    schema = load_json(SECURITY_CLOSURE_SCHEMA_PATH)
    policy = load_json(SECURITY_CLOSURE_POLICY_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)
    assert validate_security_closure.validate_security_closure(REPO_ROOT) == []


def test_no_workflows_use_floating_action_tags() -> None:
    for workflow_path in WORKFLOW_DIR.glob("*.yml"):
        workflow = workflow_path.read_text(encoding="utf-8")
        assert "@v" not in workflow, workflow_path.name


def test_ruleset_has_matching_codeowners_for_high_impact_paths() -> None:
    codeowners = (REPO_ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    for path in (
        "/.github/",
        "/policies/",
        "/schemas/",
        "/workers/control-api/",
        "/src/skill_centric_agent_system/runtime/",
        "/docs/policies/production-readiness.md",
        "/docs/policies/",
    ):
        assert path in codeowners

    assert "require_code_owner_review" in RULESET_PATH.read_text(encoding="utf-8")


def test_security_scripts_are_in_optional_pre_commit_hooks() -> None:
    pre_commit = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "check_no_dotenv_files.py" in pre_commit
    assert "check_workflow_hardening.py" in pre_commit
    assert "validate_dependency_policy.py" in pre_commit
    assert "validate_security_closure.py" in pre_commit


def test_security_governance_workflow_runs_expected_gates() -> None:
    workflow = (WORKFLOW_DIR / "security-governance.yml").read_text(encoding="utf-8")

    assert "detect-secrets scan" in workflow
    assert "validate_secret_scan.py gitleaks" in workflow
    assert "pip-audit" in workflow
    assert "npm audit --audit-level=high" in workflow
    assert "validate_ruleset_config.py" in workflow
    assert "validate_codeowners_coverage.py" in workflow
    assert "codeowners-effective-ownership.json" in workflow
    assert "validate_security_closure.py" in workflow
    assert "generate_actions_bom.py" in workflow
    assert "generate_sbom.py" in workflow


def test_dependency_review_and_codeql_workflows_exist() -> None:
    dependency_review = (WORKFLOW_DIR / "dependency-review.yml").read_text(encoding="utf-8")
    codeql = (WORKFLOW_DIR / "codeql.yml").read_text(encoding="utf-8")

    assert "actions/dependency-review-action@" in dependency_review
    assert "config-file: .github/dependency-review-config.yml" in dependency_review
    assert "github/codeql-action/init@" in codeql
    assert "languages: python,javascript-typescript" in codeql


def test_generated_actions_bom_has_no_unpinned_references_after_copy(tmp_path: Path) -> None:
    copied = tmp_path / "workflows"
    shutil.copytree(WORKFLOW_DIR, copied)
    bom = generate_actions_bom.build_actions_bom(copied)
    assert all(entry["sha_pinned"] for entry in bom["actions"] if entry["kind"] == "external")

