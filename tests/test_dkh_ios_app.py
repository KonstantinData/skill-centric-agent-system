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
    assert (IOS_ROOT / "DKHCRM" / "DKHCRMNativeApp.swift").exists()
    assert (IOS_ROOT / "DKHCRM" / "DKHCRM.entitlements").exists()
    assert (WEB_ROOT / "README.md").exists()
    assert (WEB_ROOT / "src" / "app" / "page.tsx").exists()

    readme = read(IOS_ROOT / "README.md")
    assert "native SwiftUI screens" in readme
    assert "does not start either website" in readme
    assert "apps/dkh-crm/" in readme


def test_dkh_ios_scope_matches_dkh_tenant_boundary() -> None:
    native_app = read(IOS_ROOT / "DKHCRM" / "DKHCRMNativeApp.swift")
    project = read(IOS_ROOT / "DKHCRM.xcodeproj" / "project.pbxproj")

    assert '"https://app.es-daskuechenhaus.de/api/mobile"' in native_app
    assert "PRODUCT_BUNDLE_IDENTIFIER = de.daskuechenhaus.crm;" in project.replace('"', "")
    assert "CODE_SIGN_ENTITLEMENTS = DKHCRM/DKHCRM.entitlements;" in project
    assert "com.apple.developer.applesignin" in read(IOS_ROOT / "DKHCRM" / "DKHCRM.entitlements")


def test_dkh_ios_is_native_and_does_not_start_websites() -> None:
    app = read(IOS_ROOT / "DKHCRM" / "DKHCRMApp.swift")
    native_app = read(IOS_ROOT / "DKHCRM" / "DKHCRMNativeApp.swift")
    project = read(IOS_ROOT / "DKHCRM.xcodeproj" / "project.pbxproj")

    assert "DKHCRMRootView()" in app
    assert "import AuthenticationServices" in native_app
    assert "ASAuthorizationController" in native_app
    assert "ASAuthorizationAppleIDProvider().createRequest()" in native_app
    assert "ASAuthorizationAppleIDCredential" in native_app
    assert "DKHKeychainStore" in native_app
    assert "DKHDeviceGrantView" in native_app
    assert "DKHMobileDataClient" in native_app
    assert "fetchLiveWorkspace" in native_app
    assert 'appending(path: "overview")' not in native_app
    assert 'fetchResource("overview"' in native_app
    assert 'fetchResource("customers"' in native_app
    assert "SignInWithAppleButton" not in native_app
    assert "Mit Apple" not in native_app
    assert "DKHAppleLoginView" not in native_app
    assert "signOut" not in native_app
    assert "Abmelden" not in native_app
    assert "signed_out" not in native_app
    assert "mobileAPINotReachable" in native_app
    assert "cannotFindHost" in native_app
    assert "Es wurde kein Server mit dem angegebenen Hostnamen gefunden" not in native_app
    assert "SFSafariViewController" not in native_app
    assert "WKWebView" not in native_app
    assert "import SafariServices" not in native_app
    assert "import WebKit" not in native_app
    assert "https://es-daskuechenhaus.de" not in native_app
    assert "https://www.es-daskuechenhaus.de" not in native_app
    assert "DKHCRMNativeApp.swift in Sources" in project
    assert "WebAppView.swift in Sources" not in project
    assert "DashboardView.swift in Sources" not in project
    assert "DKHWorkspaceSnapshot.swift in Sources" not in project


def test_dkh_ios_has_no_demo_crm_workspace_after_device_grant() -> None:
    native_app = read(IOS_ROOT / "DKHCRM" / "DKHCRMNativeApp.swift")

    forbidden_fragments = (
        "dkhCRMSections",
        "DKHCRMSectionView",
        "Diese native Ansicht",
        "produktiven CRM-Daten versorgt",
        "static CRM section database",
        "mock customer",
    )
    for fragment in forbidden_fragments:
        assert fragment not in native_app

    for expected in (
        "DKHOverviewState",
        "DKHCustomersState",
        "DKHHomePage",
        "DKHAppointmentsPage",
        "DKHTasksPage",
        "DKHEmailsPage",
        "DKHCustomersPage",
        "DKHNewLeadSheet",
        "DKHNewCustomerSheet",
        "DKHCustomerDetailPage",
        "DKHCaseDetailPage",
        "DKHCaseRegisters",
        "DKHTemplatesPage",
        "DKHAdminPage",
        "DKH Serverdaten werden geladen",
    ):
        assert expected in native_app

    for stale_view in (
        "DKHOverviewSection",
        "DKHCustomersSection",
        "DKHListDetailView",
    ):
        assert stale_view not in native_app

    assert native_app.index('Label("Kunden", systemImage: "person.2")') < native_app.index(
        'Label("Aufgaben", systemImage: "checklist")'
    )
    assert native_app.index('Label("Aufgaben", systemImage: "checklist")') < native_app.index(
        'Label("E-Mails", systemImage: "envelope")'
    )
    assert native_app.index('Label("E-Mails", systemImage: "envelope")') < native_app.index(
        'Label("Termine", systemImage: "calendar")'
    )
    assert "Kein Treffer gefunden" in native_app
    assert "Leadanlage" in native_app
    assert "Kundenanlage" in native_app
    assert "Vorgang speichern" in native_app
    assert "Kundenstammdaten bearbeiten" in native_app
    assert "DKHCustomerEditSheet" in native_app
    assert "DKHLeadDetailPage" in native_app
    assert "Kommunikation speichern" in native_app
    assert "Register bearbeiten" in native_app
    assert "DKHCaseSectionEditSheet" in native_app
    assert "Dokument-Metadaten anlegen" in native_app
    assert "DKHNewDocumentSheet" in native_app
    assert "Aufgabe im Vorgang anlegen" in native_app
    assert "DKHCaratImportControls" in native_app
    assert "Lieferanten-AB erfassen" in native_app
    assert "DKHSupplierConfirmationControls" in native_app


def test_dkh_ios_has_no_foreign_tenant_product_content() -> None:
    combined = ios_text().lower()

    forbidden_fragments = (
        "tenant_kinderhaus",
        "kinderhaus-heuschrecken",
        "khh workbench",
        "khh-ios",
        "liqui" + "sto",
        "scho" + "ber five-step",
        "demo-tenant",
    )
    for fragment in forbidden_fragments:
        assert fragment not in combined


def test_dkh_ios_keeps_privacy_and_runtime_boundaries() -> None:
    combined = ios_text()

    for expected in (
        "no CRM data export",
        "no demo customer database",
        "No demo workspace",
        "static CRM section database",
        "does not store long-lived secrets in app code",
        "No embedded Apple tokens",
        "customer records",
        "server-side Apple subject mapping",
    ):
        assert expected in combined

    assert not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", combined)
    assert not re.search(r"\b(?:\+49|0)[0-9][0-9 /()-]{6,}\b", combined)
    assert not re.search(r"\bDE[0-9]{9}\b", combined)
    assert "Commercial register" not in combined
    assert "Handelsregister" not in combined


def test_dkh_ios_readme_documents_native_device_authorization() -> None:
    readme = read(IOS_ROOT / "README.md")
    readme_single_line = " ".join(readme.split())

    for label in (
        "No standalone app login area",
        "unlocking the",
        "iPhone is enough",
        "One-time iPhone device approval",
        "No visible Apple login button",
        "authorization dialog automatically",
        "Apple `identityToken`",
        "Keychain storage",
        "trusted-device user snapshot",
        "/api/mobile/overview",
        "/api/mobile/customers",
        "User-facing network errors",
        "No `SFSafariViewController`",
        "no `WKWebView`",
        "no browser website startup",
        "No Cloudflare Access verification",
        "customers",
        "same server state used by the browser CRM",
        "mobile_api_host: app.es-daskuechenhaus.de",
    ):
        assert label in readme or label in readme_single_line

    assert "loads that same Web App" not in readme
    assert "Safari-based in-app browser" not in readme
    assert "app-login entrypoint" not in readme


def test_dkh_ios_readme_documents_local_xcode_validation() -> None:
    readme = read(IOS_ROOT / "README.md")

    assert "xcodebuild -list -project apps/dkh-ios/DKHCRM.xcodeproj" in readme
    assert "CODE_SIGNING_ALLOWED=NO build" in readme
    assert "python -m pytest tests/test_dkh_ios_app.py" in readme
