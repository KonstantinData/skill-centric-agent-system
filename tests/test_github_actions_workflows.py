from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
LIVE_RUNTIME_GATES_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "live-runtime-gates.yml"
)
PRODUCTION_READINESS_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "production-readiness.yml"
)


def load_ci_workflow() -> str:
    return CI_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_live_runtime_gates_workflow() -> str:
    return LIVE_RUNTIME_GATES_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_production_readiness_workflow() -> str:
    return PRODUCTION_READINESS_WORKFLOW_PATH.read_text(encoding="utf-8")


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
        "AI_GATEWAY_AUTH_TOKEN",
        "CONTROL_API_TOKEN",
    }

    for secret in required_secrets:
        assert f"secrets.{secret}" in workflow


def test_ci_workflow_can_deploy_ai_gateway_live_smoke() -> None:
    workflow = load_ci_workflow()

    assert "run_ai_gateway_live_smoke:" in workflow
    assert "inputs.run_ai_gateway_live_smoke == true" in workflow
    assert "OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}" in workflow
    assert "AI_GATEWAY_AUTH_TOKEN: ${{ secrets.AI_GATEWAY_AUTH_TOKEN }}" in workflow
    assert '"AI_GATEWAY_AUTH_TOKEN"' in workflow
    assert "RUN_AI_GATEWAY_LIVE_SMOKE: ${{ inputs.run_ai_gateway_live_smoke }}" in workflow
    assert "Missing required secret for live AI Gateway smoke: AI_GATEWAY_AUTH_TOKEN" in workflow
    assert "SCAS_WORKER_SECRETS_FILE" in workflow
    assert "--secrets-file" in workflow
    assert "AI_GATEWAY_ACCOUNT_ID" in workflow
    assert "CLOUDFLARE_ACCOUNT_ID" in workflow
    assert "scripts/cloudflare/ai_gateway_live_smoke.py" in workflow


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
    assert "run_postgres_concurrency_smoke:" in workflow
    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert "inputs.run_live_dev_e2e == true" in workflow
    assert "inputs.run_postgres_concurrency_smoke == true" in workflow


def test_live_runtime_gates_workflow_runs_e2e_on_hetzner() -> None:
    workflow = load_live_runtime_gates_workflow()

    assert "secrets.CONTROL_API_TOKEN" in workflow
    assert "secrets.HETZNER_SSH_KEY" in workflow
    assert "git archive --format=tar.gz" in workflow
    assert "apt-get install -y" in workflow
    assert "python3.12-venv" in workflow
    assert "scripts/runtime/live_dev_e2e.py" in workflow
    assert "postgresql:///scas_runtime?host=/var/run/postgresql" in workflow
    assert "/opt/scas/runtime/dev/live-gates" in workflow


def test_live_runtime_gates_workflow_runs_postgres_concurrency_smoke() -> None:
    workflow = load_live_runtime_gates_workflow()

    assert "RUN_POSTGRES_CONCURRENCY_SMOKE" in workflow
    assert "scripts/runtime/postgres_concurrency_smoke.py" in workflow
    assert "--events 20" in workflow
    assert "--profile-file examples/profiles/code-review-profile.json" in workflow


def test_production_readiness_workflow_exists() -> None:
    assert PRODUCTION_READINESS_WORKFLOW_PATH.exists()


def test_production_readiness_workflow_builds_non_secret_evidence() -> None:
    workflow = load_production_readiness_workflow()

    assert "workflow_dispatch:" in workflow
    assert "target_environment:" in workflow
    assert "certification_mode:" in workflow
    assert "python -m pytest" in workflow
    assert "python -m ruff check ." in workflow
    assert "ls-files" in workflow
    assert "npm run worker:typecheck" in workflow
    assert "npm run worker:test" in workflow
    assert "npm run worker:check" in workflow
    assert "production-readiness-evidence.json" in workflow
    assert "No secret values are written" in workflow
    assert "not-production-ready" in workflow
    assert "actions/upload-artifact" in workflow


def test_production_readiness_certify_mode_requires_live_evidence() -> None:
    workflow = load_production_readiness_workflow()

    assert "certify mode requires live_runtime_gates_run_url" in workflow
    assert "certify mode requires ai_gateway_smoke_run_url" in workflow
