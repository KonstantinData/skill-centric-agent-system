from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKIPPED_PARTS = {
    ".git",
    ".env",
    ".pytest_cache",
    ".ruff_cache",
    ".wrangler",
    "__pycache__",
    ".venv",
    "coverage",
    "dist",
    "node_modules",
    "skill_centric_agent_system.egg-info",
    "venv",
}
FORBIDDEN_BRAND = "liqui" + "sto"
FORBIDDEN_REMOVED_UI = "stream" + "lit"
ALLOWED_TENANT_ONBOARDING_PATHS = {
    ".github/workflows/tenant-cloudflare-dns-cutover.yml",
    "apps/liquisto-workbench/README.md",
    "apps/liquisto-workbench/package-lock.json",
    "apps/liquisto-workbench/package.json",
    "apps/liquisto-workbench/src/app/[section]/page.tsx",
    "apps/liquisto-workbench/src/app/layout.tsx",
    "apps/liquisto-workbench/src/app/page.tsx",
    "apps/liquisto-workbench/src/components/chrome/sidebar.tsx",
    "apps/liquisto-workbench/src/components/chrome/theme-script.tsx",
    "apps/liquisto-workbench/src/components/chrome/theme-toggle.tsx",
    "apps/liquisto-workbench/src/components/chrome/top-bar.tsx",
    "apps/liquisto-workbench/src/lib/auth.ts",
    "apps/liquisto-workbench/src/lib/workbench-data.ts",
    ".github/workflows/tenant-admin-bootstrap.yml",
    ".github/workflows/tenant-cloudflare-evidence.yml",
    ".github/workflows/tenant-ui-deploy.yml",
    ".github/workflows/tenant-ui-runtime-inventory.yml",
    ".gitignore",
    "docs/README.md",
    "docs/runbooks/daskuechenhaus-tenant-admin-bootstrap.md",
    "docs/runbooks/daskuechenhaus-tenant-onboarding.md",
    "docs/runbooks/liquisto-tenant-admin-bootstrap.md",
    "docs/runbooks/liquisto-tenant-dns-evidence.md",
    "docs/runbooks/liquisto-tenant-release-gate.md",
    "docs/runbooks/liquisto-tenant-rollback-deprovisioning.md",
    "docs/runbooks/liquisto-workbench-deployment.md",
    "deploy/liquisto-workbench/Dockerfile",
    "examples/control-plane/dev-seed.sql",
    "examples/crm-skill-packs/liquisto-research-assistance.json",
    "examples/tenants/liquisto.json",
    "package.json",
    "tests/test_github_actions_workflows.py",
    "tests/test_liquisto_workbench_ui.py",
    "tests/test_contract_schema_examples.py",
    "tests/test_control_plane_seed.py",
    "tests/test_tenant_hostname_resolution.py",
    "tests/test_tenant_isolation_matrix.py",
    "tests/test_repository_neutrality.py",
}


def iter_repository_text_files() -> list[Path]:
    paths: list[Path] = []
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    for relative_path in result.stdout.splitlines():
        path = REPO_ROOT / relative_path
        if not path.is_file():
            continue
        if SKIPPED_PARTS.intersection(path.relative_to(REPO_ROOT).parts):
            continue
        paths.append(path)
    return paths


def test_repository_content_uses_neutral_naming() -> None:
    offenders: list[str] = []

    for path in iter_repository_text_files():
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        if relative_path in ALLOWED_TENANT_ONBOARDING_PATHS:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        if FORBIDDEN_BRAND in content.lower():
            offenders.append(relative_path)

    assert not offenders


def test_repository_does_not_reintroduce_removed_ui_stack() -> None:
    offenders: list[str] = []

    for path in iter_repository_text_files():
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        content = path.read_text(encoding="utf-8", errors="ignore")
        if FORBIDDEN_REMOVED_UI in content.lower():
            offenders.append(relative_path)

    assert not offenders
