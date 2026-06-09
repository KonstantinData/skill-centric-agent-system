from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

MEMORY_ARCHITECTURE_PATH = REPO_ROOT / "docs" / "reference" / "memory-architecture.md"
MEMORY_BACKLOG_PATH = REPO_ROOT / "docs" / "roadmap" / "memory-architecture-backlog.md"
MEMORY_ADR_PATH = (
    REPO_ROOT
    / "docs"
    / "adr"
    / "0009-task-subject-data-and-procedural-memory-separation.md"
)


def test_memory_architecture_defines_task_subject_boundary() -> None:
    architecture = MEMORY_ARCHITECTURE_PATH.read_text(encoding="utf-8")

    assert "Agent Memory stores reusable process lessons" in architecture
    assert "Task-Subject Data" in architecture
    assert "Procedural Agent Memory" in architecture
    assert "Semantic Retrieval Signal" in architecture


def test_memory_architecture_is_wired_into_contracts_and_roadmap() -> None:
    contracts = (REPO_ROOT / "docs" / "policies" / "contracts.md").read_text(
        encoding="utf-8"
    )
    runtime_contract = (
        REPO_ROOT / "docs" / "policies" / "runtime-contract.md"
    ).read_text(encoding="utf-8")
    data_governance = (
        REPO_ROOT / "docs" / "policies" / "data-governance.md"
    ).read_text(encoding="utf-8")
    roadmap = (REPO_ROOT / "docs" / "reference" / "repository-roadmap.md").read_text(
        encoding="utf-8"
    )

    assert "docs/reference/memory-architecture.md" in contracts
    assert "Memory Promotion Boundary" in runtime_contract
    assert "Task-Subject Data And Agent Memory" in data_governance
    assert "docs/roadmap/memory-architecture-backlog.md" in roadmap


def test_memory_architecture_has_accepted_adr_and_backlog() -> None:
    adr = MEMORY_ADR_PATH.read_text(encoding="utf-8")
    backlog = MEMORY_BACKLOG_PATH.read_text(encoding="utf-8")

    assert "## Status" in adr
    assert "Accepted" in adr
    assert "Agent Memory stores reusable process lessons" in adr
    assert "Delivery Order" in backlog
    assert "Procedural Memory Validation" in backlog
