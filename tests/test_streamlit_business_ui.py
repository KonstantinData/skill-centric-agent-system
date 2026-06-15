from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "apps" / "streamlit_business_ui" / "app.py"


spec = importlib.util.spec_from_file_location("streamlit_business_ui_app", APP_PATH)
assert spec is not None
streamlit_business_ui_app = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = streamlit_business_ui_app
spec.loader.exec_module(streamlit_business_ui_app)


def test_business_ui_loads_liquisto_tenant_shell() -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()

    shell = streamlit_business_ui_app.build_tenant_shell(tenants["liquisto"])

    assert shell.tenant_id == "liquisto"
    assert shell.area_id == "liquisto"
    assert shell.hostname == "liquisto.condata.io"
    assert shell.admin_routes == ("/admin/users", "/admin/roles", "/admin/settings")
    assert shell.role_names == ("Tenant Owner", "Researcher")
    assert shell.data_sources == ("Liquisto Website",)
    assert "keine Cross-Tenant" in shell.isolation_summary
