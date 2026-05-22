from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATIONS_RUNBOOK_PATH = REPO_ROOT / "docs" / "operations-runbook.md"


def test_operations_runbook_exists() -> None:
    assert OPERATIONS_RUNBOOK_PATH.exists()


def test_operations_runbook_covers_runtime_baseline() -> None:
    runbook = OPERATIONS_RUNBOOK_PATH.read_text(encoding="utf-8")

    required_sections = (
        "Environment Separation",
        "Migration Flow",
        "Smoke Tests",
        "Diagnostics",
        "Disable Paths",
        "Recovery",
    )
    for section in required_sections:
        assert f"## {section}" in runbook

    required_terms = (
        "Cloudflare Control Plane",
        "Hetzner Runtime Plane",
        "SCAS_RUNTIME_DATABASE_URL",
        "runtime.runtime_events",
        "validation_results",
        "live dev E2E gate",
    )
    for term in required_terms:
        assert term in runbook
