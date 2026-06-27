from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IOS_ROOT = REPO_ROOT / "apps" / "khh-ios"
WEB_ROOT = REPO_ROOT / "apps" / "khh-workbench"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_khh_ios_app_exists_alongside_web_workbench() -> None:
    assert (IOS_ROOT / "KHHWorkbench.xcodeproj" / "project.pbxproj").exists()
    assert (IOS_ROOT / "KHHWorkbench" / "KHHWorkbenchApp.swift").exists()
    assert (WEB_ROOT / "README.md").exists()

    readme = read(IOS_ROOT / "README.md")
    assert "additional iOS" in readme
    assert "surface" in readme
    assert "not a replacement for the browser version" in readme
    assert "kinderhaus-heuschrecken.cloud" in readme


def test_khh_ios_scope_matches_tenant_boundary() -> None:
    snapshot = read(IOS_ROOT / "KHHWorkbench" / "Models" / "KHHWorkbenchSnapshot.swift")
    project = read(IOS_ROOT / "KHHWorkbench.xcodeproj" / "project.pbxproj")

    assert 'tenantId: "tenant_kinderhaus"' in snapshot
    assert 'areaId: "kinderhaus-heuschrecken"' in snapshot
    assert 'primaryHostname: "kinderhaus-heuschrecken.cloud"' in snapshot
    assert 'PRODUCT_BUNDLE_IDENTIFIER = "de.kinderhaus-heuschrecken.workbench";' in project


def test_khh_ios_keeps_privacy_and_read_only_boundaries() -> None:
    combined = "\n".join(
        read(path)
        for path in [
            IOS_ROOT / "README.md",
            IOS_ROOT / "KHHWorkbench" / "Models" / "KHHWorkbenchSnapshot.swift",
        ]
    )

    assert "Keine vollstaendigen Kinder-, Eltern- oder Personalstammdaten" in combined
    assert "Personenbezug nur mit Vorname, Kuerzel oder interner Referenz" in combined
    assert "No write intents" in combined

    forbidden_fragments = (
        "Liquisto",
        "daskuechenhaus",
        "diagnosis",
        "private contact",
        "birth date",
    )
    for fragment in forbidden_fragments:
        assert fragment not in combined


def test_khh_ios_dashboard_matches_core_workbench_sections() -> None:
    snapshot = read(IOS_ROOT / "KHHWorkbench" / "Models" / "KHHWorkbenchSnapshot.swift")

    for label in (
        "Leitungs-Cockpit",
        "Fristen",
        "Personal-Ampel",
        "Dienste",
        "Vorgaenge",
        "Belegung",
        "Entwicklung",
        "Dokumente",
        "Aufgaben",
    ):
        assert label in snapshot
