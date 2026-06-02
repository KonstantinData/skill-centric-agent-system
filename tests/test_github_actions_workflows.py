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
RUNTIME_RETENTION_CLEANUP_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "runtime-retention-cleanup.yml"
)


def load_ci_workflow() -> str:
    return CI_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_live_runtime_gates_workflow() -> str:
    return LIVE_RUNTIME_GATES_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_production_readiness_workflow() -> str:
    return PRODUCTION_READINESS_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_runtime_retention_cleanup_workflow() -> str:
    return RUNTIME_RETENTION_CLEANUP_WORKFLOW_PATH.read_text(encoding="utf-8")


def test_ci_workflow_exists() -> None:
    assert CI_WORKFLOW_PATH.exists()


def test_ci_workflow_runs_repository_validation() -> None:
    workflow = load_ci_workflow()

    assert "uv sync --frozen --extra dev --extra runtime" in workflow
    assert "uv lock --check" in workflow
    assert "uv run pytest" in workflow
    assert "uv run ruff check ." in workflow
    assert "uv run mypy" in workflow
    assert "scripts/runtime/skill_handler_coverage.py --check" in workflow
    assert "scripts/runtime/production_skill_instruction_packs.py --check" in workflow
    assert "scripts/runtime/validate_hooks_usage_model.py --check" in workflow
    assert "scripts/runtime/invariant_check.py" in workflow
    assert "ci-evidence/invariant-check.json" in workflow
    assert "scripts/runtime/run_incident_locked_regressions.py" in workflow
    assert "ci-evidence/incident-locked-regressions.json" in workflow
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
    assert "-----BEGIN OPENSSH PRIVATE KEY-----" in workflow  # pragma: allowlist secret


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
    assert "target_environment:" in workflow
    assert "control_api_url:" in workflow
    assert "run_live_dev_e2e:" in workflow
    assert "run_postgres_concurrency_smoke:" in workflow
    assert "live_task_file:" in workflow
    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert "inputs.run_live_dev_e2e == true" in workflow
    assert "inputs.run_postgres_concurrency_smoke == true" in workflow


def test_live_runtime_gates_workflow_runs_e2e_on_hetzner() -> None:
    workflow = load_live_runtime_gates_workflow()

    assert "secrets.SCAS_DEV_OPENAI_API_KEY" in workflow
    assert "secrets.SCAS_STAGING_OPENAI_API_KEY" in workflow
    assert "secrets.SCAS_PROD_OPENAI_API_KEY" in workflow
    assert "secrets.SCAS_DEV_CONTROL_API_TOKEN" in workflow
    assert "secrets.SCAS_STAGING_CONTROL_API_TOKEN" in workflow
    assert "secrets.SCAS_PROD_CONTROL_API_TOKEN" in workflow
    assert "secrets.SCAS_DEV_HETZNER_SSH_KEY" in workflow
    assert "secrets.SCAS_STAGING_HETZNER_SSH_KEY" in workflow
    assert "secrets.SCAS_PROD_HETZNER_SSH_KEY" in workflow
    assert 'OPENAI_API_KEY="$(resolve_env_secret' in workflow
    assert 'CONTROL_API_TOKEN="$(resolve_env_secret' in workflow
    assert 'HETZNER_SSH_KEY="$(resolve_env_secret' in workflow
    assert "SCAS_OPENAI_API_KEY_B64" in workflow
    assert "export OPENAI_API_KEY" in workflow
    assert "HETZNER_SSH_KEY<<__SCAS_HETZNER_SSH_KEY__" in workflow
    assert "control_api_url is required for ${TARGET_ENVIRONMENT}" in workflow
    assert "git archive --format=tar.gz" in workflow
    assert "apt-get install -y" in workflow
    assert "python3.12-venv" in workflow
    assert "scripts/runtime/live_dev_e2e.py" in workflow
    assert "--environment \"${TARGET_ENVIRONMENT}\"" in workflow
    assert "--task-file \"${LIVE_TASK_FILE}\"" in workflow
    assert "postgresql:///${runtime_database}?host=/var/run/postgresql" in workflow
    assert "/opt/scas/runtime/${TARGET_ENVIRONMENT}/live-gates" in workflow
    assert "live-runtime-handler-binding-evidence" in workflow
    assert "live-runtime-evidence/live-dev-e2e.json" in workflow


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
    assert "uv sync --frozen --extra dev --extra runtime" in workflow
    assert "uv lock --check" in workflow
    assert "uv run pytest" in workflow
    assert "uv run ruff check ." in workflow
    assert "uv run mypy" in workflow
    assert "scripts/runtime/skill_handler_coverage.py --check" in workflow
    assert "scripts/runtime/production_skill_instruction_packs.py --check" in workflow
    assert "scripts/runtime/validate_hooks_usage_model.py --check" in workflow
    assert "scripts/runtime/invariant_check.py" in workflow
    assert "production-evidence/invariant-check.json" in workflow
    assert "scripts/runtime/run_incident_locked_regressions.py" in workflow
    assert "production-evidence/incident-locked-regressions.json" in workflow
    assert "scripts/operations/evaluate_shadow_regression_thresholds.py" in workflow
    assert "production-evidence/shadow-regression-threshold-evaluation.json" in workflow
    assert "scripts/release/evaluate_pre_canary_gate.py" in workflow
    assert "production-evidence/pre-canary-safety-gate.json" in workflow
    assert "scripts/release/evaluate_automatic_rollback_rules.py" in workflow
    assert "policies/runtime/automatic-rollback-rules.json" in workflow
    assert "production-evidence/automatic-rollback-evaluation.json" in workflow
    assert "ls-files" in workflow
    assert "npm run worker:typecheck" in workflow
    assert "npm run worker:test" in workflow
    assert "npm run worker:check" in workflow
    assert "scripts/release/build_production_readiness_evidence.py" in workflow
    assert "production-readiness-evidence.json" in workflow
    assert "actions/upload-artifact" in workflow
    assert "gh run download" in workflow
    assert "live-runtime-handler-binding-evidence" in workflow


def test_production_readiness_certify_mode_requires_live_evidence() -> None:
    workflow = load_production_readiness_workflow()

    assert "--validate-only" in workflow
    assert "gh run view" in workflow
    assert "production-evidence/live-runtime-gates-run.json" in workflow
    assert "production-evidence/ai-gateway-smoke-run.json" in workflow
    assert "actions: read" in workflow


def test_runtime_retention_cleanup_workflow_exists() -> None:
    assert RUNTIME_RETENTION_CLEANUP_WORKFLOW_PATH.exists()


def test_runtime_retention_cleanup_workflow_is_scheduled_and_manual() -> None:
    workflow = load_runtime_retention_cleanup_workflow()

    assert "schedule:" in workflow
    assert 'cron: "17 2 * * *"' in workflow
    assert "workflow_dispatch:" in workflow
    assert "target_environment:" in workflow
    assert "cleanup_mode:" in workflow
    assert "confirmed-delete" in workflow
    assert "strict_missing:" in workflow


def test_runtime_retention_cleanup_workflow_defaults_to_dry_run() -> None:
    workflow = load_runtime_retention_cleanup_workflow()

    assert "CLEANUP_MODE: ${{ github.event_name == 'workflow_dispatch'" in workflow
    assert "inputs.cleanup_mode || 'dry-run'" in workflow
    assert "Scheduled retention cleanup must run in dry-run mode." in workflow
    assert 'if [ "${CLEANUP_MODE}" = "confirmed-delete" ]; then' in workflow
    assert "cleanup_args+=(--confirm)" in workflow
    assert "--confirm" not in workflow.split("cleanup_args=(")[1].split(")")[0]


def test_runtime_retention_cleanup_workflow_runs_on_hetzner_and_uploads_evidence() -> None:
    workflow = load_runtime_retention_cleanup_workflow()

    assert "secrets.SCAS_DEV_HETZNER_SSH_KEY" in workflow
    assert "secrets.SCAS_STAGING_HETZNER_SSH_KEY" in workflow
    assert "secrets.SCAS_PROD_HETZNER_SSH_KEY" in workflow
    assert "ssh-keygen -y -f" in workflow
    assert "git archive --format=tar.gz" in workflow
    assert "python3.12-venv" in workflow
    assert "postgresql:///${runtime_database}?host=/var/run/postgresql" in workflow
    assert "scas-runtime\" \"${cleanup_args[@]}\"" in workflow
    assert "/opt/scas/runtime/dev" in workflow
    assert "/opt/scas/runtime/staging" in workflow
    assert "/opt/scas/runtime/prod" in workflow
    assert "runtime-retention-cleanup-report.json" in workflow
    assert "exit-status.txt" in workflow
    assert "runtime-retention-cleanup-evidence" in workflow
