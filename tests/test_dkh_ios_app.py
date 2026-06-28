from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IOS_ROOT = REPO_ROOT / "apps" / "dkh-ios"
WEB_ROOT = REPO_ROOT / "apps" / "dkh-crm"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def ios_text() -> str:
    return "\n".join(
        read(path)
        for path in sorted(IOS_ROOT.rglob("*"))
        if path.is_file()
        and path.suffix in {".md", ".swift", ".pbxproj", ".json", ".xcworkspacedata"}
    )


def test_dkh_ios_app_exists_alongside_web_crm() -> None:
    assert (IOS_ROOT / "DKHCRM.xcodeproj" / "project.pbxproj").exists()
    assert (IOS_ROOT / "DKHCRM" / "DKHCRMApp.swift").exists()
    assert (WEB_ROOT / "README.md").exists()
    assert (WEB_ROOT / "src" / "app" / "page.tsx").exists()

    readme = read(IOS_ROOT / "README.md")
    assert "additional iOS surface beside the browser version" in readme
    assert "not a replacement" in readme
    assert "apps/dkh-crm/" in readme


def test_dkh_ios_scope_matches_dkh_tenant_boundary() -> None:
    snapshot = read(IOS_ROOT / "DKHCRM" / "Models" / "DKHWorkspaceSnapshot.swift")
    project = read(IOS_ROOT / "DKHCRM.xcodeproj" / "project.pbxproj")

    assert 'tenantId: "daskuechenhaus"' in snapshot
    assert 'areaId: "daskuechenhaus"' in snapshot
    assert '"es-daskuechenhaus.de"' in snapshot
    assert '"www.es-daskuechenhaus.de"' in snapshot
    assert 'PRODUCT_BUNDLE_IDENTIFIER = "de.daskuechenhaus.crm";' in project


def test_dkh_ios_has_no_foreign_tenant_product_content() -> None:
    combined = ios_text().lower()

    forbidden_fragments = (
        "tenant_kinderhaus",
        "kinderhaus-heuschrecken",
        "khh workbench",
        "khh-ios",
        "liquisto",
        "schober five-step",
        "demo-tenant",
    )
    for fragment in forbidden_fragments:
        assert fragment not in combined


def test_dkh_ios_keeps_privacy_and_read_only_boundaries() -> None:
    combined = ios_text()

    for expected in (
        "Keine echten Kundennamen, E-Mail-Adressen, Telefonnummern oder Postadressen",
        "Keine Dokumentinhalte, Roh-Mails, API-Antworten, Tokens oder Runtime-Traces",
        "No write intents",
        "No customer master-data cache",
        "No object-storage document access",
        "No Cloudflare Access token storage",
        "No Hetzner Admin API secrets",
    ):
        assert expected in combined

    assert not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", combined)
    assert not re.search(r"\b(?:\+49|0)[0-9][0-9 /()-]{6,}\b", combined)
    assert not re.search(r"\bDE[0-9]{9}\b", combined)
    assert "Commercial register" not in combined
    assert "Handelsregister" not in combined


def test_dkh_ios_dashboard_matches_core_dkh_crm_sections() -> None:
    snapshot = read(IOS_ROOT / "DKHCRM" / "Models" / "DKHWorkspaceSnapshot.swift")

    for label in (
        "Uebersicht",
        "Termine",
        "Aufgaben",
        "E-Mails",
        "Kunden",
        "Vorgaenge",
        "Kaufvertrag und Rechnung",
        "Vorlagen",
        "Admin",
    ):
        assert label in snapshot


def test_dkh_ios_readme_documents_local_xcode_validation() -> None:
    readme = read(IOS_ROOT / "README.md")

    assert "xcodebuild -list -project apps/dkh-ios/DKHCRM.xcodeproj" in readme
    assert "CODE_SIGNING_ALLOWED=NO build" in readme
    assert "python -m pytest tests/test_dkh_ios_app.py" in readme
