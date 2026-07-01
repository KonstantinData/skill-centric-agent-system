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
GITHUB_GOVERNANCE_DRIFT_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "github-governance-drift.yml"
)
CONTROL_API_WORKER_SECRETS_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "control-api-worker-secrets.yml"
)
STAGING_RUNTIME_BOOTSTRAP_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "staging-runtime-bootstrap.yml"
)
TENANT_UI_DEPLOY_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "tenant-ui-deploy.yml"
TENANT_ADMIN_BOOTSTRAP_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "tenant-admin-bootstrap.yml"
)
TENANT_CLOUDFLARE_EVIDENCE_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "tenant-cloudflare-evidence.yml"
)
TENANT_CLOUDFLARE_DNS_CUTOVER_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "tenant-cloudflare-dns-cutover.yml"
)
LIQUISTO_CLOUDFLARE_ACCESS_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "liquisto-cloudflare-access.yml"
)
KHH_CLOUDFLARE_ACCESS_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "khh-cloudflare-access.yml"
)
ES_DASKUECHENHAUS_SITE_DEPLOY_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "es-daskuechenhaus-site-deploy.yml"
)
ES_DASKUECHENHAUS_CRM_DEPLOY_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "es-daskuechenhaus-crm-deploy.yml"
)
ES_DASKUECHENHAUS_MAIL_RUNTIME_SYNC_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "es-daskuechenhaus-mail-runtime-sync.yml"
)
ES_DASKUECHENHAUS_ADMIN_API_DEPLOY_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "es-daskuechenhaus-admin-api-deploy.yml"
)
ES_DASKUECHENHAUS_ACCESS_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "es-daskuechenhaus-access.yml"
)
ES_DASKUECHENHAUS_CUSTOMER_DATABASE_RESET_WORKFLOW_PATH = (
    REPO_ROOT
    / ".github"
    / "workflows"
    / "es-daskuechenhaus-customer-database-reset.yml"
)
DEFAULT_TENANT_OWNER_PRINCIPAL_ENV_NAME = "LIQUI" + "STO_OWNER_PRINCIPAL_ID"
DASKUECHENHAUS_OWNER_PRINCIPAL_ENV_NAME = "DASKUECHENHAUS_OWNER_PRINCIPAL_ID"
TENANT_KINDERHAUS_OWNER_PRINCIPAL_ENV_NAME = "TENANT_KINDERHAUS_OWNER_PRINCIPAL_ID"
DASKUECHENHAUS_ADDITIONAL_ADMIN_PRINCIPALS_ENV_NAME = (
    "DASKUECHENHAUS_ADDITIONAL_ADMIN_PRINCIPAL_IDS_JSON"
)


def load_ci_workflow() -> str:
    return CI_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_live_runtime_gates_workflow() -> str:
    return LIVE_RUNTIME_GATES_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_production_readiness_workflow() -> str:
    return PRODUCTION_READINESS_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_runtime_retention_cleanup_workflow() -> str:
    return RUNTIME_RETENTION_CLEANUP_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_github_governance_drift_workflow() -> str:
    return GITHUB_GOVERNANCE_DRIFT_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_control_api_worker_secrets_workflow() -> str:
    return CONTROL_API_WORKER_SECRETS_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_staging_runtime_bootstrap_workflow() -> str:
    return STAGING_RUNTIME_BOOTSTRAP_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_tenant_ui_deploy_workflow() -> str:
    return TENANT_UI_DEPLOY_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_tenant_admin_bootstrap_workflow() -> str:
    return TENANT_ADMIN_BOOTSTRAP_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_tenant_cloudflare_evidence_workflow() -> str:
    return TENANT_CLOUDFLARE_EVIDENCE_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_tenant_cloudflare_dns_cutover_workflow() -> str:
    return TENANT_CLOUDFLARE_DNS_CUTOVER_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_liquisto_cloudflare_access_workflow() -> str:
    return LIQUISTO_CLOUDFLARE_ACCESS_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_khh_cloudflare_access_workflow() -> str:
    return KHH_CLOUDFLARE_ACCESS_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_es_daskuechenhaus_site_deploy_workflow() -> str:
    return ES_DASKUECHENHAUS_SITE_DEPLOY_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_es_daskuechenhaus_crm_deploy_workflow() -> str:
    return ES_DASKUECHENHAUS_CRM_DEPLOY_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_es_daskuechenhaus_mail_runtime_sync_workflow() -> str:
    return ES_DASKUECHENHAUS_MAIL_RUNTIME_SYNC_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_es_daskuechenhaus_admin_api_deploy_workflow() -> str:
    return ES_DASKUECHENHAUS_ADMIN_API_DEPLOY_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_es_daskuechenhaus_access_workflow() -> str:
    return ES_DASKUECHENHAUS_ACCESS_WORKFLOW_PATH.read_text(encoding="utf-8")


def load_es_daskuechenhaus_customer_database_reset_workflow() -> str:
    return ES_DASKUECHENHAUS_CUSTOMER_DATABASE_RESET_WORKFLOW_PATH.read_text(
        encoding="utf-8"
    )


def test_ci_workflow_exists() -> None:
    assert CI_WORKFLOW_PATH.exists()


def test_ci_workflow_runs_repository_validation() -> None:
    workflow = load_ci_workflow()

    assert "uv sync --frozen --extra dev --extra runtime" in workflow
    assert "uv lock --check" in workflow
    assert "uv run pytest" in workflow
    assert "uv run pytest tests/test_runtime_efficiency_baselines.py" in workflow
    assert "uv run ruff check ." in workflow
    assert "uv run mypy" in workflow
    assert "scripts/runtime/skill_handler_coverage.py --check" in workflow
    assert "scripts/runtime/production_skill_instruction_packs.py --check" in workflow
    assert "scripts/runtime/validate_hooks_usage_model.py --check" in workflow
    assert "scripts/release/validate_production_recertification_policy.py --check" in workflow
    assert "scripts/runtime/scan_transition_signals.py --check" in workflow
    assert "scripts/runtime/validate_transition_evidence.py --check" in workflow
    assert "scripts/runtime/validate_capability_delta_transition_policy.py --check" in workflow
    assert "scripts/runtime/evaluate_intent_transition_traces.py --check" in workflow
    assert "scripts/runtime/evaluate_intent_transition_shadow_metrics.py --check" in workflow
    assert "scripts/runtime/validate_structured_evidence_extraction_decision.py --check" in workflow
    assert "scripts/runtime/validate_semantic_drift_guard.py --check" in workflow
    assert "scripts/runtime/invariant_check.py" in workflow
    assert "ci-evidence/invariant-check.json" in workflow
    assert "scripts/runtime/run_incident_locked_regressions.py" in workflow
    assert "ci-evidence/incident-locked-regressions.json" in workflow
    assert "rglob(\"*.json\")" in workflow


def test_ci_workflow_references_required_infrastructure_secrets() -> None:
    workflow = load_ci_workflow()
    required_secrets = {
        "CLOUDFLARE_ZONE_ID",
        "SCAS_DEV_CLOUDFLARE_ACCOUNT_ID",
        "SCAS_DEV_CLOUDFLARE_DEPLOY_TOKEN",
        "SCAS_STAGING_CLOUDFLARE_ACCOUNT_ID",
        "SCAS_STAGING_CLOUDFLARE_DEPLOY_TOKEN",
        "SCAS_PROD_CLOUDFLARE_ACCOUNT_ID",
        "SCAS_PROD_CLOUDFLARE_DEPLOY_TOKEN",
        "HETZNER_HOST",
        "HETZNER_SSH_KEY",
        "HETZNER_USER",
        "OPENAI_API_KEY",
        "AI_GATEWAY_AUTH_TOKEN",
        "CONTROL_API_TOKEN",
    }

    for secret in required_secrets:
        assert f"secrets.{secret}" in workflow
    assert "secrets.CLOUDFLARE_API_TOKEN" not in workflow


def test_ci_workflow_can_deploy_ai_gateway_live_smoke() -> None:
    workflow = load_ci_workflow()

    assert "target_environment:" in workflow
    assert "run_ai_gateway_live_smoke:" in workflow
    assert "confirm_production:" in workflow
    assert "inputs.run_ai_gateway_live_smoke == true" in workflow
    assert "environment:" in workflow
    assert "inputs.target_environment == 'prod' && 'production'" in workflow
    assert "CONFIRM_PRODUCTION: ${{ inputs.confirm_production }}" in workflow
    assert "confirm_production must be true for production Control API deploys" in workflow
    assert "SCAS_DEV_OPENAI_API_KEY: ${{ secrets.SCAS_DEV_OPENAI_API_KEY }}" in workflow
    assert "SCAS_DEV_CONTROL_API_TOKEN: ${{ secrets.SCAS_DEV_CONTROL_API_TOKEN }}" in workflow
    assert "SCAS_STAGING_OPENAI_API_KEY: ${{ secrets.SCAS_STAGING_OPENAI_API_KEY }}" in workflow
    assert (
        "SCAS_STAGING_CONTROL_API_TOKEN: "
        "${{ secrets.SCAS_STAGING_CONTROL_API_TOKEN }}"
    ) in workflow
    assert (
        "SCAS_DEV_CLOUDFLARE_ACCOUNT_ID: ${{ secrets.SCAS_DEV_CLOUDFLARE_ACCOUNT_ID }}"
        in workflow
    )
    assert (
        "SCAS_DEV_CLOUDFLARE_DEPLOY_TOKEN: "
        "${{ secrets.SCAS_DEV_CLOUDFLARE_DEPLOY_TOKEN }}"
    ) in workflow
    assert (
        "SCAS_STAGING_CLOUDFLARE_ACCOUNT_ID: "
        "${{ secrets.SCAS_STAGING_CLOUDFLARE_ACCOUNT_ID }}"
    ) in workflow
    assert (
        "SCAS_STAGING_CLOUDFLARE_DEPLOY_TOKEN: "
        "${{ secrets.SCAS_STAGING_CLOUDFLARE_DEPLOY_TOKEN }}"
    ) in workflow
    assert "LEGACY_OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}" in workflow
    assert "LEGACY_CONTROL_API_TOKEN: ${{ secrets.CONTROL_API_TOKEN }}" in workflow
    assert 'resolve_env_secret "${TARGET_ENVIRONMENT}" CONTROL_API_TOKEN' in workflow
    assert 'resolve_env_secret "${TARGET_ENVIRONMENT}" OPENAI_API_KEY' in workflow
    assert 'resolve_env_secret "${TARGET_ENVIRONMENT}" CLOUDFLARE_ACCOUNT_ID' in workflow
    assert 'resolve_env_secret "${TARGET_ENVIRONMENT}" CLOUDFLARE_API_TOKEN' in workflow
    assert "CLOUDFLARE_DEPLOY_TOKEN must allow Worker script writes" in workflow
    assert "SCAS_DEV_CLOUDFLARE_API_TOKEN" not in workflow
    assert "LEGACY_CLOUDFLARE_API_TOKEN" not in workflow
    assert "AI_GATEWAY_AUTH_TOKEN: ${{ secrets.AI_GATEWAY_AUTH_TOKEN }}" in workflow
    assert '"AI_GATEWAY_AUTH_TOKEN"' in workflow
    assert "RUN_AI_GATEWAY_LIVE_SMOKE: ${{ inputs.run_ai_gateway_live_smoke }}" in workflow
    assert "Missing required secret for live AI Gateway smoke: AI_GATEWAY_AUTH_TOKEN" in workflow
    assert "SCAS_WORKER_SECRETS_FILE" in workflow
    assert "--secrets-file" in workflow
    assert 'wrangler_env_args=(--env "${TARGET_ENVIRONMENT}")' in workflow
    assert 'SCAS_CONTROL_API_URL="https://scas-control-api-staging.' in workflow
    assert 'still-butterfly-bbff.workers.dev"' in workflow
    assert 'scas-ai-gateway-{target_environment}-run' in workflow
    assert "AI_GATEWAY_ACCOUNT_ID" in workflow
    assert "CLOUDFLARE_ACCOUNT_ID" in workflow
    assert "scripts/cloudflare/ai_gateway_live_smoke.py" in workflow


def test_ci_workflow_validates_hetzner_private_key_format() -> None:
    workflow = load_ci_workflow()

    assert "ssh-keygen -y -f" in workflow
    assert "HETZNER_SSH_KEY must contain the complete private OpenSSH key block" in workflow
    assert "The configured key is missing the expected OpenSSH private key header" in workflow
    assert "Expected first line" not in workflow


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
    assert "confirm_production:" in workflow
    assert "inputs.target_environment == 'prod' && 'production'" in workflow
    assert "CONFIRM_PRODUCTION: ${{ inputs.confirm_production }}" in workflow
    assert "confirm_production must be true for production live runtime gates." in workflow
    assert "Production Control Plane seeding is not allowed from Live Runtime Gates." in workflow
    assert "control_api_url:" in workflow
    assert "run_live_dev_e2e:" in workflow
    assert "run_postgres_concurrency_smoke:" in workflow
    assert "live_task_file:" in workflow
    assert "- tenant" in workflow
    assert "- liquisto" in workflow
    assert "- daskuechenhaus" in workflow
    assert "- kinderhaus" in workflow
    assert "- single" in workflow
    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert "inputs.run_live_dev_e2e == true" in workflow
    assert "inputs.run_postgres_concurrency_smoke == true" in workflow


def test_live_runtime_gates_workflow_runs_e2e_on_hetzner() -> None:
    workflow = load_live_runtime_gates_workflow()

    assert "secrets.SCAS_DEV_OPENAI_API_KEY" in workflow
    assert "secrets.SCAS_STAGING_OPENAI_API_KEY" in workflow
    assert "secrets.SCAS_PROD_OPENAI_API_KEY" in workflow
    assert "secrets.SCAS_DEV_CLOUDFLARE_DEPLOY_TOKEN" in workflow
    assert "secrets.SCAS_STAGING_CLOUDFLARE_DEPLOY_TOKEN" in workflow
    assert "secrets.SCAS_PROD_CLOUDFLARE_DEPLOY_TOKEN" in workflow
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
    assert "SCAS_LIVE_E2E_REDACT_PRINCIPAL_ID" in workflow
    assert "SCAS_LIQUISTO_OWNER_PRINCIPAL_ID_B64" not in workflow
    assert "SCAS_${TARGET_ENVIRONMENT^^}_LIQUISTO_OWNER_PRINCIPAL_ID" not in workflow
    assert "liquisto-live-task.json" not in workflow
    assert "export OPENAI_API_KEY" in workflow
    assert "HETZNER_SSH_KEY<<__SCAS_HETZNER_SSH_KEY__" in workflow
    assert "control_api_url is required for ${TARGET_ENVIRONMENT}" in workflow
    assert "Validate Control Plane credentials" in workflow
    assert "--data @examples/control-api/composition-context-request.json" in workflow
    assert "SCAS_${TARGET_ENVIRONMENT^^}_CONTROL_API_TOKEN" in workflow
    assert 'wrangler_env_args=()' in workflow
    assert 'if [ "${TARGET_ENVIRONMENT}" != "dev" ]; then' in workflow
    assert 'wrangler_env_args=(--env "${TARGET_ENVIRONMENT}")' in workflow
    assert 'wrangler.toml "${wrangler_env_args[@]}"' in workflow
    assert "npx wrangler whoami --config workers/control-api/wrangler.toml" in workflow
    assert 'if [ "${TARGET_ENVIRONMENT}" = "dev" ]; then' in workflow
    assert 'npx wrangler deploy --config workers/control-api/wrangler.toml --env ""' in workflow
    assert "live gates only auto-deploy dev" in workflow
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
    assert "SCAS_DEV_CLOUDFLARE_API_TOKEN" not in workflow


def test_live_runtime_gates_workflow_runs_postgres_concurrency_smoke() -> None:
    workflow = load_live_runtime_gates_workflow()

    assert "RUN_POSTGRES_CONCURRENCY_SMOKE" in workflow
    assert "scripts/runtime/postgres_concurrency_smoke.py" in workflow
    assert "--events 20" in workflow
    assert "--profile-file examples/profiles/code-review-profile.json" in workflow


def test_control_api_worker_secrets_workflow_syncs_environment_secrets() -> None:
    assert CONTROL_API_WORKER_SECRETS_WORKFLOW_PATH.exists()
    workflow = load_control_api_worker_secrets_workflow()

    assert "workflow_dispatch:" in workflow
    assert "target_environment:" in workflow
    assert "confirm_production:" in workflow
    assert "inputs.target_environment == 'prod' && 'production'" in workflow
    assert "CONFIRM_PRODUCTION: ${{ inputs.confirm_production }}" in workflow
    assert "confirm_production must be true for production Worker secret sync." in workflow
    assert "SCAS_STAGING_CLOUDFLARE_DEPLOY_TOKEN" in workflow
    assert "SCAS_STAGING_CLOUDFLARE_API_TOKEN" not in workflow
    assert "LEGACY_CLOUDFLARE_API_TOKEN" not in workflow
    assert "SCAS_STAGING_CONTROL_API_TOKEN" in workflow
    assert "SCAS_STAGING_OPENAI_API_KEY" in workflow
    assert "CONTROL_API_COMPOSITION_TOKEN" in workflow
    assert "CONTROL_API_INGESTION_TOKEN" in workflow
    assert "CONTROL_API_RETRIEVAL_TOKEN" in workflow
    assert "CONTROL_API_AI_GATEWAY_TOKEN" in workflow
    assert "wrangler secret bulk" in workflow
    assert "wrangler secret list" in workflow
    assert 'wrangler_env_args=()' in workflow
    assert 'if [ "${TARGET_ENVIRONMENT}" != "dev" ]; then' in workflow
    assert 'wrangler_env_args=(--env "${TARGET_ENVIRONMENT}")' in workflow
    assert "SCAS_WORKER_SECRETS_FILE" in workflow
    assert "rm -f" in workflow


def test_staging_runtime_bootstrap_workflow_uses_staging_hetzner_secrets() -> None:
    assert STAGING_RUNTIME_BOOTSTRAP_WORKFLOW_PATH.exists()
    workflow = load_staging_runtime_bootstrap_workflow()

    assert "workflow_dispatch:" in workflow
    assert "options:" in workflow
    assert "- staging" in workflow
    assert "secrets.SCAS_STAGING_HETZNER_HOST" in workflow
    assert "secrets.SCAS_STAGING_HETZNER_SSH_KEY" in workflow
    assert "secrets.SCAS_STAGING_HETZNER_USER" in workflow
    assert "SCAS_RUNTIME_DB: scas_runtime_staging" in workflow
    assert "SCAS_RUNTIME_DB_OWNER: scas_runtime_staging_app" in workflow
    assert "SCAS_RUNTIME_ROOT: /opt/scas/runtime/staging" in workflow
    assert "SCAS_REMOTE_MIGRATIONS_DIR: /opt/scas/migrations/hetzner/postgres" in workflow
    assert "scripts/hetzner/bootstrap_runtime_plane.sh" in workflow
    assert "--migrations-dir \"${SCAS_REMOTE_MIGRATIONS_DIR}\"" in workflow
    assert "SELECT count(*) FROM runtime.runtime_runs;" in workflow


def test_staging_runtime_bootstrap_workflow_does_not_rebuild_or_log_secrets() -> None:
    workflow = load_staging_runtime_bootstrap_workflow()

    assert "--rebuild" not in workflow
    assert "printf 'HETZNER_HOST=%s" not in workflow
    assert "printf 'HETZNER_USER=%s" not in workflow
    assert "printf 'HETZNER_SSH_KEY=%s" not in workflow
    assert "ssh-keygen -y -f" in workflow
    assert "HETZNER_SSH_KEY must contain the complete private OpenSSH key block" in workflow
    assert "The configured key is missing the expected OpenSSH private key header" in workflow
    assert "Expected first line" not in workflow


def test_tenant_ui_deploy_workflow_is_manual_only_and_builds_first() -> None:
    assert TENANT_UI_DEPLOY_WORKFLOW_PATH.exists()
    workflow = load_tenant_ui_deploy_workflow()

    assert "workflow_dispatch:" in workflow
    assert "target_environment:" in workflow
    assert "apply_deploy:" in workflow
    assert "default: false" in workflow
    assert "ui_app:" in workflow
    assert "- liquisto-workbench" in workflow
    assert "deploy/liquisto-workbench/Dockerfile" in workflow
    assert "scas-liquisto-workbench:${GITHUB_SHA}" in workflow
    assert "scas-liquisto-workbench.override.yml" in workflow
    assert "docker build" in workflow
    assert "docker save" in workflow
    assert "tenant-ui-deploy-plan" in workflow
    assert "sync_cloudflare_dns:" in workflow


def test_tenant_ui_deploy_workflow_requires_auth_evidence_for_mutation() -> None:
    workflow = load_tenant_ui_deploy_workflow()

    assert "upstream_auth_evidence_url:" in workflow
    assert "owner_principal_id:" in workflow
    assert "upstream_auth_evidence_url is required when apply_deploy=true" in workflow
    assert "owner_principal_id must be a non-secret stable id" in workflow
    assert "confirm_production must be true for production deploys" in workflow
    assert "SCAS_STAGING_UI_SESSION_CONTEXT_JSON" in workflow
    assert "SCAS_PROD_UI_SESSION_CONTEXT_JSON" in workflow
    assert "SCAS_STAGING_UI_LOGIN_USERS_JSON" in workflow
    assert "SCAS_PROD_UI_LOGIN_USERS_JSON" in workflow
    assert f"SCAS_STAGING_{DEFAULT_TENANT_OWNER_PRINCIPAL_ENV_NAME}" in workflow
    assert f"SCAS_PROD_{DEFAULT_TENANT_OWNER_PRINCIPAL_ENV_NAME}" in workflow
    assert f"SCAS_STAGING_{DASKUECHENHAUS_OWNER_PRINCIPAL_ENV_NAME}" in workflow
    assert f"SCAS_PROD_{DASKUECHENHAUS_OWNER_PRINCIPAL_ENV_NAME}" in workflow
    assert f"SCAS_STAGING_{TENANT_KINDERHAUS_OWNER_PRINCIPAL_ENV_NAME}" in workflow
    assert f"SCAS_PROD_{TENANT_KINDERHAUS_OWNER_PRINCIPAL_ENV_NAME}" in workflow
    assert "Unsupported owner principal mapping for staging tenant ${TENANT_ID}" in workflow
    assert "Unsupported owner principal mapping for prod tenant ${TENANT_ID}" in workflow
    assert "login_url must be an https URL when provided" in workflow
    assert "SCAS_UI_LOGIN_URL" in workflow
    assert 'SCAS_STAGING_TENANT_ADMIN_TOKEN:-${SCAS_STAGING_CONTROL_API_TOKEN:-}' in workflow
    assert 'SCAS_PROD_TENANT_ADMIN_TOKEN:-${SCAS_PROD_CONTROL_API_TOKEN:-}' in workflow
    assert '"membership_id": f"tm-{tenant_id}-initial-owner"' in workflow
    assert "UI_SESSION_CONTEXT_JSON_B64=" in workflow
    assert "UI_LOGIN_USERS_JSON_B64=" in workflow
    assert "for secret_value in" in workflow
    assert 'if [ -n "${secret_value}" ]; then' in workflow
    assert "echo \"::add-mask::${secret_value}\"" in workflow
    assert "label=com.docker.compose.project=${COMPOSE_PROJECT}" in workflow
    assert "label=com.docker.compose.service=${SERVICE_NAME}" in workflow
    assert "-f \"${EXISTING_COMPOSE_PATH}\"" not in workflow
    assert "-f \"${REMOTE_OVERRIDE_PATH}\"" in workflow
    assert "legacy compose files and .env are not read" in workflow
    assert "Waiting for tenant UI health check (${attempt}/30)" in workflow
    assert "SCAS_UI_AUTH_MODE=%s" in workflow
    assert "SCAS_UI_LOGIN_USERS_JSON" in workflow
    assert "SCAS_UI_UPSTREAM_AUTH_TRUSTED=true" in workflow
    assert "SCAS_UI_CONTAINER_PORT" in workflow
    assert "SCAS_UI_HEALTH_PATH" in workflow
    assert "Create Cloudflare Origin certificate" in workflow
    assert "LIQUISTO_CLOUDFLARE_API_TOKEN" in workflow
    assert "LIQUISTO_CLOUDFLARE_ZONE_ID" in workflow
    assert "KHH_CLOUDFLARE_API_TOKEN" in workflow
    assert "KHH_CLOUDFLARE_ZONE_ID" in workflow
    assert "skipping origin certificate creation" in workflow
    assert "target host must already have a certificate" in workflow
    assert "/client/v4/certificates" in workflow
    assert "tenant-ui-origin-cert/origin.pem" in workflow
    assert 'cert_hostnames+=("www.${REVERSE_PROXY_CERT_HOSTNAME}")' in workflow
    assert '"hostnames": hostnames' in workflow
    assert "Cloudflare DNS sync is only wired for approved tenant UI hostnames" in workflow
    assert "tenant_kinderhaus:kinderhaus-heuschrecken.cloud" in workflow
    assert "Cloudflare DNS sync hostname is not approved for ${TENANT_ID}" in workflow
    assert "Sync Cloudflare DNS to deployment host" in workflow
    assert 'delete_records("A", f"www.{hostname}")' in workflow
    assert 'delete_records("AAAA", f"www.{hostname}")' in workflow
    assert "synced-to-deployment-host" in workflow


def test_tenant_ui_deploy_workflow_has_rollback_guard() -> None:
    workflow = load_tenant_ui_deploy_workflow()

    assert "previous_image" in workflow
    assert "Post-deploy health check failed." in workflow
    assert "Rolled back to previous image" in workflow
    assert 'health_path="/"' in workflow
    assert "health_path=\"/\"" in workflow
    assert "tenant-ui-deployment-evidence" in workflow
    assert "manage_reverse_proxy:" in workflow
    assert "reverse_proxy_config_path must stay under /etc/nginx/sites-available" in workflow
    assert "nginx -t" in workflow
    assert 'if [ -L "${nginx_enabled}" ]; then' in workflow
    assert "nginx-sites-enabled-conflicts" in workflow
    assert "restore_nginx_conflicts" in workflow
    assert 'rm -f "${enabled_entry}"' in workflow
    assert 'conflicting server name \\"${reverse_proxy_hostname}\\"' in workflow
    assert 'reverse_proxy_server_names="${TENANT_HOSTNAME} www.${TENANT_HOSTNAME}"' in workflow
    assert "server_name ${reverse_proxy_server_names};" in workflow
    assert "systemctl reload nginx" in workflow
    assert "nginx -s reload" in workflow
    assert "systemctl start nginx" in workflow
    assert "reverse_proxy_attempt" in workflow
    assert "Waiting for reverse proxy origin check for ${reverse_proxy_hostname}" in workflow
    assert "Reverse proxy origin check failed for ${reverse_proxy_hostname}." in workflow
    assert "tail -n 80 /var/log/nginx/error.log" in workflow
    assert 'docker logs --tail 80 "${service_id}"' in workflow
    assert "Reverse proxy:" in workflow
    assert "Reverse proxy server names:" in workflow
    assert "Origin certificate:" in workflow
    assert "expected_content_marker=\"Liquisto workspace\"" in workflow
    assert 'forbidden_content_marker="daskuechenhaus"' in workflow
    assert 'expected_content_marker="Leitungs-Cockpit"' in workflow
    assert 'forbidden_content_marker="liquisto"' in workflow
    assert "Post-deploy content check failed" in workflow
    assert "forbidden cross-tenant marker" in workflow
    assert "Verify public tenant UI content" in workflow
    assert 'public_urls+=("https://www.${TENANT_HOSTNAME}${SCAS_UI_HEALTH_PATH}")' in workflow
    assert "Waiting for Cloudflare Access public check for ${public_url}" in workflow
    assert "cloudflareaccess" + ".com" in workflow
    assert "/cdn-cgi/access/login/" in workflow
    assert "Public tenant UI content check failed for ${public_url}." in workflow
    assert "Ensure KHH Cloudflare Access is fail closed" in workflow
    assert "tenant-ui-khh-access-evidence" in workflow
    assert "cf-access-authenticated-user-email-required" in workflow
    assert "proxy_set_header cf-access-authenticated-user-email" in workflow
    assert "Nginx requires cf-access-authenticated-user-email" in workflow
    assert "KHH_CLOUDFLARE_ACCOUNT_ID" in workflow
    assert "Cloudflare Access One-Time PIN email verification" in workflow
    assert "kontakt@konstantinmilonas.de" in workflow
    assert "Account Access API mutation: `performed-by-tenant-ui-deploy`" in workflow


def test_tenant_admin_bootstrap_workflow_is_manual_and_sanitized() -> None:
    assert TENANT_ADMIN_BOOTSTRAP_WORKFLOW_PATH.exists()
    workflow = load_tenant_admin_bootstrap_workflow()

    assert "workflow_dispatch:" in workflow
    assert "target_environment:" in workflow
    assert "apply_bootstrap:" in workflow
    assert "confirm_production:" in workflow
    assert "SCAS_STAGING_CONTROL_API_TOKEN" in workflow
    assert "SCAS_PROD_CONTROL_API_TOKEN" in workflow
    assert f"SCAS_STAGING_{DEFAULT_TENANT_OWNER_PRINCIPAL_ENV_NAME}" in workflow
    assert f"SCAS_PROD_{DEFAULT_TENANT_OWNER_PRINCIPAL_ENV_NAME}" in workflow
    assert f"SCAS_STAGING_{DASKUECHENHAUS_OWNER_PRINCIPAL_ENV_NAME}" in workflow
    assert f"SCAS_PROD_{DASKUECHENHAUS_OWNER_PRINCIPAL_ENV_NAME}" in workflow
    assert f"SCAS_STAGING_{DASKUECHENHAUS_ADDITIONAL_ADMIN_PRINCIPALS_ENV_NAME}" in workflow
    assert f"SCAS_PROD_{DASKUECHENHAUS_ADDITIONAL_ADMIN_PRINCIPALS_ENV_NAME}" in workflow
    assert "staging:daskuechenhaus)" in workflow
    assert "prod:daskuechenhaus)" in workflow
    assert "Unsupported tenant owner bootstrap target" in workflow
    assert "Missing ${OWNER_PRINCIPAL_SECRET_NAME}." in workflow
    assert "Owner principal: stored in environment-scoped GitHub secret; not printed" in workflow
    assert (
        "Additional admin principals: stored in environment-scoped GitHub secret; not printed"
        in workflow
    )
    assert "Additional admin principal ids must be non-secret stable ids" in workflow
    assert "additional_admin_membership_count" in workflow
    assert "scas-tenant-admin-bootstrap/1.0" in workflow
    assert 'context.get("users", [])' in workflow
    assert 'membership.get("membership_id") == membership_id' in workflow
    assert "tenant-admin-bootstrap-evidence/bootstrap.md" in workflow
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in workflow
    assert "/tenant-admin/tenants/{tenant_id}/memberships" in workflow
    assert "Owner principal id must be a non-secret stable id, not an email address." in workflow


def test_tenant_cloudflare_evidence_workflow_is_manual_and_hides_origin() -> None:
    assert TENANT_CLOUDFLARE_EVIDENCE_WORKFLOW_PATH.exists()
    workflow = load_tenant_cloudflare_evidence_workflow()

    assert "workflow_dispatch:" in workflow
    assert "require_worker_route:" in workflow
    assert "apply_dns_cutover:" in workflow
    assert "origin_ipv4:" in workflow
    assert "confirm_hostname:" in workflow
    assert "default: liquisto.cloud" in workflow
    assert "LIQUISTO_CLOUDFLARE_ZONE_ID" in workflow
    assert "LIQUISTO_CLOUDFLARE_API_TOKEN" in workflow
    assert "SCAS_STAGING_CLOUDFLARE_EVIDENCE_TOKEN" not in workflow
    assert "SCAS_PROD_CLOUDFLARE_EVIDENCE_TOKEN" not in workflow
    assert "SCAS_STAGING_CLOUDFLARE_API_TOKEN" not in workflow
    assert "SCAS_PROD_CLOUDFLARE_API_TOKEN" not in workflow
    assert "Missing LIQUISTO_CLOUDFLARE_API_TOKEN" in workflow
    assert "Missing LIQUISTO_CLOUDFLARE_ZONE_ID" in workflow
    assert "DNS cutover is only allowed for liquisto.cloud" in workflow
    assert "confirm_hostname must match hostname when apply_dns_cutover=true" in workflow
    assert "export CLOUDFLARE_API_TOKEN" in workflow
    assert "export CLOUDFLARE_ZONE_ID" in workflow
    assert "upsert(\"A\", hostname, origin_ipv4)" in workflow
    assert "upsert(\"CNAME\", f\"www.{hostname}\", hostname)" in workflow
    assert "Apex A record cutover" in workflow
    assert "WWW CNAME cutover" in workflow
    assert "/dns_records?type={record_type}&name=" in workflow
    assert "/settings/ssl" in workflow
    assert "/workers/routes?per_page=100" in workflow
    assert "Origin record content: not printed" in workflow
    assert "tenant-cloudflare-evidence/evidence.md" in workflow
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in workflow


def test_tenant_cloudflare_dns_cutover_workflow_is_guarded_and_hides_origin() -> None:
    assert TENANT_CLOUDFLARE_DNS_CUTOVER_WORKFLOW_PATH.exists()
    workflow = load_tenant_cloudflare_dns_cutover_workflow()

    assert "workflow_dispatch:" in workflow
    assert "default: liquisto.cloud" in workflow
    assert "origin_ipv4:" in workflow
    assert "apply_changes:" in workflow
    assert "default: false" in workflow
    assert "confirm_hostname:" in workflow
    assert "hostname must be liquisto.cloud" in workflow
    assert "confirm_hostname must match hostname when apply_changes=true" in workflow
    assert "LIQUISTO_CLOUDFLARE_ZONE_ID" in workflow
    assert "LIQUISTO_CLOUDFLARE_API_TOKEN" in workflow
    assert "/dns_records" in workflow
    assert '"type": record_type' in workflow
    assert '"proxied": True' in workflow
    assert '"ttl": 1' in workflow
    assert "Apex origin content: not printed" in workflow
    assert "origin_content_printed" in workflow
    assert "tenant-cloudflare-dns-cutover/evidence.md" in workflow
    assert "SCAS_STAGING_CLOUDFLARE_EVIDENCE_TOKEN" not in workflow
    assert "SCAS_PROD_CLOUDFLARE_EVIDENCE_TOKEN" not in workflow


def test_liquisto_cloudflare_access_workflow_restricts_public_workbench() -> None:
    assert LIQUISTO_CLOUDFLARE_ACCESS_WORKFLOW_PATH.exists()
    workflow = load_liquisto_cloudflare_access_workflow()

    assert "workflow_dispatch:" in workflow
    assert "apply_changes:" in workflow
    assert "confirm_production:" in workflow
    assert "environment:" in workflow
    assert "name: production" in workflow
    assert "confirm_production must be true when apply_changes=true" in workflow
    assert "confirm_hostname must match primary_hostname when apply_changes=true" in workflow
    assert "LIQUISTO_CLOUDFLARE_ACCOUNT_ID" in workflow
    assert "LIQUISTO_CLOUDFLARE_API_TOKEN" in workflow
    assert "default: liquisto.cloud" in workflow
    assert "redirect_hostnames:" in workflow
    assert "default: www.liquisto.cloud" in workflow
    assert "default: konstantin@liquisto.com aernout@liquisto.com" in workflow
    assert (
        "allowed_emails must be exactly konstantin@liquisto.com and aernout@liquisto.com"
        in workflow
    )
    assert "Cloudflare Access One-Time PIN email verification" in workflow
    assert "No Cloudflare Access One-Time PIN identity provider is configured" in workflow
    assert 'payload["same_site_cookie_attribute"] = "lax"' in workflow
    assert 'payload["path_cookie_attribute"] = False' in workflow
    assert "Liquisto Access app still has path-scoped cookies enabled" in workflow
    assert "Cookie scope after:" in workflow
    assert "started-before-cloudflare-api-call" in workflow
    assert "must allow account-scoped Cloudflare Access application, policy" in workflow
    assert "zone-scoped Rulesets edit" in workflow
    assert "http_request_dynamic_redirect" in workflow
    assert r'"code"\s*:\s*10003\b' in workflow
    assert "liquisto_www_to_apex" in workflow
    assert 'concat("https://liquisto.cloud", http.request.uri.path)' in workflow
    assert "Liquisto Access may only protect liquisto.cloud directly." in workflow
    assert "organization, and identity-provider operations" not in workflow
    assert "access/organizations" not in workflow
    assert "Organization scope: `not read or modified by this Liquisto workflow`" in workflow
    assert "Canonical redirect status:" in workflow
    assert "Das Küchenhaus CRM" not in workflow
    assert "SCAS Liquisto Workbench allowed users" in workflow
    assert (
        'cf_request("DELETE", '
        'f"/accounts/{account_id}/access/apps/{app[\'id\']}/policies/{policy[\'id\']}")'
        in workflow
    )
    assert "Verify public Access redirect" in workflow
    assert "cloudflareaccess" + ".com" in workflow
    assert "liquisto-access-evidence" in workflow
    assert "DKH_CLOUDFLARE_API_TOKEN" not in workflow
    assert "SCAS_PROD_CLOUDFLARE_DEPLOY_TOKEN" not in workflow


def test_khh_cloudflare_access_workflow_restricts_public_workbench() -> None:
    assert KHH_CLOUDFLARE_ACCESS_WORKFLOW_PATH.exists()
    workflow = load_khh_cloudflare_access_workflow()

    assert "workflow_dispatch:" in workflow
    assert "apply_changes:" in workflow
    assert "confirm_production:" in workflow
    assert "environment:" in workflow
    assert "name: production" in workflow
    assert "confirm_production must be true when apply_changes=true" in workflow
    assert "confirm_hostname must match primary_hostname when apply_changes=true" in workflow
    assert "KHH_CLOUDFLARE_ACCOUNT_ID" in workflow
    assert "KHH_CLOUDFLARE_API_TOKEN" in workflow
    assert "default: kinderhaus-heuschrecken.cloud www.kinderhaus-heuschrecken.cloud" in workflow
    assert "default: kontakt@konstantinmilonas.de" in workflow
    assert "hostnames must be exactly the KHH apex and www hostnames." in workflow
    assert "allowed_emails must be exactly kontakt@konstantinmilonas.de." in workflow
    assert "Cloudflare Access One-Time PIN email verification" in workflow
    assert "No Cloudflare Access One-Time PIN identity provider is configured" in workflow
    assert 'payload["same_site_cookie_attribute"] = "lax"' in workflow
    assert 'payload["path_cookie_attribute"] = False' in workflow
    assert "KHH Access app still has path-scoped cookies enabled" in workflow
    assert "Cookie scope after:" in workflow
    assert "must allow account-scoped Cloudflare Access application, policy" in workflow
    assert "Verify public Access redirect" in workflow
    assert "Expected Cloudflare Access login redirect" in workflow
    assert "Waiting for Cloudflare Access login redirect" in workflow
    assert "cloudflareaccess" + ".com" in workflow
    assert "khh-access-evidence" in workflow
    assert "LIQUISTO_CLOUDFLARE_API_TOKEN" not in workflow
    assert "DKH_CLOUDFLARE_API_TOKEN" not in workflow
    assert "SCAS_PROD_CLOUDFLARE_DEPLOY_TOKEN" not in workflow


def test_es_daskuechenhaus_site_deploy_workflow_is_protected() -> None:
    assert not ES_DASKUECHENHAUS_SITE_DEPLOY_WORKFLOW_PATH.exists()
    for workflow_path in (REPO_ROOT / ".github" / "workflows").glob("*.yml"):
        workflow = workflow_path.read_text(encoding="utf-8")
        assert "workers/es-daskuechenhaus-site" not in workflow
        assert "dkh-site:typecheck" not in workflow
        assert "dkh-site:check" not in workflow


def test_es_daskuechenhaus_crm_deploy_workflow_cuts_over_to_nextjs_origin() -> None:
    assert ES_DASKUECHENHAUS_CRM_DEPLOY_WORKFLOW_PATH.exists()
    workflow = load_es_daskuechenhaus_crm_deploy_workflow()

    assert "workflow_dispatch:" in workflow
    assert "apply_deploy:" in workflow
    assert "confirm_production:" in workflow
    assert "environment:" in workflow
    assert "name: production" in workflow
    assert "confirm_production must be true when apply_deploy=true" in workflow
    assert "apps/dkh-crm" in workflow
    assert "npm run dkh-crm:check" in workflow
    assert "dkh-crm-standalone.tar.gz" in workflow
    assert "daskuechenhaus-crm.service" in workflow
    assert "es-daskuechenhaus.de www.es-daskuechenhaus.de" in workflow
    assert "es-daskuechenhaus-crm" in workflow
    assert "DKH_CLOUDFLARE_ZONE_ID" in workflow
    assert "DKH_CLOUDFLARE_API_TOKEN" in workflow
    assert "Create Cloudflare Origin certificate" in workflow
    assert "/client/v4/certificates" in workflow
    assert "/etc/ssl/cloudflare" in workflow
    assert "/workers/routes" in workflow
    assert "/dns_records" in workflow
    assert "Access application/policies: `preserved; not modified by this workflow`" in workflow
    assert "workers/es-daskuechenhaus-site" not in workflow
    assert "es-daskuechenhaus-site" not in workflow


def test_es_daskuechenhaus_mail_runtime_sync_workflow_is_hetzner_only() -> None:
    assert ES_DASKUECHENHAUS_MAIL_RUNTIME_SYNC_WORKFLOW_PATH.exists()
    workflow = load_es_daskuechenhaus_mail_runtime_sync_workflow()

    assert "workflow_dispatch:" in workflow
    assert "apply_sync:" in workflow
    assert "confirm_production:" in workflow
    assert "DKH_MAIL_K_MILONAS_IMAP_USERNAME" in workflow
    assert "DKH_MAIL_K_MILONAS_IMAP_PASSWORD" in workflow
    assert "DKH_MAIL_K_MILONAS_SMTP_USERNAME" in workflow
    assert "DKH_MAIL_K_MILONAS_SMTP_PASSWORD" in workflow
    assert "DKH_MAIL_K_MILONAS_FROM_ADDRESS" in workflow
    assert "DKH_EMAIL_IMAP_HOST" in workflow
    assert "DKH_EMAIL_IMAP_PORT" in workflow
    assert "DKH_EMAIL_SMTP_HOST" in workflow
    assert "DKH_EMAIL_SMTP_PORT" in workflow
    assert "SCAS_PROD_HETZNER_HOST" in workflow
    assert "SCAS_PROD_HETZNER_SSH_KEY" in workflow
    assert "SCAS_PROD_HETZNER_USER" in workflow
    assert "confirm_production must be true when apply_sync=true" in workflow
    assert "/etc/daskuechenhaus/mail.env" in workflow
    assert "0003_mail_runtime_configuration.sql" in workflow
    assert "sudo -n -u postgres psql -d tenant_daskuechenhaus" in workflow
    assert "Secret values in artifact: `none`" in workflow
    assert "wrangler" not in workflow
    assert "CLOUDFLARE_API_TOKEN" not in workflow


def test_es_daskuechenhaus_mail_runtime_sync_exports_multiline_ssh_key_safely() -> None:
    workflow = load_es_daskuechenhaus_mail_runtime_sync_workflow()

    assert "TARGET_HETZNER_SSH_KEY<<__SCAS_HETZNER_SSH_KEY__" in workflow
    assert 'printf \'%s\\n\' "${target_key}"' in workflow
    assert "echo '__SCAS_HETZNER_SSH_KEY__'" in workflow
    assert "value contains reserved delimiter" in workflow
    assert "printf 'TARGET_HETZNER_SSH_KEY=%s" not in workflow


def test_es_daskuechenhaus_admin_api_deploy_workflow_is_production_guarded() -> None:
    assert ES_DASKUECHENHAUS_ADMIN_API_DEPLOY_WORKFLOW_PATH.exists()
    workflow = load_es_daskuechenhaus_admin_api_deploy_workflow()

    assert "workflow_dispatch:" in workflow
    assert "apply_deploy:" in workflow
    assert "confirm_production:" in workflow
    assert "environment:" in workflow
    assert "name: production" in workflow
    assert "SCAS_PROD_HETZNER_HOST" in workflow
    assert "SCAS_PROD_HETZNER_SSH_KEY" in workflow
    assert "SCAS_PROD_HETZNER_USER" in workflow
    assert "DKH_OBJECT_STORAGE_ACCESS_KEY_ID" in workflow
    assert "DKH_OBJECT_STORAGE_SECRET_ACCESS_KEY" in workflow
    assert "/etc/daskuechenhaus/object-storage.env" in workflow
    assert "confirm_production must be true when apply_deploy=true" in workflow
    assert "TARGET_HETZNER_SSH_KEY<<__SCAS_HETZNER_SSH_KEY__" in workflow
    assert "HETZNER_SSH_KEY must contain the complete private OpenSSH key block" in workflow
    assert "wrangler" not in workflow
    assert "CLOUDFLARE_API_TOKEN" not in workflow


def test_es_daskuechenhaus_admin_api_deploy_runs_preflight_and_smoke() -> None:
    workflow = load_es_daskuechenhaus_admin_api_deploy_workflow()

    assert "0008_customer_search_first_deduplication.sql" in workflow
    assert "0009_customer_file_desktop.sql" in workflow
    assert "0010_customer_case_document_metadata.sql" in workflow
    assert "0011_customer_document_object_storage.sql" in workflow
    assert "0012_carat_prjz_imports.sql" in workflow
    assert "0013_supplier_order_confirmations.sql" in workflow
    assert "0014_lead_intake.sql" in workflow
    assert "0015_mobile_app_identities.sql" in workflow
    assert "0016_mobile_app_konstantin_activation.sql" in workflow
    assert "REMOTE_DOCUMENT_MIGRATION" in workflow
    assert "REMOTE_OBJECT_STORAGE_MIGRATION" in workflow
    assert "REMOTE_CARAT_IMPORT_MIGRATION" in workflow
    assert "REMOTE_SUPPLIER_CONFIRMATION_MIGRATION" in workflow
    assert "REMOTE_MOBILE_APP_IDENTITIES_MIGRATION" in workflow
    assert "REMOTE_MOBILE_KONSTANTIN_ACTIVATION_MIGRATION" in workflow
    assert "daskuechenhaus_admin_api.py" in workflow
    assert "daskuechenhaus-admin-api.service" in workflow
    assert (
        "Duplicate active customer emails block Search-First hard-bounce migration"
        not in workflow
    )
    assert (
        "Duplicate active primary phone numbers block Search-First hard-bounce migration"
        in workflow
    )
    assert (
        "Duplicate active primary mobile numbers block Search-First hard-bounce migration"
        in workflow
    )
    assert "Invalid customer source values block Search-First source constraint" in workflow
    assert "sudo -n -u postgres psql -d tenant_daskuechenhaus -v ON_ERROR_STOP=1" in workflow
    assert "systemctl restart daskuechenhaus-admin-api.service" in workflow
    assert "http://127.0.0.1:8715/health" in workflow
    assert "Admin API did not become reachable on 127.0.0.1:8715" in workflow
    assert "http://127.0.0.1:8715/customers/search?q=abc" in workflow
    assert "Secret values in artifact: `none`" in workflow


def test_es_daskuechenhaus_access_workflow_does_not_write_policy_mfa_config() -> None:
    workflow = load_es_daskuechenhaus_access_workflow()

    policy_payload = workflow.split("          def policy_payload", 1)[1].split(
        "          def policy_emails",
        1,
    )[0]
    disabled_policy_payload = workflow.split(
        "          def with_disabled_mfa_policy",
        1,
    )[1].split("          def app_name_for_hostname", 1)[0]

    assert "mfa_config" not in policy_payload
    assert '                  "mfa_config",' not in disabled_policy_payload
    assert 'payload.pop("mfa_config", None)' in disabled_policy_payload
    assert "if not mfa_config:" in workflow


def test_es_daskuechenhaus_customer_database_reset_is_production_guarded() -> None:
    assert ES_DASKUECHENHAUS_CUSTOMER_DATABASE_RESET_WORKFLOW_PATH.exists()
    workflow = load_es_daskuechenhaus_customer_database_reset_workflow()

    assert "workflow_dispatch:" in workflow
    assert "apply_reset:" in workflow
    assert "confirm_production:" in workflow
    assert "confirmation_text:" in workflow
    assert "environment:" in workflow
    assert "name: production" in workflow
    assert "apply_reset must be true for a destructive reset" in workflow
    assert "confirm_production must be true for a production reset" in workflow
    assert "confirmation_text does not match the required phrase" in workflow
    assert "Ja, produktive DKH-Kundendatenbank leeren." in workflow
    assert "SCAS_PROD_HETZNER_HOST" in workflow
    assert "SCAS_PROD_HETZNER_SSH_KEY" in workflow
    assert "SCAS_PROD_HETZNER_USER" in workflow
    assert "TARGET_HETZNER_SSH_KEY<<__SCAS_HETZNER_SSH_KEY__" in workflow
    assert "HETZNER_SSH_KEY must contain the complete private OpenSSH key block" in workflow
    assert "wrangler" not in workflow
    assert "CLOUDFLARE_API_TOKEN" not in workflow


def test_es_daskuechenhaus_customer_database_reset_scope_and_evidence() -> None:
    workflow = load_es_daskuechenhaus_customer_database_reset_workflow()

    assert "tenant_daskuechenhaus" in workflow
    assert "DELETE FROM app.customers" in workflow
    assert "DELETE FROM app.customer_cases" in workflow
    assert "DELETE FROM app.customer_addresses" in workflow
    assert "DELETE FROM app.customer_contacts" in workflow
    assert "DELETE FROM app.customer_file_sections" in workflow
    assert "DELETE FROM app.customer_case_sections" in workflow
    assert "DELETE FROM app.customer_case_notes" in workflow
    assert "DELETE FROM app.customer_case_documents" in workflow
    assert "DELETE FROM app.customer_case_audit_events" in workflow
    assert "DELETE FROM app.customer_case_participants" in workflow
    assert "DELETE FROM app.customer_case_project_profiles" in workflow
    assert "DELETE FROM app.tasks" in workflow
    assert "DELETE FROM app.appointments" in workflow
    assert "DELETE FROM app.email_case_links" in workflow
    assert "DELETE FROM app.email_assignment_suggestions" in workflow
    assert "DELETE FROM app.communication_events" in workflow
    assert "DELETE FROM app.users" not in workflow
    assert "DELETE FROM app.roles" not in workflow
    assert "DELETE FROM app.permissions" not in workflow
    assert "DELETE FROM app.customer_case_status_phases" not in workflow
    assert "DELETE FROM app.task_statuses" not in workflow
    assert "DELETE FROM app.email_accounts" not in workflow
    assert "Secret values in artifact: `none`" in workflow
    assert "customers-state.json" in workflow
    assert "customers=[]" in workflow
    assert "customer_cases=[]" in workflow
    assert "es-daskuechenhaus-customer-database-reset-evidence" in workflow


def test_production_readiness_workflow_exists() -> None:
    assert PRODUCTION_READINESS_WORKFLOW_PATH.exists()


def test_production_readiness_workflow_builds_non_secret_evidence() -> None:
    workflow = load_production_readiness_workflow()

    assert "workflow_dispatch:" in workflow
    assert "target_environment:" in workflow
    assert "certification_mode:" in workflow
    assert "evidence_source_mode:" in workflow
    assert "consume-existing" in workflow
    assert "recheck" in workflow
    assert "ci_run_url:" in workflow
    assert "security_governance_run_url:" in workflow
    assert "uv sync --frozen --extra dev --extra runtime" in workflow
    assert "uv lock --check" in workflow
    assert "uv run pytest" in workflow
    assert "uv run ruff check ." in workflow
    assert "uv run mypy" in workflow
    assert "scripts/runtime/skill_handler_coverage.py --check" in workflow
    assert "scripts/runtime/production_skill_instruction_packs.py --check" in workflow
    assert "scripts/runtime/validate_hooks_usage_model.py --check" in workflow
    assert "scripts/release/validate_production_recertification_policy.py --check" in workflow
    assert "scripts/runtime/scan_transition_signals.py --check" in workflow
    assert "scripts/runtime/validate_transition_evidence.py --check" in workflow
    assert "scripts/runtime/validate_capability_delta_transition_policy.py --check" in workflow
    assert "scripts/runtime/evaluate_intent_transition_traces.py --check" in workflow
    assert "scripts/runtime/evaluate_intent_transition_shadow_metrics.py --check" in workflow
    assert "scripts/runtime/validate_structured_evidence_extraction_decision.py --check" in workflow
    assert "scripts/runtime/validate_semantic_drift_guard.py --check" in workflow
    assert "scripts/security/validate_codeowners_coverage.py" in workflow
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
    assert "uv run python scripts/release/build_production_readiness_evidence.py" in workflow
    assert "--evidence-source-mode" in workflow
    assert "--ci-run-metadata production-evidence/ci-run.json" in workflow
    assert (
        "--security-governance-metadata "
        "production-evidence/security-governance-run.json"
    ) in workflow
    assert (
        "--security-governance-artifacts-dir "
        "production-evidence/security-governance"
    ) in workflow
    assert "production-evidence/security-governance/*.json" in workflow
    assert "production-readiness-evidence.json" in workflow
    assert "actions/upload-artifact" in workflow
    assert "gh run download" in workflow
    assert "live-runtime-handler-binding-evidence" in workflow


def test_production_readiness_workflow_consumes_upstream_evidence_by_default() -> None:
    workflow = load_production_readiness_workflow()

    assert "default: consume-existing" in workflow
    assert "EVIDENCE_SOURCE_MODE:" in workflow
    assert "Collect consumed CI and security evidence metadata" in workflow
    assert "production-evidence/ci-run.json" in workflow
    assert "production-evidence/security-governance-run.json" in workflow
    assert "--name security-evidence" in workflow
    assert "--dir production-evidence/security-governance" in workflow
    assert "ci_run_id" in workflow
    assert "security_run_id" in workflow
    assert workflow.count("inputs.evidence_source_mode == 'recheck'") >= 10
    assert "inputs.evidence_source_mode == 'consume-existing'" in workflow


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
    assert "confirm_production:" in workflow
    assert "CONFIRM_PRODUCTION: ${{ github.event_name == 'workflow_dispatch'" in workflow
    assert "inputs.confirm_production || false" in workflow
    assert "inputs.target_environment == 'prod' && 'production'" in workflow
    assert "confirm_production must be true for production retention cleanup." in workflow
    assert "CONFIRM_PRODUCTION='${CONFIRM_PRODUCTION}'" in workflow
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


def test_runtime_retention_cleanup_workflow_exports_multiline_ssh_key_safely() -> None:
    workflow = load_runtime_retention_cleanup_workflow()

    assert "HETZNER_SSH_KEY<<__SCAS_HETZNER_SSH_KEY__" in workflow
    assert 'printf \'%s\\n\' "${HETZNER_SSH_KEY}"' in workflow
    assert "echo '__SCAS_HETZNER_SSH_KEY__'" in workflow
    assert "value contains reserved delimiter" in workflow
    assert "printf 'HETZNER_SSH_KEY=%s" not in workflow


def test_github_governance_drift_workflow_is_scheduled_and_manual() -> None:
    workflow = load_github_governance_drift_workflow()

    assert "schedule:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "permissions:" in workflow
    assert "contents: read" in workflow
    assert "concurrency:" in workflow
    assert "timeout-minutes:" in workflow


def test_github_governance_drift_workflow_fetches_live_ruleset_and_uploads_evidence() -> None:
    workflow = load_github_governance_drift_workflow()

    assert "SCAS_GOVERNANCE_DRIFT_TOKEN" in workflow
    assert "validate_ruleset_config.py" in workflow
    assert "--fetch-live" in workflow
    assert "github-governance-drift.json" in workflow
    assert "github-governance-drift-evidence" in workflow
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in workflow
