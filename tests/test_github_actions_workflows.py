from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
LIVE_RUNTIME_GATES_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "live-runtime-gates.yml"
)


def load_ci_workflow() -> str:
    return CI_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_live_runtime_gates_workflow() -> str:
    return LIVE_RUNTIME_GATES_WORKFLOW_PATH.read_text(encoding="utf-8")


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
        "CONTROL_API_TOKEN",
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


def test_live_runtime_gates_workflow_exists() -> None:
    assert LIVE_RUNTIME_GATES_WORKFLOW_PATH.exists()


def test_live_runtime_gates_workflow_is_manual_only() -> None:
    workflow = load_live_runtime_gates_workflow()

    assert "workflow_dispatch:" in workflow
    assert "run_live_dev_e2e:" in workflow
    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert "inputs.run_live_dev_e2e == true" in workflow


def test_live_runtime_gates_workflow_runs_e2e_on_hetzner() -> None:
    workflow = load_live_runtime_gates_workflow()

    assert "secrets.CONTROL_API_TOKEN" in workflow
    assert "secrets.HETZNER_SSH_KEY" in workflow
    assert "git archive --format=tar.gz" in workflow
    assert "scripts/runtime/live_dev_e2e.py" in workflow
    assert "postgresql:///scas_runtime?host=/var/run/postgresql" in workflow
    assert "/opt/scas/runtime/live-dev-gates" in workflow
