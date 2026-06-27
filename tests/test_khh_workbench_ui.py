from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "apps" / "khh-workbench"
DOMAIN_ROOT = REPO_ROOT / "packages" / "tenant-workbench-domain"


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
    data = load_text(DOMAIN_ROOT / "src" / "khh.ts")
    reexport = load_text(APP_ROOT / "src" / "lib" / "workbench-data.ts")

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
    assert "lucide-react" not in data
    assert "export * from" in reexport


def test_khh_workbench_home_is_application_surface() -> None:
    home = load_text(APP_ROOT / "src" / "app" / "page.tsx")
    section_page = load_text(APP_ROOT / "src" / "app" / "[section]" / "page.tsx")
    page_hero = load_text(APP_ROOT / "src" / "components" / "chrome" / "page-hero.tsx")
    globals_css = load_text(APP_ROOT / "src" / "app" / "globals.css")
    domain = load_text(DOMAIN_ROOT / "src" / "khh.ts")

    assert "Leitungs-Cockpit" in domain
    assert "Datenschutz-Leitplanke" not in home
    assert "Agent-Hinweise" not in home
    assert "PageHero" in home
    assert "PageHero" in section_page
    assert "/kinderhaus-heuschrecken.jpg" in page_hero
    assert "Arbeitsansicht" in section_page
    assert "Beispiel ohne Stammdaten" in section_page
    assert (APP_ROOT / "public" / "kinderhaus-heuschrecken.jpg").exists()
    assert "height: 5cm" in globals_css
    assert "--foreground: #1e293b" in globals_css
    assert "--background: #fafaf7" in globals_css
    assert "--accent: #6f8f72" in globals_css
    assert "--danger-soft" in globals_css
    assert "--warning-soft" in globals_css
    assert "--success-soft" in globals_css
    assert ".day-strip" in globals_css
    assert ".nav-link" in globals_css
    assert ".section-list-item" in globals_css
    assert "--shadow-strong" in globals_css


def test_khh_workbench_visible_copy_hides_internal_architecture_terms() -> None:
    source_files = [
        APP_ROOT / "src" / "app" / "layout.tsx",
        APP_ROOT / "src" / "app" / "page.tsx",
        APP_ROOT / "src" / "app" / "[section]" / "page.tsx",
        APP_ROOT / "src" / "components" / "chrome" / "bottom-nav.tsx",
        APP_ROOT / "src" / "components" / "chrome" / "page-hero.tsx",
        APP_ROOT / "src" / "components" / "chrome" / "sidebar.tsx",
        APP_ROOT / "src" / "components" / "chrome" / "top-bar.tsx",
    ]
    combined = "\n".join(load_text(path) for path in source_files)
    visible_copy_surface = "\n".join(
        line
        for line in combined.splitlines()
        if not line.strip().startswith("import ") and "@scas/" not in line
    )

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
        "tenant",
        "kinderhaus-heuschrecken.cloud",
    )
    for fragment in forbidden_fragments:
        assert fragment not in visible_copy_surface


def test_khh_workbench_uses_cloudflare_access_identity_header() -> None:
    auth = load_text(APP_ROOT / "src" / "lib" / "auth.ts")
    client = load_text(REPO_ROOT / "packages" / "tenant-workbench-client" / "src" / "index.ts")
    top_bar = load_text(APP_ROOT / "src" / "components" / "chrome" / "top-bar.tsx")

    assert "createCloudflareAccessHeaderAuthAdapter" in auth
    assert "x-khh-user-email" in client
    assert "cf-access-authenticated-user-email" in client
    assert "Leitungs-Cockpit" in top_bar
    assert "Heute, Dienste, Fristen und Aufgaben" in top_bar
    assert "liquisto" not in top_bar.lower()
