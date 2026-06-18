from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "tenant-ui-deploy.yml"
DOCKERFILE_PATH = REPO_ROOT / "deploy" / "streamlit-business-ui" / "Dockerfile"
RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "streamlit-business-ui-deployment.md"
ADMIN_BOOTSTRAP_RUNBOOK_PATH = (
    REPO_ROOT / "docs" / "runbooks" / "liquisto-tenant-admin-bootstrap.md"
)
ROLLBACK_RUNBOOK_PATH = (
    REPO_ROOT / "docs" / "runbooks" / "liquisto-tenant-rollback-deprovisioning.md"
)
README_PATH = REPO_ROOT / "apps" / "streamlit_business_ui" / "README.md"
RELEASE_GATE_PATH = REPO_ROOT / "docs" / "runbooks" / "liquisto-tenant-release-gate.md"
DOCS_INDEX_PATH = REPO_ROOT / "docs" / "README.md"


def test_streamlit_business_ui_container_definition_is_production_targeted() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in dockerfile
    assert "apps/streamlit_business_ui" in dockerfile
    assert "examples/tenants" in dockerfile
    assert "python -m pip install --no-cache-dir \".[ui]\"" in dockerfile
    assert "USER scas" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "_stcore/health" in dockerfile
    assert 'CMD ["streamlit", "run", "apps/streamlit_business_ui/app.py"]' in dockerfile


def test_tenant_ui_deploy_workflow_is_manual_and_fail_closed() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "target_environment:" in workflow
    assert "- staging" in workflow
    assert "- prod" in workflow
    assert "apply_deploy:" in workflow
    assert "default: false" in workflow
    assert "confirm_production:" in workflow
    assert "upstream_auth_evidence_url:" in workflow
    assert "upstream_auth_evidence_url is required when apply_deploy=true" in workflow
    assert "confirm_production must be true for production deploys" in workflow
    assert "remote_override_path must stay under /opt" in workflow


def test_tenant_ui_deploy_workflow_builds_image_and_uploads_plan_artifact() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "deploy/streamlit-business-ui/Dockerfile" in workflow
    assert "docker build" in workflow
    assert "docker save" in workflow
    assert "scas-streamlit-business-ui-image.tar.gz" in workflow
    assert "tenant-ui-deploy-plan" in workflow
    assert "no remote host was changed" in workflow


def test_tenant_ui_deploy_workflow_resolves_environment_secrets() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "SCAS_STAGING_HETZNER_HOST" in workflow
    assert "SCAS_STAGING_HETZNER_SSH_KEY" in workflow
    assert "SCAS_STAGING_UI_SESSION_CONTEXT_JSON" in workflow
    assert "SCAS_STAGING_TENANT_ADMIN_TOKEN" in workflow
    assert "SCAS_STAGING_CONTROL_API_TOKEN" in workflow
    assert "SCAS_STAGING_LIQUISTO_OWNER_PRINCIPAL_ID" in workflow
    assert "SCAS_PROD_HETZNER_HOST" in workflow
    assert "SCAS_PROD_HETZNER_SSH_KEY" in workflow
    assert "SCAS_PROD_UI_SESSION_CONTEXT_JSON" in workflow
    assert "SCAS_PROD_TENANT_ADMIN_TOKEN" in workflow
    assert "SCAS_PROD_CONTROL_API_TOKEN" in workflow
    assert "SCAS_PROD_LIQUISTO_OWNER_PRINCIPAL_ID" in workflow
    assert '"membership_id": f"tm-{tenant_id}-initial-owner"' in workflow
    assert "::add-mask::${UI_SESSION_CONTEXT_JSON_B64}" in workflow
    assert "Deprecated compatibility input; SCAS-managed deploy does not read it" in workflow
    assert "label=com.docker.compose.project=${COMPOSE_PROJECT}" in workflow
    assert "-f \"${EXISTING_COMPOSE_PATH}\"" not in workflow
    assert "-f \"${REMOTE_OVERRIDE_PATH}\"" in workflow
    assert "SCAS_UI_AUTH_MODE=required" in workflow
    assert "SCAS_UI_TENANT_ID=%s" in workflow
    assert "SCAS_UI_UPSTREAM_AUTH_TRUSTED=true" in workflow
    assert "SCAS_UI_SESSION_CONTEXT_JSON" in workflow


def test_tenant_ui_deploy_workflow_has_rollback_and_evidence_contract() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "previous_image" in workflow
    assert "Post-deploy health check failed." in workflow
    assert "Rolled back to previous image" in workflow
    assert '127.0.0.1:${LOCAL_HEALTH_PORT}:8501' in workflow
    assert "for attempt in $(seq 1 30)" in workflow
    assert "Waiting for Streamlit health check (${attempt}/30)" in workflow
    assert "restart: unless-stopped" in workflow
    assert "legacy compose files and .env are not read" in workflow
    assert "tenant-ui-deployment-evidence" in workflow
    assert "deployment.md" in workflow
    assert "HETZNER_SSH_KEY must contain the complete private OpenSSH key block" in workflow


def test_streamlit_deployment_runbook_is_linked_from_operational_docs() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    readme = README_PATH.read_text(encoding="utf-8")
    release_gate = RELEASE_GATE_PATH.read_text(encoding="utf-8")

    assert "tenant-ui-deploy.yml" in runbook
    assert "deploy/streamlit-business-ui/Dockerfile" in runbook
    assert "SCAS_UI_TENANT_ID=liquisto" in runbook
    assert "SCAS_PROD_UI_SESSION_CONTEXT_JSON" in runbook
    assert "SCAS_STAGING_LIQUISTO_OWNER_PRINCIPAL_ID" in runbook
    assert "SCAS_PROD_LIQUISTO_OWNER_PRINCIPAL_ID" in runbook
    assert "tenant-admin-bootstrap.yml" in runbook
    assert "Rollback Behavior" in runbook
    assert "Launch Gate Mapping" in runbook
    assert "docs/runbooks/streamlit-business-ui-deployment.md" in readme
    assert "tenant-ui-deploy.yml" in release_gate


def test_liquisto_admin_bootstrap_runbook_keeps_owner_data_out_of_repo() -> None:
    runbook = ADMIN_BOOTSTRAP_RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "approved operational source" in runbook
    assert "Do not hardcode the owner" in runbook
    assert "tenant-admin" in runbook
    assert "Control API" in runbook
    assert "non-admin and cross-tenant access attempts fail closed" in runbook
    assert "email addresses" in runbook
    assert "session JSON" in runbook


def test_liquisto_rollback_runbook_is_tenant_local_and_dry_run_first() -> None:
    runbook = ROLLBACK_RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "tenant-local" in runbook
    assert "default mode: suspend dry-run" in runbook
    assert "Confirm no other tenant references" in runbook
    assert "disabled tenant hostnames fail closed" in runbook
    assert "Deletion is irreversible" in runbook


def test_liquisto_launch_runbooks_are_indexed() -> None:
    docs_index = DOCS_INDEX_PATH.read_text(encoding="utf-8")
    release_gate = RELEASE_GATE_PATH.read_text(encoding="utf-8")
    deployment = RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "liquisto-tenant-admin-bootstrap.md" in docs_index
    assert "liquisto-tenant-rollback-deprovisioning.md" in docs_index
    assert "liquisto-tenant-admin-bootstrap.md" in release_gate
    assert "liquisto-tenant-rollback-deprovisioning.md" in release_gate
    assert "liquisto-tenant-admin-bootstrap.md" in deployment
    assert "liquisto-tenant-rollback-deprovisioning.md" in deployment
