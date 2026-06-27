from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "apps" / "khh-workbench"


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_khh_workbench_exists_as_product_facing_app() -> None:
    assert APP_ROOT.exists()
    package_json = load_text(APP_ROOT / "package.json")
    readme = load_text(APP_ROOT / "README.md")

    assert '"name": "khh-workbench"' in package_json
    assert "kinderhaus-heuschrecken.cloud" in readme
    assert "tenant_kinderhaus" in readme
    assert "must not become a master-data" in readme
    assert "Users must not see or infer that other tenants exist" in readme


def test_khh_workbench_navigation_matches_leadership_cockpit() -> None:
    data = load_text(APP_ROOT / "src" / "lib" / "workbench-data.ts")

    for label in (
        "Heute",
        "Fristen",
        "Personal-Ampel",
        "Dienste",
        "Vorgaenge",
        "Belegung",
        "Entwicklung",
        "Dokumente",
        "Aufgaben",
    ):
        assert label in data

    assert "Keine vollstaendigen Kinder-, Eltern- oder Personalstammdaten" in data
    assert "Personenbezug nur mit Vorname, Kuerzel oder interner Referenz" in data
    assert "Meldungen an Jugendamt, KVJS oder Gesundheitsamt nur nach Freigabe" in data


def test_khh_workbench_home_is_application_surface() -> None:
    home = load_text(APP_ROOT / "src" / "app" / "page.tsx")
    section_page = load_text(APP_ROOT / "src" / "app" / "[section]" / "page.tsx")
    globals_css = load_text(APP_ROOT / "src" / "app" / "globals.css")

    assert "Leitungs-Cockpit" in home
    assert "Datenschutz-Leitplanke" in home
    assert "Agent-Hinweise" in home
    assert "Arbeitsansicht" in section_page
    assert "Beispiel ohne Stammdaten" in section_page
    assert "--foreground: #1e293b" in globals_css
    assert "--background: #fafaf7" in globals_css
    assert "--accent: #6f8f72" in globals_css
    assert "--danger-soft" in globals_css
    assert "--warning-soft" in globals_css
    assert "--success-soft" in globals_css
    assert ".day-strip" in globals_css
    assert ".nav-link" in globals_css
    assert ".section-list-item" in globals_css


def test_khh_workbench_visible_copy_hides_internal_architecture_terms() -> None:
    source_files = [
        APP_ROOT / "src" / "app" / "layout.tsx",
        APP_ROOT / "src" / "app" / "page.tsx",
        APP_ROOT / "src" / "app" / "[section]" / "page.tsx",
        APP_ROOT / "src" / "components" / "chrome" / "bottom-nav.tsx",
        APP_ROOT / "src" / "components" / "chrome" / "sidebar.tsx",
        APP_ROOT / "src" / "components" / "chrome" / "top-bar.tsx",
        APP_ROOT / "src" / "lib" / "workbench-data.ts",
    ]
    combined = "\n".join(load_text(path) for path in source_files)

    forbidden_fragments = (
        "runtime profile",
        "policy gate",
        "validator",
        "tool selection",
        "SCAS",
        "Task Analyzer",
        "Agent Composer",
        "Liquisto",
        "daskuechenhaus",
    )
    for fragment in forbidden_fragments:
        assert fragment not in combined


def test_khh_workbench_uses_cloudflare_access_identity_header() -> None:
    auth = load_text(APP_ROOT / "src" / "lib" / "auth.ts")
    top_bar = load_text(APP_ROOT / "src" / "components" / "chrome" / "top-bar.tsx")

    assert "x-khh-user-email" in auth
    assert "cf-access-authenticated-user-email" in auth
    assert "kinderhaus-heuschrecken.cloud" in top_bar
    assert "KHH Workbench" in top_bar
    assert "liquisto" not in top_bar.lower()
