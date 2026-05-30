from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ADR_PATH = (
    REPO_ROOT / "docs" / "adr" / "0006-formal-safety-guarantees-profile-sealing.md"
)


def test_formal_safety_adr_exists_and_is_accepted() -> None:
    adr = ADR_PATH.read_text(encoding="utf-8")

    assert "# ADR-0006: Formal Safety Guarantees for Profile Sealing and Pre-Canary Gates" in adr
    assert "## Status" in adr
    assert "Accepted" in adr


def test_formal_safety_adr_is_wired_into_architecture_and_policy() -> None:
    architecture = (REPO_ROOT / "docs" / "reference" / "architecture.md").read_text(
        encoding="utf-8"
    )
    invariant_policy = (
        REPO_ROOT / "docs" / "policies" / "formal-safety-invariants.md"
    ).read_text(encoding="utf-8")

    assert "0006-formal-safety-guarantees-profile-sealing.md" in architecture
    assert "0006-formal-safety-guarantees-profile-sealing.md" in invariant_policy
