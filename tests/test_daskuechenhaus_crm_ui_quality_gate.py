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
    assert "Vorschlaege sichtbar, Ausfuehrung nur mit Bestaetigung" in source


def test_crm_layout_has_responsive_grid_guards() -> None:
    source = load_worker_source()

    assert "@media (max-width: 1100px)" in source
    assert "@media (max-width: 920px)" in source
    assert "@media (max-width: 780px)" in source
    assert ".command-search { grid-template-columns: 1fr; }" in source
    assert ".command-actions { grid-template-columns: repeat(2, minmax(0, 1fr)); }" in source
    assert ".shell { grid-template-columns: 1fr; }" in source
    assert ".risk-item { grid-template-columns: auto minmax(0, 1fr); }" in source


def test_crm_surface_keeps_outcome_first_paths_visible() -> None:
    source = load_worker_source()

    assert "Kontrollverlust" in source
    assert "Was jetzt kippen kann" in source
    assert "Heute arbeiten" in source
    assert "Blackbox" in source
    assert "customerMatchesQuery" in source
    assert "renderCommandCenter(state.current_user" in source
