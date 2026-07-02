from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

AUTHORITY_BOUNDARY_DOC = REPO_ROOT / "docs" / "policies" / "source-authority-boundaries.md"
AUTHORITY_BOUNDARY_ADR = REPO_ROOT / "docs" / "adr" / "0014-source-authority-boundaries.md"
DOCS_INDEX = REPO_ROOT / "docs" / "README.md"

AUTHORITY_ADJACENT_EXAMPLE_PREFIXES = (
    "examples/control-plane/",
    "examples/crm-skill-packs/",
    "examples/governance/",
    "examples/infrastructure/",
    "examples/operations/",
    "examples/repo/",
    "examples/runtime/",
    "examples/runtime-evidence/",
    "examples/tenants/",
)

LEGACY_AUTHORITY_ADJACENT_EXAMPLES = {
    "examples/control-plane/cloudflare-control-plane.json",
    "examples/control-plane/dev-seed.sql",
    "examples/crm-skill-packs/daskuechenhaus-email-assignment.json",
    "examples/crm-skill-packs/daskuechenhaus-next-step-planning.json",
    "examples/crm-skill-packs/generic-email-assignment.json",
    "examples/crm-skill-packs/khh-deadline-assistance.json",
    "examples/crm-skill-packs/khh-development-planning.json",
    "examples/governance/knowledge-quality-policy.json",
    "examples/infrastructure/environment-manifest.json",
    "examples/operations/automatic-rollback-evaluation-snapshot.json",
    "examples/operations/error-classification-gate-policy.json",
    "examples/operations/error-classification-gate-snapshot.json",
    "examples/operations/error-classification-report-snapshot.json",
    "examples/operations/invariant-check-report-snapshot.json",
    "examples/operations/memory-operations-evidence.json",
    "examples/operations/pre-canary-safety-gate-snapshot.json",
    "examples/operations/production-telemetry-policy.json",
    "examples/operations/production-telemetry-snapshot.json",
    "examples/operations/rollout-metadata-snapshot.json",
    "examples/operations/shadow-eval-report-snapshot.json",
    "examples/operations/shadow-eval-trace-snapshot.json",
    "examples/operations/shadow-regression-threshold-evaluation.json",
    "examples/repo/notion-issue-comment-audit.json",
    "examples/runtime/controlled-write-action-plan.json",
    "examples/runtime/production-skill-instruction-packs.json",
    "examples/runtime/skill-handler-coverage.json",
    "examples/runtime-evidence/daskuechenhaus.json",
    "examples/runtime-evidence/kinderhaus.json",
    "examples/runtime-evidence/liquisto.json",
    "examples/runtime-evidence/tenant-under-test.json",
    "examples/tenants/daskuechenhaus.json",
    "examples/tenants/kinderhaus.json",
    "examples/tenants/tenant-under-test.json",
}


def git_tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [
        path
        for path in (line.strip() for line in result.stdout.splitlines())
        if path and (REPO_ROOT / path).is_file()
    ]


def test_source_authority_policy_documents_required_boundaries() -> None:
    policy = AUTHORITY_BOUNDARY_DOC.read_text(encoding="utf-8")
    docs_index = DOCS_INDEX.read_text(encoding="utf-8")

    for required_phrase in (
        "`registry/`",
        "`schemas/`",
        "`docs/`",
        "`tests/fixtures/`",
        "`examples/`",
        "`operations/staging-tasks/`",
        "Tenant-specific authority belongs in a governed tenant registry",
    ):
        assert required_phrase in policy

    assert "docs/policies/source-authority-boundaries.md" in docs_index
    assert "docs/adr/0014-source-authority-boundaries.md" in docs_index
    assert AUTHORITY_BOUNDARY_ADR.is_file()


def test_examples_authority_adjacent_paths_are_closed_to_new_files() -> None:
    offenders = [
        path
        for path in git_tracked_paths()
        if path.startswith(AUTHORITY_ADJACENT_EXAMPLE_PREFIXES)
        and path not in LEGACY_AUTHORITY_ADJACENT_EXAMPLES
    ]

    assert not offenders, (
        "New authority-adjacent files must not be added under examples/. "
        "Move them to registry/, tests/fixtures/, operations/, or document an "
        f"explicit legacy exception. Offenders: {offenders}"
    )
