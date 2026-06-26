from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "apps" / "liquisto-workbench"


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_liquisto_workbench_exists_as_scas_tenant_app() -> None:
    assert APP_ROOT.exists()
    package_json = load_text(APP_ROOT / "package.json")
    readme = load_text(APP_ROOT / "README.md")

    assert '"name": "liquisto-workbench"' in package_json
    assert "configured Liquisto runtime workflows" in readme
    assert "Do not add\nconceptual product areas" in readme
    assert "placeholder workflows" in readme
    assert "Cloudflare Control Plane / Hetzner Runtime Plane" in readme


def test_liquisto_workbench_navigation_is_runtime_backed() -> None:
    data = load_text(APP_ROOT / "src" / "lib" / "workbench-data.ts")

    for label in ("Cockpit", "Research", "Admin"):
        assert label in data

    for removed_label in (
        "Inventory Intake",
        "Excess Analysis",
        "Initiatives",
        "Monetization",
        "Repurposing",
        "Partner Network",
    ):
        assert removed_label not in data

    assert "research-intake" in data
    assert "tenant-admin" in data


def test_liquisto_workbench_cockpit_is_an_application_surface() -> None:
    home = load_text(APP_ROOT / "src" / "app" / "page.tsx")
    section_page = load_text(APP_ROOT / "src" / "app" / "[section]" / "page.tsx")
    data = load_text(APP_ROOT / "src" / "lib" / "workbench-data.ts")
    globals_css = load_text(APP_ROOT / "src" / "app" / "globals.css")

    assert "Liquisto workspace" in home
    assert 'href: "/research"' in data
    assert "Open research" in data
    assert 'href: "/admin"' in data
    assert "Admin" in data
    assert "workspaceActions" in data
    assert "Command Center" not in home
    assert "commandSuggestions" not in data
    assert "Search research tasks" not in home
    assert "Runtime Evidence" not in home
    assert "Evidence Timeline" not in home
    assert "Runtime Configuration" not in home
    assert "Control Boundary" not in home
    assert "isolation evidence" not in home
    assert "Task Analyzer and Agent Composer" in section_page
    assert "immutable" in section_page
    assert "denials" in section_page
    assert ".hero-band" in globals_css
    assert ".system-grid" in globals_css


def test_liquisto_workbench_design_supports_sota_operations_surfaces() -> None:
    data = load_text(APP_ROOT / "src" / "lib" / "workbench-data.ts")
    home = load_text(APP_ROOT / "src" / "app" / "page.tsx")
    globals_css = load_text(APP_ROOT / "src" / "app" / "globals.css")

    assert "workspaceActions" in data
    assert "systemSignals" not in data
    assert "evidenceTimeline" not in data
    assert "dataSourceHealth" not in data
    assert "--accent-cool" in globals_css
    assert "--accent-warm" in globals_css
    assert "--success" in globals_css


def test_liquisto_workbench_css_uses_liquisto_palette() -> None:
    globals_css = load_text(APP_ROOT / "src" / "app" / "globals.css")

    for color in (
        "#007d8e",
        "#ffffff",
        "#000",
        "#333",
        "#999",
        "#b3b3b3",
        "#fafafa",
        "#5ab963",
        "#48944f",
    ):
        assert color in globals_css

    assert "--petrol" in globals_css
    assert "--white" in globals_css
    assert "--black" in globals_css
    assert "--medium-sea-green" in globals_css
    assert "--sea-green" in globals_css


def test_liquisto_workbench_uses_cloudflare_access_identity_header() -> None:
    auth = load_text(APP_ROOT / "src" / "lib" / "auth.ts")
    top_bar = load_text(APP_ROOT / "src" / "components" / "chrome" / "top-bar.tsx")

    assert "x-liquisto-user-email" in auth
    assert "cf-access-authenticated-user-email" in auth
    assert "liquisto.cloud" in top_bar
    assert "Cloudflare Access" in top_bar
    assert "Search tenant authority" not in top_bar
    assert "Search research" not in top_bar


def test_liquisto_workbench_ui_copy_is_english() -> None:
    source_files = [
        APP_ROOT / "src" / "app" / "page.tsx",
        APP_ROOT / "src" / "app" / "[section]" / "page.tsx",
        APP_ROOT / "src" / "components" / "chrome" / "top-bar.tsx",
        APP_ROOT / "src" / "lib" / "workbench-data.ts",
    ]
    combined = "\n".join(load_text(path) for path in source_files)

    forbidden_fragments = (
        " oder ",
        " und ",
        " fuer ",
        "Geschaeft",
        "Monetarisierung",
        "Freigabe",
        "Freigaben",
        "Angemeldet",
        "Benutzername",
        "Passwort",
        "Heute",
        "Morgen",
        "Pruefung",
        "Prüfung",
        "prüf",
        "veränderlich",
    )
    for fragment in forbidden_fragments:
        assert fragment not in combined
