from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def load_ci_workflow() -> str:
    return CI_WORKFLOW_PATH.read_text(encoding="utf-8")


def test_ci_workflow_exists() -> None:
    assert CI_WORKFLOW_PATH.exists()


def test_ci_workflow_runs_repository_validation() -> None:
    workflow = load_ci_workflow()

    assert "python -m pytest" in workflow
    assert "python -m ruff check ." in workflow
    assert "rglob(\"*.json\")" in workflow


def test_ci_workflow_references_required_infrastructure_secrets() -> None:
    workflow = load_ci_workflow()
    required_secrets = {
        "CLOUDFLARE_ACCOUNT_ID",
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ZONE_ID",
        "HETZNER_HOST",
        "HETZNER_SSH_KEY",
        "HETZNER_USER",
        "OPENAI_API_KEY",
    }

    for secret in required_secrets:
        assert f"secrets.{secret}" in workflow


def test_ci_workflow_validates_hetzner_private_key_format() -> None:
    workflow = load_ci_workflow()

    assert "ssh-keygen -y -f" in workflow
    assert "HETZNER_SSH_KEY must contain the complete private OpenSSH key block" in workflow
    assert "-----BEGIN OPENSSH PRIVATE KEY-----" in workflow


def test_infrastructure_smoke_test_is_manual_only() -> None:
    workflow = load_ci_workflow()

    assert "workflow_dispatch:" in workflow
    assert "run_infra_smoke:" in workflow
    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert "inputs.run_infra_smoke == true" in workflow
