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


def test_dkh_crm_proxy_routes_keep_backend_contracts_guarded() -> None:
    proxy = load_text(APP_ROOT / "src" / "lib" / "proxy.ts")
    kunden_search = load_text(APP_ROOT / "src" / "app" / "api" / "kunden" / "search" / "route.ts")

    assert 'type ProxyKind = "overview" | "admin" | "customers"' in proxy
    assert "Disallowed API path" in proxy
    assert "safeDecodeSegment" in proxy
    assert "/customers/search" in kunden_search
    assert 'upstream.searchParams.set("status", status)' in kunden_search
    assert '["active", "closed", "all"].includes(status)' in kunden_search
    assert "x-access-user-email" in proxy
    assert "x-access-user-email" in kunden_search
    assert "cf-access-authenticated-user-email" in kunden_search


def test_dkh_crm_surface_uses_new_routes_not_php_worker_routes() -> None:
    source = "\n".join(
        load_text(path)
        for path in (APP_ROOT / "src").rglob("*.tsx")
    )

    for route in ("/termine", "/aufgaben", "/emails", "/kunden", "/vorgaenge", "/admin"):
        assert route in source

    assert ".php" not in source
    assert "tenant-assets/daskuechenhaus" not in source


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

    search_script = load_text(APP_ROOT / "public" / "customer-search.v1.js")
    assert "syncCaseDetails" in search_script
    assert "setupSearch" in search_script
    assert "openCreateModal: true" in search_script
    assert "openCreateModal: false" in search_script
    assert 'caseDetails.hidden = !enabled' in search_script
    assert 'field.disabled = !enabled' in search_script
