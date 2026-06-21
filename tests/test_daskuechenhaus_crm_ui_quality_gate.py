from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_SOURCE_PATH = (
    REPO_ROOT / "workers" / "es-daskuechenhaus-site" / "src" / "index.ts"
)


def load_worker_source() -> str:
    return WORKER_SOURCE_PATH.read_text(encoding="utf-8")


def test_crm_ui_uses_tenant_owned_branding_without_svg_logo_fallback() -> None:
    source = load_worker_source()

    assert "DKH_TENANT_UI" in source
    assert 'assetScope: "tenant-owned"' in source
    assert "/tenant-assets/daskuechenhaus/logo.svg" in source
    assert '<img class="tenant-logo"' in source
    assert "LOGO_MARKUP" not in source
    assert "svg.logo" not in source


def test_crm_command_center_has_accessible_search_and_scas_status() -> None:
    source = load_worker_source()

    assert 'aria-label="Command Center"' in source
    assert '<label for="command-search">Suche</label>' in source
    assert 'id="command-search"' in source
    assert 'type="search"' in source
    assert 'aria-label="Schnellaktionen"' in source
    assert "Vorschlaege sichtbar, Ausfuehrung nur mit Bestaetigung" not in source


def test_crm_layout_is_mobile_first_with_min_width_guards() -> None:
    source = load_worker_source()

    # Mobile-first: layout grows via min-width only, no max-width fallbacks remain.
    assert "@media (min-width: 768px)" in source
    assert "@media (min-width: 1100px)" in source
    assert "@media (max-width:" not in source

    # Desktop multi-column layout is restored inside the min-width guards.
    assert ".shell { display: grid; grid-template-columns: 252px minmax(0, 1fr); }" in source


def test_crm_touch_targets_meet_mobile_contract() -> None:
    source = load_worker_source()

    assert "min-height: 48px" in source
    assert "min-height: 44px" not in source


def test_crm_has_app_like_bottom_navigation_and_fab() -> None:
    source = load_worker_source()

    assert "renderBottomNav(" in source
    assert "renderFab(" in source
    assert 'class="tab-bar"' in source
    assert "aria-label=\"Hauptbereiche\"" in source
    # Bottom nav and FAB are mobile-only and respect the safe area.
    assert ".tab-bar { display: none; }" in source
    assert ".fab { display: none; }" in source
    assert "env(safe-area-inset-bottom)" in source


def test_crm_uses_cards_native_links_and_cls_safe_media() -> None:
    source = load_worker_source()

    # Wide customer table collapses into progressive-disclosure cards.
    assert "renderContactLinks(" in source
    assert '<details class="card">' in source
    # Native mobile protocols for one-tap contact actions.
    assert "tel:" in source
    assert "mailto:" in source
    assert "maps/search" in source
    # Fixed aspect ratio keeps cumulative layout shift at zero.
    assert "aspect-ratio: 260 / 88" in source


def test_crm_surface_keeps_outcome_first_paths_visible() -> None:
    source = load_worker_source()

    assert "<h1>Steuerung</h1>" in source
    assert "Entscheidungszentrale" in source
    assert "Jetzt bearbeiten" in source
    assert "Aktive Vorgaenge steuern" in source
    assert "Nachvollziehbare Aenderungen" in source
    assert "renderDecisionQueue" in source
    assert "renderCustomerFocus" in source
    assert "renderAuditTrail" in source
    assert 'url.pathname === "/emails.php"' in source
    assert "renderEmailsPage" in source
    assert 'renderSideNav("emails"' in source
    assert 'href="/emails.php"' in source
    assert "Faellige Aufgaben" in source
    assert "Eingang und Zuordnung" in source
    assert "customerMatchesQuery" in source
    assert "renderCommandCenter({" in source


def test_crm_surface_rejects_non_production_language() -> None:
    source = load_worker_source()

    forbidden_terms = [
        "Blackbox",
        "Funkverkehr",
        "Flugplan",
        "Instrumententafel",
        "Was jetzt kippen kann",
        "Kontrollverlust",
        "EXIT",
        "Aufgabe(n)",
        "E-Mail(s)",
        "Vorgang/Vorgaenge",
        "Das Cockpit zeigt",
        "CRM Steuerung",
        "entscheidungsrelevante Arbeit",
        "Team <span>Admin</span>",
        'href="/admin.php?modal=users"',
        "Aufgaben und E-Mails werden hier",
        "/aufgaben.php#emails",
        "SCAS Kontrolle",
        "SCAS-Freigaben",
        "SCAS-Vorschlaege",
        "Keine SCAS-Vorschlaege",
        "renderScasReviewQueue",
        '<span class="section-kicker">Neue Aufgabe</span><h2>Aufgabe anlegen</h2>',
        '<span class="section-kicker">Bearbeiten</span><h2>Offene Aufgaben</h2>',
        '<span class="section-kicker">Kommunikation</span><h2>E-Mail-Eingang</h2>',
        '<span class="section-kicker">Kundenbestand</span><h2>Aktuell angelegte Kunden</h2>',
        "Anlage(n)",
    ]

    for term in forbidden_terms:
        assert term not in source
