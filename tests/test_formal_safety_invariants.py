from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_formal_invariant_catalog_is_present_and_complete() -> None:
    catalog = (
        REPO_ROOT / "docs" / "policies" / "formal-safety-invariants.md"
    ).read_text(encoding="utf-8")

    for invariant_id in (
        "fail_closed_on_unknowns",
        "no_self_granting",
        "mandatory_validators_per_change_type",
        "scope_monotonicity",
        "immutable_profile_after_seal",
    ):
        assert f"`{invariant_id}`" in catalog

    assert "Pass:" in catalog
    assert "Fail:" in catalog


def test_formal_invariant_catalog_is_wired_into_core_docs() -> None:
    contracts = (REPO_ROOT / "docs" / "policies" / "contracts.md").read_text(
        encoding="utf-8"
    )
    architecture = (REPO_ROOT / "docs" / "reference" / "architecture.md").read_text(
        encoding="utf-8"
    )
    queue = (REPO_ROOT / "docs" / "roadmap" / "scas-execution-queue.md").read_text(
        encoding="utf-8"
    )

    assert "formal-safety-invariants.md" in contracts
    assert "formal-safety-invariants.md" in architecture
    assert "FSG-09 Enforce Pre-Canary Gate: Invariants + Shadow Eval" in queue
