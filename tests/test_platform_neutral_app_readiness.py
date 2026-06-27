from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_platform_neutral_adr_defines_native_ready_tenant_workbench_path() -> None:
    adr = read("docs/adr/0012-platform-neutral-tenant-workbench-architecture.md")

    assert "## Status\n\nAccepted" in adr
    assert "tenant_kinderhaus" in adr
    assert "kinderhaus-heuschrecken.cloud" in adr
    assert "React Native for Web / Expo-compatible boundaries" in adr
    assert "auth, navigation, offline behavior, push" in adr
    assert "device permissions" in adr
    assert "does not require shipping native apps in the current sprint" in adr


def test_platform_neutral_readiness_backlog_has_estimate_and_milestones() -> None:
    roadmap = read("docs/roadmap/platform-neutral-app-readiness.md")

    assert "Planning total: 17.5 implementation days." in roadmap
    assert "Recommended sprint allocation: 18 implementation days plus review buffer." in roadmap
    assert "### M1: Native-Ready Architecture Contract" in roadmap
    assert "### M2: Shared Workbench Foundation" in roadmap
    assert "### M3: Shared UI And Web Shell Migration" in roadmap
    assert "### M4: Native Proof And Gates" in roadmap
    assert "No new KHH feature work bypasses the shared architecture path." in roadmap


def test_repository_docs_route_khh_workbench_through_platform_neutral_plan() -> None:
    architecture = read("docs/reference/architecture.md")
    repository_roadmap = read("docs/reference/repository-roadmap.md")
    execution_queue = read("docs/roadmap/scas-execution-queue.md")
    docs_index = read("docs/README.md")

    for document in (architecture, repository_roadmap, execution_queue, docs_index):
        assert "platform-neutral" in document

    assert "ADR-0012" in architecture
    assert "docs/roadmap/platform-neutral-app-readiness.md" in architecture
    assert "Phase 9: Platform-Neutral Tenant Workbench Readiness" in repository_roadmap
    assert "tenant_kinderhaus" in repository_roadmap
    assert "Native-Ready Architecture Contract" in execution_queue
    assert "apps/khh-workbench/" in docs_index
