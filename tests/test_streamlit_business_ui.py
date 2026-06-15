from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

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
    assert shell.legal_name == "Liquisto Technologies GmbH"
    assert shell.hostname == "liquisto.condata.io"
    assert shell.logo_path == "assets/images/liquisto/liquisto_logo.png"
    assert shell.admin_routes == ("/admin/users", "/admin/roles", "/admin/settings")
    assert shell.role_names == ("Tenant Owner", "Researcher")
    assert shell.data_sources == ("Liquisto Website",)
    assert "keine Cross-Tenant" in shell.isolation_summary


def test_business_ui_builds_read_only_tenant_admin_sections() -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()

    admin = streamlit_business_ui_app.build_tenant_admin_section(tenants["liquisto"])

    assert admin.users == (
        {
            "user": "Initial owner pending",
            "status": "pending",
            "roles": "Tenant Owner",
        },
    )
    assert admin.roles[0]["role_id"] == "liquisto-owner"
    assert admin.roles[0]["capabilities"] == "research, tenant-admin"
    assert admin.settings["assignment_model"] == "users-receive-roles-only"
    assert admin.settings["shared_promotion_allowed"] == "False"


def test_business_ui_builds_research_tiles_for_researcher_role() -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()

    areas = streamlit_business_ui_app.build_workspace_areas(
        tenants["liquisto"],
        ("liquisto-researcher",),
    )

    assert [area.area_id for area in areas] == ["research"]
    assert areas[0].route == "/research"
    assert areas[0].required_capability == "research"
    assert areas[0].admin_only is False


def test_business_ui_builds_admin_tiles_only_for_admin_capability() -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()

    owner_areas = streamlit_business_ui_app.build_workspace_areas(
        tenants["liquisto"],
        ("liquisto-owner",),
    )
    unknown_areas = streamlit_business_ui_app.build_workspace_areas(
        tenants["liquisto"],
        ("unknown-role",),
    )

    assert [area.area_id for area in owner_areas] == ["research", "tenant-admin"]
    assert owner_areas[1].admin_only is True
    assert unknown_areas == ()


def test_business_ui_role_ids_from_env_does_not_accept_unknown_roles(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    monkeypatch.setenv("SCAS_UI_ROLE_IDS", "unknown-role")

    assert streamlit_business_ui_app.role_ids_from_env(tenants["liquisto"]) == (
        "liquisto-researcher",
    )


def test_business_ui_loads_tenant_admin_context_from_control_api(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return (
                b'{"tenant":{"tenant_id":"liquisto","area_id":"liquisto",'
                b'"display_name":"Liquisto","status":"setup",'
                b'"hostname":{"hostname":"liquisto.condata.io"}},'
                b'"admin":{"admin_routes":["/admin/users","/admin/roles"]},'
                b'"users":[{"membership_id":"liquisto-membership-owner",'
                b'"principal_id":"liquisto-owner","status":"active",'
                b'"role_ids":["liquisto-owner"]}],'
                b'"roles":[{"id":"liquisto-owner","display_name":"Tenant Owner",'
                b'"role_type":"system","capability_grants":["research","tenant-admin"],'
                b'"data_source_grants":[{"data_source_id":"liquisto-website"}]}],'
                b'"data_sources":[{"display_name":"Liquisto Website"}],'
                b'"settings":{"assignment_model":"users-receive-roles-only"}}'
            )

    def fake_urlopen(request, timeout: float) -> FakeResponse:
        captured["url"] = request.full_url
        captured["authorization"] = request.headers["Authorization"]
        captured["hostname"] = request.headers["X-scas-tenant-hostname"]
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(streamlit_business_ui_app.urlrequest, "urlopen", fake_urlopen)
    config = streamlit_business_ui_app.TenantAdminApiConfig(
        base_url="https://control-api.example.invalid",
        token="tenant-admin-token",
        timeout_seconds=3.0,
    )

    context = streamlit_business_ui_app.load_tenant_admin_context_from_api(
        config,
        "liquisto",
        "liquisto.condata.io",
    )
    shell = streamlit_business_ui_app.build_tenant_shell_from_admin_context(context)
    admin = streamlit_business_ui_app.build_tenant_admin_section_from_context(context)

    assert captured == {
        "url": "https://control-api.example.invalid/tenant-admin/tenants/liquisto",
        "authorization": "Bearer tenant-admin-token",
        "hostname": "liquisto.condata.io",
        "timeout": 3.0,
    }
    assert shell.role_names == ("Tenant Owner",)
    assert shell.data_sources == ("Liquisto Website",)
    assert "Backend-geprüfte" in shell.isolation_summary
    assert admin.users[0]["membership_id"] == "liquisto-membership-owner"
    assert admin.roles[0]["capabilities"] == "research, tenant-admin"
