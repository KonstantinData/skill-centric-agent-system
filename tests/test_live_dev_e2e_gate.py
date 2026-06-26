from __future__ import annotations

from pathlib import Path

import pytest

from scripts.runtime.live_dev_e2e import (
    REDACTED_PRINCIPAL_ID,
    _composition_request_summary,
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
    assert "tenant-inactive-tenant" in source
    assert "tenant-missing-membership" in source
    assert "tenant-foreign-data-source" in source
    assert "tenant-tampered-authority" in source
    assert "SCAS_LIVE_E2E_REDACT_PRINCIPAL_ID" in source


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
