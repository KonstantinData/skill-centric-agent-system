from __future__ import annotations

from pathlib import Path

import pytest

from scripts.runtime.live_dev_e2e import main as live_dev_e2e_main
from scripts.runtime.postgres_concurrency_smoke import main as postgres_concurrency_smoke_main

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
