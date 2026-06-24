from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "apps" / "dkh-crm"


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_dkh_crm_next_app_is_the_only_site_ui() -> None:
    assert APP_ROOT.exists()
    assert not (REPO_ROOT / "workers" / "daskuechenhaus-control-api").exists()
    assert not (REPO_ROOT / "docs" / "diagrams" / "daskuechenhaus-cloudflare-d1.drawio").exists()
    assert not (REPO_ROOT / "workers" / "es-daskuechenhaus-site").exists()
    assert not (
        REPO_ROOT / ".github" / "workflows" / "es-daskuechenhaus-site-deploy.yml"
    ).exists()
    assert not (
        REPO_ROOT / "scripts" / "cloudflare" / "es_daskuechenhaus_access.py"
    ).exists()


def test_dkh_crm_uses_tenant_owned_assets_and_search() -> None:
    assert (APP_ROOT / "public" / "logo.svg").exists()
    assert (APP_ROOT / "public" / "crm-hero.jpg").exists()
    assert (APP_ROOT / "public" / "customer-search.v1.js").exists()

    search_script = load_text(APP_ROOT / "public" / "customer-search.v1.js")
    assert 'fetch("/api/kunden/search?" + params.toString()' in search_script
    assert "URLSearchParams" in search_script
    assert 'params.set("status", filterValue)' in search_script
    assert "/kunden/" in search_script
    assert "maxOpenFiles = 3" in search_script
    assert "[data-customer-create-modal]" in search_script
    assert "[data-customer-email-duplicate-modal]" in search_script
    assert "customer_email_duplicate_found" in search_script
    assert 'confirmedData.set("allow_duplicate_email", "true")' in search_script
    assert "syncCustomerTypeSections" in search_script
    assert "options.openCreateModal && createModal" in search_script
    assert "closeCreateModal" in search_script
    assert "if (createForm) createForm.reset()" in search_script
    assert "pendingDuplicateFormData = null" in search_script
    assert "if (emailDuplicateResults) emailDuplicateResults.innerHTML = \"\"" in search_script
    assert "syncCustomerTypeSections();" in search_script
    assert "syncCaseDetails();" in search_script
    assert "Escape" in search_script


def test_dkh_crm_access_middleware_strips_spoofable_identity_headers() -> None:
    middleware = load_text(APP_ROOT / "src" / "middleware.ts")

    assert "cf-access-jwt-assertion" in middleware
    assert "cf-access-authenticated-user-email" in middleware
    assert "cf-access-client-id" in middleware
    assert "cf-access-client-secret" in middleware
    assert "cf-access-user-email" in middleware
    assert "x-access-user-email" in middleware
    assert "x-dkh-user-email" in middleware
    assert "jwtVerify" in middleware


def test_dkh_crm_supports_dark_mode_theme_toggle() -> None:
    globals_css = load_text(APP_ROOT / "src" / "app" / "globals.css")
    layout = load_text(APP_ROOT / "src" / "app" / "layout.tsx")
    top_bar = load_text(APP_ROOT / "src" / "components" / "chrome" / "top-bar.tsx")
    sidebar = load_text(APP_ROOT / "src" / "components" / "chrome" / "sidebar.tsx")
    bottom_nav = load_text(APP_ROOT / "src" / "components" / "chrome" / "bottom-nav.tsx")
    theme_toggle = load_text(APP_ROOT / "src" / "components" / "chrome" / "theme-toggle.tsx")
    theme_script = load_text(APP_ROOT / "src" / "components" / "chrome" / "theme-script.tsx")

    assert '[data-theme="dark"]' in globals_css
    assert "--field-surface" in globals_css
    assert "--chrome-surface" in globals_css
    assert ".bg-white" in globals_css
    assert "ThemeScript" in layout
    assert "ThemeToggle" in top_bar
    assert "bg-[var(--chrome-surface)]" in sidebar
    assert "bg-[var(--chrome-surface)]" in bottom_nav
    assert "dkh-crm-theme" in theme_toggle
    assert "prefers-color-scheme: dark" in theme_toggle
    assert "localStorage.setItem" in theme_toggle
    assert "Systemmodus aktiv" in theme_toggle
    assert "dangerouslySetInnerHTML" in theme_script


def test_dkh_crm_proxy_routes_keep_backend_contracts_guarded() -> None:
    proxy = load_text(APP_ROOT / "src" / "lib" / "proxy.ts")
    kunden_search = load_text(APP_ROOT / "src" / "app" / "api" / "kunden" / "search" / "route.ts")
    dkh_api = load_text(APP_ROOT / "src" / "lib" / "dkh-api.ts")

    assert 'type ProxyKind = "overview" | "admin" | "customers"' in proxy
    assert "Disallowed API path" in proxy
    assert r"^cases\/\d+\/carat-imports\/\d+\/positions$" in proxy
    assert r"^cases\/\d+\/confirmations$" in proxy
    assert r"^confirmations\/\d+\/exceptions\/\d+\/decide$" in proxy
    assert "safeDecodeSegment" in proxy
    assert "/customers/search" in kunden_search
    assert 'upstream.searchParams.set("status", status)' in kunden_search
    assert '["active", "closed", "all"].includes(status)' in kunden_search
    assert "x-access-user-email" in proxy
    assert "x-access-user-email" in kunden_search
    assert "cf-access-authenticated-user-email" in kunden_search
    assert "content-disposition" in proxy
    assert "multipart/form-data" in proxy
    assert "request.arrayBuffer()" in proxy
    assert "withFallback" in dkh_api
    assert "CustomersState | null" in dkh_api
    assert "EMPTY_CUSTOMERS_STATE" in dkh_api


def test_dkh_crm_surface_uses_new_routes_not_php_worker_routes() -> None:
    source = "\n".join(
        load_text(path)
        for path in (APP_ROOT / "src").rglob("*.tsx")
    )

    for route in ("/termine", "/aufgaben", "/emails", "/kunden", "/admin"):
        assert route in source

    assert ".php" not in source
    assert "tenant-assets/daskuechenhaus" not in source


def test_dkh_crm_cases_route_redirects_to_customer_files() -> None:
    source = load_text(APP_ROOT / "src" / "app" / "vorgaenge" / "page.tsx")
    nav = load_text(APP_ROOT / "src" / "components" / "chrome" / "nav-items.ts")

    assert 'redirect("/kunden")' in source
    assert 'href: "/vorgaenge"' not in nav
    assert 'label: "Vorgänge"' not in nav


def test_dkh_crm_customers_page_is_search_first_and_recent_only() -> None:
    source = load_text(APP_ROOT / "src" / "app" / "kunden" / "page.tsx")
    hero = load_text(APP_ROOT / "src" / "components" / "chrome" / "page-hero.tsx")

    assert "eyebrow={null}" in source
    assert "Suche, Neuanlage und direkter Einstieg in Kundenakten." in source
    assert "Suche, Dubletten-sensible Neuanlage" not in source
    assert "eyebrow = \"das küchenhaus\"" in hero
    assert "data-customer-create-modal" in source
    assert "data-customer-create-form" in source
    assert "role=\"dialog\"" in source
    assert "data-customer-create-close" in source
    assert "data-customer-email-duplicate-modal" in source
    assert "data-customer-email-duplicate-results" in source
    assert "Trotzdem speichern" in source
    assert "Neukundenanlage" in source
    assert "Kunde suchen" not in source
    assert "data-customer-direct-search" in source
    assert "Kunden direkt Suche" in source
    assert "data-customer-status-filter" in source
    assert "Aktive Kunden" in source
    assert "Abgeschlossene Kunden" in source
    assert "Alle Kunden" in source
    assert "xl:grid-cols-2" in source
    assert "data-customer-search-empty" not in source
    assert "name=\"create_case\"" in source
    assert "data-customer-type-select" in source
    assert "data-customer-type-section=\"private\"" in source
    assert "data-customer-type-section=\"company\"" in source
    assert "name=\"salutation\"" in source
    assert "name=\"title\"" in source
    assert "Prof. Dr." in source
    assert "name=\"object_customer_label\"" in source
    assert "Architekt" in source
    assert "Bauträger" in source
    assert "Schreinerei" in source
    assert "name=\"legal_form\"" in source
    assert "name=\"vat_id\"" in source
    assert "name=\"registry_number\"" in source
    assert "name=\"registry_court\"" in source
    assert "name=\"contact_first_name\"" in source
    assert "name=\"contact_email\"" in source
    assert "name=\"country\"" in source
    assert "Schweiz" in source
    assert "name=\"tax_treatment\"" in source
    assert "NATO / US-Streitkräfte prüfen" in source
    assert "data-customer-country-select" in source
    assert "data-customer-custom-vat" in source
    assert "name=\"has_custom_vat\"" in source
    assert "name=\"custom_vat_rate\"" in source
    assert "name=\"custom_vat_rate_label\"" in source
    assert "Schweiz Normalsatz" in source
    assert "data-customer-create-case-toggle" in source
    assert "data-customer-case-details" in source
    assert "defaultChecked" not in source
    assert "create_direct_case" not in source
    assert "Wird beim Speichern automatisch vergeben" in source
    assert "name=\"carat_order_number\"" in source
    assert "pattern=\"[A-Za-z0-9]{1,5}-[A-Za-z0-9]{1,3}\"" in source
    assert "Vorgangsnummer" in source
    assert "recentlyUsedCustomers" in source
    assert ".slice(0, 5)" in source
    assert "Zuletzt verwendet" in source
    assert "Aktuelle Kunden" not in source
    assert "const currentUserId = state.current_user.primary_user_id" in source
    assert "const assignableUsers =" in source
    assert "state.users.length > 0 || !currentUserId" in source
    assert (
        'Select name="owner_user_id" '
        "defaultValue={currentUserId ? String(currentUserId) : undefined}"
    ) in source
    assert (
        'Select name="responsible_user_id" '
        "defaultValue={currentUserId ? String(currentUserId) : undefined}"
    ) in source
    assert "assignableUsers.map((user)" in source

    search_script = load_text(APP_ROOT / "public" / "customer-search.v1.js")
    assert "syncCaseDetails" in search_script
    assert "syncCustomVat" in search_script
    assert 'country === "CH"' in search_script
    assert "customerCustomVatRate.value = \"8.10\"" in search_script
    assert "customerCustomVatFlag.value = enabled ? \"true\" : \"false\"" in search_script
    assert "setupSearch" in search_script
    assert "openCreateModal: true" in search_script
    assert "openCreateModal: false" in search_script
    assert 'caseDetails.hidden = !enabled' in search_script
    assert 'field.disabled = !enabled' in search_script


def test_dkh_crm_email_page_supports_sender_filter_and_direct_delete() -> None:
    source = load_text(APP_ROOT / "src" / "app" / "emails" / "page.tsx")
    globals_css = load_text(APP_ROOT / "src" / "app" / "globals.css")

    assert "Absender filtern" in source
    assert "Alle Absender" in source
    assert "Zurücksetzen" in source
    assert 'participant.type !== "from"' in source
    assert "visibleEmails" in source
    assert "selectedSender" in source
    assert "encodedReturnTo" in source
    assert "archive?return_to" not in source
    assert ">Archiv<" not in source
    assert "/delete?return_to=" in source
    assert "formAction={`/api/overview/emails/${email.id}/delete" not in source
    assert ".btn-danger:hover" in globals_css
    assert "background: var(--danger);" in globals_css
    assert "color: #fff;" in globals_css


def test_dkh_crm_customer_file_uses_desktop_and_case_shelf() -> None:
    source = load_text(APP_ROOT / "src" / "app" / "kunden" / "[id]" / "page.tsx")
    proxy = load_text(APP_ROOT / "src" / "lib" / "proxy.ts")
    search_js = load_text(APP_ROOT / "public" / "customer-search.v1.js")

    assert "notFound" not in source
    assert "Kundenakte nicht gefunden" in source
    assert "Zur Kundensuche" in source
    assert "Stammdaten-Snapshot" in source
    assert "Vorgangsregal" in source
    assert "data-customer-master-open" in source
    assert "data-customer-master-modal" in source
    assert "Kundenstammdaten bearbeiten" in source
    assert "data-customer-master-type-section" in source
    assert 'Script src="/customer-search.v1.js"' in source
    assert "data-customer-master-open" in search_js
    assert "syncCustomerMasterTypeSections" in search_js
    assert "data-document-upload-modal" in search_js
    assert "openDocumentUploadModal" in search_js
    assert "closeDocumentUploadModal" in search_js
    assert "Neuen Vorgang anlegen" in source
    assert 'action={`/api/kunden/cases?return_to=/kunden/${customer.id}`}' in source
    assert 'name="customer_id"' in source
    assert "Vorgang anlegen" in source
    assert "Kundenakte herunterladen" in source
    assert "Letzter Export:" in source
    assert "INITIAL_CUSTOMER_EXPORT_AT" in source
    assert "/api/kunden/customers/${customer.id}/export" in source
    assert "CASE_REGISTERS" in source
    assert "registerForPhase" in source
    assert "normalizeRegister" in source
    assert "activeRegister" in source
    assert "Vergangenheit" in source
    assert "Zukunft" in source
    assert "Aktueller Bereich" in source
    assert "DOCUMENTS_REGISTER" in source
    assert "Dokumentenbereich öffnen" in source
    assert "Hochladen, herunterladen und per E-Mail versenden" in source
    assert "Vorgangsdokumente" in source
    assert "data-document-upload-open" in source
    assert "data-document-upload-modal" in source
    assert "data-document-upload-close" in source
    assert "data-document-upload-backdrop" in source
    assert "Dokumentenarten" in source
    assert 'activeRegister === DOCUMENTS_REGISTER.key' in source
    assert "DOCUMENT_GUIDE_CATEGORIES" in source
    assert "Die Dokumentart ist pro Eintrag direkt sichtbar" in source
    assert "vom Kunden" in source
    assert "Aufmaß" in source
    assert "Planung" in source
    assert "Angebot" in source
    assert "Auftrag" in source
    assert "Bestellabwicklung" in source
    assert "Lieferung / Montage" in source
    assert "Reklamation / Kundendienst" in source
    assert "Rechnung" in source
    assert "Legt automatisch fest, in welchem Register das Dokument geführt wird" in source
    assert "Noch keine Dokumente in diesem Vorgang" in source
    assert "Dokument hinzufügen" in source
    assert "Dokument hochladen" in source
    assert 'encType="multipart/form-data"' in source
    assert 'name="file"' in source
    assert ".prjz" in source
    assert "application/zip" in source
    assert "lg:grid-cols-[minmax(0,1fr)_360px]" in source
    assert "lg:grid-cols-[minmax(0,1.35fr)_minmax(170px,0.65fr)]" in source
    assert "Legt automatisch fest, in welchem Register" in source
    assert "/download" in source
    assert "Herunterladen" in source
    assert 'name="document_category"' in source
    assert 'name="register_code"' not in source
    assert 'name="document_status"' in source
    assert 'name="version_label"' in source
    assert "caseDocuments" in source
    assert "documentCategoryLabel" in source
    assert "Archivieren" in source
    assert "Noch ohne Datei" in source
    assert "Die Dokumentart ordnet den Upload automatisch dem passenden Register zu" in source
    assert "Desktop" in source
    assert "Geöffnete Vorgangsmappe" in source
    assert "PROJECT_OBJECTS" in source
    assert "PROJECT_SITUATIONS" in source
    assert "PROJECT_URGENCIES" in source
    assert "BUDGET_RANGES" in source
    assert "INQUIRY_SOURCES" in source
    assert "UrgencyInfoTooltip" in source
    assert "Einbauküche" in source
    assert "Garderobe" in source
    assert "Sideboard" in source
    assert "Liefer-/Montageort PLZ" in source
    assert "Liefer-/Montageort Ort" in source
    assert 'name="delivery_postal_code"' in source
    assert 'name="delivery_city"' in source
    assert "Gewünschter Zeitraum" in source
    assert "Budgetrahmen" in source
    assert "Terminrelevant" in source
    assert "Notfall / Ersatzbedarf" in source
    assert "Bestehende Küche nicht nutzbar oder Schadenfall" in source
    assert "CARAT-Importe" in source
    assert "PRJZ-Projektdateien werden hier importiert" in source
    assert "CARAT-Projektdatei" in source
    assert 'name="document_category" value="order_processing"' in source
    assert 'name="document_type" value="carat_project"' in source
    assert 'name="carat_upload_mode"' in source
    assert 'value="new_version"' in source
    assert 'value="replace_latest"' in source
    assert "Als neue Version hochladen" in source
    assert "Vorherigen CARAT-Import ersetzen" in source
    assert "latestCurrentCaratDocument" in source
    assert "CARAT importieren" in source
    assert "Ausgewählte Positionen übernehmen" in source
    assert "Ausgewählte Positionen zurücksetzen" in source
    assert 'name="carat_action" value="reset"' in source
    assert 'name="carat_action" value="transfer"' in source
    assert "Alles markieren" in source
    assert "data-carat-supplier-group" in source
    assert "data-carat-supplier-toggle" in source
    assert "data-carat-position-checkbox" in source
    assert "syncCaratSupplierToggle" in source
    assert "isExportableCaratPosition" in source
    assert "exportablePositions" in source
    assert "Bilddaten nicht exportiert" in source
    assert (
        "Bilddaten wie Wand- oder Deckenpositionen werden nicht in Bestellungen übernommen."
        in source
    )
    assert "transferredCount" in source
    assert "Übernommen" in source
    assert "Markiert" in source
    assert "caratImports" in source
    assert "AB-Cockpit" in source
    assert "supplierOrders" in source
    assert "supplierConfirmations" in source
    assert "openConfirmationExceptionCount" in source
    assert "Nur 1:1-Übereinstimmungen werden grün" in source
    assert "AB prüfen" in source
    assert "confirmation_positions" in source
    assert "Änderungs-AB" in source
    assert "Lieferantenkommunikation" in source
    assert "position.selection_status" in source
    assert "displayImportQuantity" in source
    assert "displayDimensions" in source
    assert "carat-imports/${caratImport.id}/positions" in source
    assert (
        "Noch kein CARAT-Import in diesem Vorgang. Laden Sie eine PRJZ-Datei direkt hier hoch."
        in source
    )
    assert "/confirmations?return_to=" in source
    assert "/exceptions/${exception.id}/decide?return_to=" in source
    assert "Informationen zu den Dringlichkeitsleveln" in source
    assert "Kontaktweg" in source
    assert "Vorhandene Unterlagen" in source
    assert "Interne Notiz für den ersten Termin" in source
    assert "Projektgrundlagen speichern" in source
    assert "Planung speichern" in source
    assert "CONTACT_ROLES" in source
    assert "Architekt" in source
    assert "Schreinerei" in source
    assert "primary_contact_same_as_master" in source
    assert "project_objects" in source
    assert "project_contacts" in source
    assert "process_control" in source
    assert "Dokumentenregister speichern" in source
    assert "Telefonnotiz speichern" in source
    assert "Entwurf vormerken" in source
    assert "/api/overview/tasks" in source
    assert "/api/kunden/cases?return_to=/kunden/${customer.id}" in source
    assert "/sections/project_objects" in source
    assert "/sections/project_contacts" in source
    assert "/sections/documents" in source
    assert "/documents?return_to=" in source
    assert "/documents/${document.id}/archive?return_to=" in source
    assert "/documents/${document.id}/download" in source
    assert "/sections/process_control" in source
    assert "Vorgang schließen" in source
    assert r"^cases$" in proxy
    assert r"^cases\/\d+$" in proxy
    assert r"^cases\/\d+\/documents$" in proxy
    assert r"^cases\/\d+\/documents\/\d+\/archive$" in proxy
    assert r"^cases\/\d+\/sections\/[a-z0-9_-]+$" in proxy
    assert "publicRedirectOrigin(request)" in proxy
    assert "https://www.es-daskuechenhaus.de" in proxy
    assert "isLocalRedirectHost(host)" in proxy
    assert "new URL(returnTo, request.url)" not in proxy


def test_dkh_crm_admin_user_save_preserves_existing_admin_role() -> None:
    source = load_text(APP_ROOT / "src" / "app" / "admin" / "page.tsx")

    assert 'title="Admin Bereich"' in source
    assert "ADMIN_SECTIONS" in source
    assert 'key: "benutzer"' in source
    assert 'key: "firmenstammdaten"' in source
    assert 'key: "integrationen"' in source
    assert 'key: "system"' in source
    assert "Zur Admin-Übersicht" in source
    assert 'activeSection === "benutzer"' in source
    assert 'activeSection === "firmenstammdaten"' in source
    assert 'activeSection === "integrationen"' in source
    assert 'activeSection === "system"' in source
    assert (
        'const isLockedAdminRole = user.roles.includes("admin") && role.code === "admin"'
    ) in source
    assert '<input name="role_admin" value="true" type="hidden" />' in source
    assert "defaultChecked={isLockedAdminRole || user.roles.includes(role.code)}" in source
    assert "disabled={isLockedAdminRole}" in source
