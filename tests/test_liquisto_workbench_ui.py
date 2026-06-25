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
    assert "SCAS architecture" in readme
    assert "not a Streamlit replacement" in readme
    assert "Cloudflare Control Plane / Hetzner Runtime Plane" in readme


def test_liquisto_workbench_navigation_matches_scas_operating_model() -> None:
    data = load_text(APP_ROOT / "src" / "lib" / "workbench-data.ts")

    for label in (
        "Cockpit",
        "Tasks",
        "Research",
        "Cases",
        "Knowledge",
        "Agent Runs",
        "Approvals",
        "Data Sources",
        "Audit",
        "Admin",
    ):
        assert label in data

    assert "Technical authority: liquisto.cloud" in data
    assert "Control Plane: Cloudflare" in data
    assert "Runtime Plane: Hetzner" in data
    assert "Runtime model: single agent, immutable task profile" in data
    assert "Cross-tenant access: fail closed" in data


def test_liquisto_workbench_surfaces_agent_governance_not_marketing_site() -> None:
    home = load_text(APP_ROOT / "src" / "app" / "page.tsx")
    section_page = load_text(APP_ROOT / "src" / "app" / "[section]" / "page.tsx")
    globals_css = load_text(APP_ROOT / "src" / "app" / "globals.css")

    assert "Operations Workbench" in home
    assert "ein Runtime-Agent" in home
    assert "tenant-spezifische Profile" in home
    assert "kontrollierte Skills" in home
    assert "überprüfbare" in home
    assert "Task Analyzer und Agent Composer" in section_page
    assert "unveränderlichen Runtime Profile" in section_page
    assert "Denials" in section_page
    assert ".hero-band" in globals_css
    assert ".metric-grid" in globals_css


def test_liquisto_workbench_uses_cloudflare_access_identity_header() -> None:
    auth = load_text(APP_ROOT / "src" / "lib" / "auth.ts")
    top_bar = load_text(APP_ROOT / "src" / "components" / "chrome" / "top-bar.tsx")

    assert "x-liquisto-user-email" in auth
    assert "cf-access-authenticated-user-email" in auth
    assert "liquisto.cloud" in top_bar
    assert "Cloudflare Access" in top_bar
