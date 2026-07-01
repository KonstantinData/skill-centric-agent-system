from __future__ import annotations

from pathlib import Path

import pytest

from scripts.runtime.live_dev_e2e import (
    FIRST_TARGET_TENANT_SUITE,
    REDACTED_PRINCIPAL_ID,
    TARGET_TENANT_SUITES,
    _composition_request_summary,
    _run_denied_start_case,
    _tenant_task_variant,
    handler_binding_evidence_from_checkpoints,
)
from scripts.runtime.live_dev_e2e import (
    main as live_dev_e2e_main,
)
from scripts.runtime.postgres_concurrency_smoke import main as postgres_concurrency_smoke_main
from skill_centric_agent_system.runtime import JsonArtifactStore

REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_DEV_E2E_PATH = REPO_ROOT / "scripts" / "runtime" / "live_dev_e2e.py"
POSTGRES_CONCURRENCY_SMOKE_PATH = (
    REPO_ROOT / "scripts" / "runtime" / "postgres_concurrency_smoke.py"
)


def test_live_dev_e2e_gate_script_exists() -> None:
    assert LIVE_DEV_E2E_PATH.exists()


def test_live_dev_e2e_gate_documents_required_live_surfaces() -> None:
    source = LIVE_DEV_E2E_PATH.read_text(encoding="utf-8")

    assert "ControlPlaneClient" in source
    assert "open_runtime_store_session" in source
    assert 'mode="postgres"' in source
    assert "MinimalRuntimeLoop" in source
    assert "SCAS_RUNTIME_DATABASE_URL" in source
    assert "SCAS_CONTROL_API_TOKEN" in source
    assert "handler_binding_status" in source
    assert "skill_handlers" in source
    assert '"tenant"' in source
    assert "examples/tasks/tenant-research-task.json" in source
    assert "tenant-unknown-tenant" in source
    assert "tenant-missing-membership" in source
    assert "tenant-foreign-data-source" in source
    assert "tenant-tampered-authority" in source
    assert "SCAS_LIVE_E2E_REDACT_PRINCIPAL_ID" in source
    assert FIRST_TARGET_TENANT_SUITE in TARGET_TENANT_SUITES
    assert "daskuechenhaus" in TARGET_TENANT_SUITES
    assert "kinderhaus" in TARGET_TENANT_SUITES


def test_live_dev_e2e_target_tenant_suite_preserves_area_id_with_underscore() -> None:
    task = _tenant_task_variant(
        {
            "context": {
                "auth": {
                    "tenant_id": "demo-tenant",
                    "area_id": "demo-tenant",
                }
            }
        },
        tenant_id="tenant_kinderhaus",
        area_id="kinderhaus-heuschrecken",
        role_id="tenant_kinderhaus-public-researcher",
        membership_id="tm-tenant_kinderhaus-repository-maintainer",
        hostname="kinderhaus-heuschrecken.cloud",
        role_data_sources=("kinderhaus-public-website",),
    )

    auth = task["context"]["auth"]
    assert auth["tenant_id"] == "tenant_kinderhaus"
    assert auth["area_id"] == "kinderhaus-heuschrecken"
    assert auth["roles"] == ["tenant_kinderhaus-public-researcher"]


def test_live_dev_e2e_redacts_configured_secret_principal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    principal_id = "liqui" + "sto-prod-owner"
    monkeypatch.setenv("SCAS_LIVE_E2E_REDACT_PRINCIPAL_ID", principal_id)

    summary = _composition_request_summary(
        {
            "principal": {"kind": "user", "id": principal_id},
            "task": {"type": "research"},
        }
    )

    assert summary["principal_id"] == REDACTED_PRINCIPAL_ID


def test_live_dev_e2e_extracts_handler_binding_evidence(tmp_path: Path) -> None:
    artifacts = JsonArtifactStore(tmp_path)
    state_uri = artifacts.write_json(
        ("traces", "run-example", "checkpoints", "001-planner"),
        {
            "skill_handlers": [
                {
                    "name": "git-diff-analysis",
                    "version": "0.1.0",
                    "handler_id": "git-diff-analysis@0.1.0",
                }
            ]
        },
        redact=False,
    )

    evidence = handler_binding_evidence_from_checkpoints(
        ({"phase": "planner", "state_uri": state_uri},),
        artifact_root=tmp_path,
    )

    assert evidence["handler_binding_status"] == "passed"
    assert evidence["planner_checkpoint_uri"] == state_uri
    assert evidence["skill_handlers"] == [
        {
            "name": "git-diff-analysis",
            "version": "0.1.0",
            "handler_id": "git-diff-analysis@0.1.0",
        }
    ]


def test_live_dev_e2e_treats_inactive_tenant_as_expected_denial(
    tmp_path: Path,
) -> None:
    class InactiveTenantControlPlaneClient:
        def composition_context(self, _request: object) -> dict[str, object]:
            return {
                "composition_status": "accepted",
                "tenant_authority": {
                    "tenant_id": "tenant-under-test",
                    "area_id": "tenant-under-test",
                    "status": "inactive",
                },
            }

    result = _run_denied_start_case(
        label="tenant-inactive",
        task={
            "id": "task-tenant-under-test-research",
            "request": "Research the tenant-under-test website.",
            "constraints": {"write_access": False, "destructive_actions": False},
            "context": {
                "auth": {
                    "principal_id": "repository-maintainer",
                    "principal_type": "user",
                    "tenant_id": "tenant-under-test",
                    "area_id": "tenant-under-test",
                    "tenant_hostname": "tenant-under-test.example.invalid",
                    "membership_id": "tm-tenant-under-test-repository-maintainer",
                    "role_data_sources": ["tenant-under-test-website"],
                    "role_capabilities": ["research"],
                }
            },
        },
        store=object(),
        artifacts=JsonArtifactStore(tmp_path),
        control_plane_client=InactiveTenantControlPlaneClient(),
        environment="staging",
        run_id="run-live-test-tenant-inactive",
    )

    assert result["status"] == "passed"
    assert result["runtime_started"] is False
    assert result["error_type"] == "RuntimeTenantStatusError"


def test_live_dev_e2e_gate_requires_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SCAS_RUNTIME_DATABASE_URL", raising=False)

    with pytest.raises(SystemExit, match="SCAS_RUNTIME_DATABASE_URL"):
        live_dev_e2e_main(
            [
                "--task-file",
                str(REPO_ROOT / "examples" / "tasks" / "code-review-task.json"),
            ]
        )


def test_postgres_concurrency_smoke_script_exists_and_uses_postgres() -> None:
    source = POSTGRES_CONCURRENCY_SMOKE_PATH.read_text(encoding="utf-8")

    assert POSTGRES_CONCURRENCY_SMOKE_PATH.exists()
    assert "ThreadPoolExecutor" in source
    assert "open_runtime_store_session" in source
    assert 'mode="postgres"' in source
    assert "SCAS_RUNTIME_DATABASE_URL" in source


def test_postgres_concurrency_smoke_requires_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SCAS_RUNTIME_DATABASE_URL", raising=False)

    with pytest.raises(SystemExit, match="SCAS_RUNTIME_DATABASE_URL"):
        postgres_concurrency_smoke_main(["--events", "2"])
