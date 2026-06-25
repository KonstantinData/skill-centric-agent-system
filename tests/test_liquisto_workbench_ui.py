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
    assert "Liquisto business processes" in readme
    assert "not a Streamlit replacement" in readme
    assert "not a SCAS-first" in readme
    assert "Cloudflare Control Plane / Hetzner Runtime Plane" in readme


def test_liquisto_workbench_navigation_prioritizes_business_processes() -> None:
    data = load_text(APP_ROOT / "src" / "lib" / "workbench-data.ts")

    for label in (
        "Cockpit",
        "Inventory Intake",
        "Excess Analysis",
        "Initiatives",
        "Monetization",
        "Repurposing",
        "Partner Network",
        "SCAS Workbench",
    ):
        assert label in data

    assert "Tasks" in data
    assert "Agent Runs" in data
    assert "Approvals" in data
    assert "SCAS Workbench as one register" in load_text(APP_ROOT / "README.md")
    assert "Technical authority: liquisto.cloud" in data
    assert "Control Plane: Cloudflare" in data
    assert "Runtime Plane: Hetzner" in data
    assert "Runtime model: single agent, immutable task profile" in data
    assert "Cross-tenant access: fail closed" in data


def test_liquisto_workbench_surfaces_business_processes_not_marketing_site() -> None:
    home = load_text(APP_ROOT / "src" / "app" / "page.tsx")
    section_page = load_text(APP_ROOT / "src" / "app" / "[section]" / "page.tsx")
    globals_css = load_text(APP_ROOT / "src" / "app" / "globals.css")

    assert "Geschaeftsprozess-Plattform" in home
    assert "Excess Inventory" in home
    assert "Monetarisierung" in home
    assert "Repurposing" in home
    assert "SCAS Workbench ist ein Register" in home
    assert "Task Analyzer und Agent Composer" in section_page
    assert "unveränderlichen Runtime Profile" in section_page
    assert "Denials" in section_page
    assert ".hero-band" in globals_css
    assert ".metric-grid" in globals_css
    assert ".command-surface" in globals_css
    assert ".system-grid" in globals_css
    assert ".timeline" in globals_css
    assert ".source-table" in globals_css


def test_liquisto_workbench_design_supports_sota_operations_surfaces() -> None:
    data = load_text(APP_ROOT / "src" / "lib" / "workbench-data.ts")
    home = load_text(APP_ROOT / "src" / "app" / "page.tsx")
    globals_css = load_text(APP_ROOT / "src" / "app" / "globals.css")

    assert "commandSuggestions" in data
    assert "systemSignals" in data
    assert "businessProcesses" in data
    assert "scasWorkbenchAreas" in data
    assert "evidenceTimeline" in data
    assert "dataSourceHealth" in data
    assert "executionPhases" in data
    assert "Command Center" in home
    assert "SCAS Workbench Register" in home
    assert "Evidence Timeline" in home
    assert "Data Source Health" in home
    assert "progress-track" in home
    assert "--accent-cool" in globals_css
    assert "--accent-warm" in globals_css
    assert "--success" in globals_css
    assert ".work-table" in globals_css
    assert ".phase-rail" in globals_css
    assert ".progress-track" in globals_css


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
