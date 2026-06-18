from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

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


def test_business_ui_loads_daskuechenhaus_tenant_shell() -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()

    shell = streamlit_business_ui_app.build_tenant_shell(
        tenants["daskuechenhaus"]
    )

    assert shell.tenant_id == "daskuechenhaus"
    assert shell.area_id == "daskuechenhaus"
    assert shell.legal_name == "das küchenhaus ralph schober GmbH"
    assert shell.hostname == "daskuechenhaus.condata.io"
    assert shell.logo_path is None
    assert shell.admin_routes == ("/admin/users", "/admin/roles", "/admin/settings")
    assert shell.role_names == ("Tenant Owner", "Researcher")
    assert shell.data_sources == ("Daskuechenhaus Website",)
    assert "keine Cross-Tenant" in shell.isolation_summary


def test_business_ui_branding_is_loaded_from_selected_tenant_metadata() -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()

    liquisto_branding = streamlit_business_ui_app.build_tenant_branding(
        tenants["liquisto"]
    )
    daskuechenhaus_branding = streamlit_business_ui_app.build_tenant_branding(
        tenants["daskuechenhaus"]
    )
    demo_branding = streamlit_business_ui_app.build_tenant_branding(
        tenants["demo-tenant"]
    )

    assert liquisto_branding.display_name == "Liquisto"
    assert liquisto_branding.hostname == "liquisto.condata.io"
    assert liquisto_branding.logo_path == "assets/images/liquisto/liquisto_logo.png"
    assert liquisto_branding.landing_type == "internal-operations-dashboard"
    assert liquisto_branding.area_presentation == "tiles"
    assert daskuechenhaus_branding.display_name == "das küchenhaus"
    assert daskuechenhaus_branding.hostname == "daskuechenhaus.condata.io"
    assert daskuechenhaus_branding.logo_path is None
    assert daskuechenhaus_branding.landing_type == "internal-operations-dashboard"
    assert demo_branding.display_name == "Demo Tenant"
    assert demo_branding.hostname == "demo-tenant.example.invalid"
    assert demo_branding.logo_path is None
    assert "Liquisto" not in demo_branding.display_name


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
    assert admin.workflows[0] == {
        "workflow": "Users",
        "route": "/admin/users",
        "authority": "tenant-admin",
        "mode": "read-only fixture",
    }
    assert admin.settings["assignment_model"] == "users-receive-roles-only"
    assert admin.settings["shared_promotion_allowed"] == "False"
    assert "Control API audit event path" in admin.audit_summary


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


def test_business_ui_navigation_is_role_aware() -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    tenant = tenants["liquisto"]

    researcher_areas = streamlit_business_ui_app.build_workspace_areas(
        tenant,
        ("liquisto-researcher",),
    )
    owner_areas = streamlit_business_ui_app.build_workspace_areas(
        tenant,
        ("liquisto-owner",),
    )
    researcher_navigation = streamlit_business_ui_app.build_tenant_navigation_items(
        researcher_areas
    )
    owner_navigation = streamlit_business_ui_app.build_tenant_navigation_items(
        owner_areas
    )

    assert [item.route for item in researcher_navigation] == ["/", "/research"]
    assert [item.route for item in owner_navigation] == ["/", "/research", "/admin"]
    assert researcher_navigation[0].required_capability is None
    assert owner_navigation[-1].admin_only is True
    assert owner_navigation[-1].required_capability == "tenant-admin"


def test_business_ui_dashboard_cards_are_tenant_scoped_and_role_aware() -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    tenant = tenants["liquisto"]
    shell = streamlit_business_ui_app.build_tenant_shell(tenant)
    admin = streamlit_business_ui_app.build_tenant_admin_section(tenant)
    researcher_session = streamlit_business_ui_app.TenantSession(
        principal_id="researcher",
        tenant_id="liquisto",
        membership_id="membership",
        role_ids=("liquisto-researcher",),
        capabilities=frozenset({"research"}),
        source="trusted-upstream",
    )
    owner_session = streamlit_business_ui_app.TenantSession(
        principal_id="owner",
        tenant_id="liquisto",
        membership_id="membership",
        role_ids=("liquisto-owner",),
        capabilities=frozenset({"research", "tenant-admin"}),
        source="trusted-upstream",
    )

    researcher_cards = streamlit_business_ui_app.build_tenant_dashboard_cards(
        shell,
        admin,
        streamlit_business_ui_app.build_workspace_areas(
            tenant,
            researcher_session.role_ids,
        ),
        researcher_session,
    )
    owner_cards = streamlit_business_ui_app.build_tenant_dashboard_cards(
        shell,
        admin,
        streamlit_business_ui_app.build_workspace_areas(tenant, owner_session.role_ids),
        owner_session,
    )

    assert researcher_cards[0].value == "liquisto.condata.io"
    assert researcher_cards[0].detail == "liquisto via trusted-upstream"
    assert researcher_cards[1].value == "1"
    assert researcher_cards[3].value == "Gesperrt"
    assert researcher_cards[3].state == "restricted"
    assert owner_cards[1].value == "2"
    assert owner_cards[3].value == "Aktiv"
    assert "/admin/users" in owner_cards[3].detail


def test_business_ui_dashboard_reports_empty_state_for_unmatched_role() -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    tenant = tenants["liquisto"]
    shell = streamlit_business_ui_app.build_tenant_shell(tenant)
    admin = streamlit_business_ui_app.build_tenant_admin_section(tenant)
    session = streamlit_business_ui_app.TenantSession(
        principal_id="unknown",
        tenant_id="liquisto",
        membership_id="membership",
        role_ids=("unknown-role",),
        capabilities=frozenset(),
        source="local-fixture",
    )

    cards = streamlit_business_ui_app.build_tenant_dashboard_cards(
        shell,
        admin,
        streamlit_business_ui_app.build_workspace_areas(tenant, session.role_ids),
        session,
    )

    assert cards[1].value == "0"
    assert cards[1].detail == "Keine freigegeben"
    assert cards[1].state == "empty"


def test_business_ui_launch_smoke_contract_covers_accessibility_labels() -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    tenant = tenants["liquisto"]

    shell = streamlit_business_ui_app.build_tenant_shell(tenant)
    admin = streamlit_business_ui_app.build_tenant_admin_section(tenant)
    researcher_areas = streamlit_business_ui_app.build_workspace_areas(
        tenant,
        ("liquisto-researcher",),
    )
    owner_areas = streamlit_business_ui_app.build_workspace_areas(
        tenant,
        ("liquisto-owner",),
    )

    assert shell.hostname == "liquisto.condata.io"
    assert all(area.display_name and area.description for area in owner_areas)
    assert all(area.route.startswith("/") for area in owner_areas)
    assert all(workflow["route"].startswith("/admin/") for workflow in admin.workflows)
    assert {area.area_id for area in researcher_areas} == {"research"}
    assert {area.area_id for area in owner_areas} == {"research", "tenant-admin"}
    assert all(area.required_capability != "tenant-admin" for area in researcher_areas)
    assert any(area.admin_only for area in owner_areas)


def test_business_ui_role_ids_from_env_does_not_accept_unknown_roles(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    monkeypatch.setenv("SCAS_UI_ROLE_IDS", "unknown-role")

    assert streamlit_business_ui_app.role_ids_from_env(tenants["liquisto"]) == (
        "liquisto-researcher",
    )


def test_business_ui_fixture_mode_allows_local_tenant_selection(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    monkeypatch.delenv("SCAS_UI_AUTH_MODE", raising=False)
    monkeypatch.delenv("SCAS_UI_TENANT_ID", raising=False)

    assert streamlit_business_ui_app.resolve_runtime_tenant_id(tenants) is None


def test_business_ui_required_mode_requires_server_bound_tenant(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "required")
    monkeypatch.delenv("SCAS_UI_TENANT_ID", raising=False)

    with pytest.raises(streamlit_business_ui_app.TenantSessionError, match="TENANT_ID"):
        streamlit_business_ui_app.resolve_runtime_tenant_id(tenants)


def test_business_ui_server_bound_tenant_hides_cross_tenant_selection(
    monkeypatch,
) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "required")
    monkeypatch.setenv("SCAS_UI_TENANT_ID", "liquisto")

    assert streamlit_business_ui_app.resolve_runtime_tenant_id(tenants) == "liquisto"


def test_business_ui_server_bound_tenant_rejects_unknown_tenant(
    monkeypatch,
) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "required")
    monkeypatch.setenv("SCAS_UI_TENANT_ID", "missing-tenant")

    with pytest.raises(streamlit_business_ui_app.TenantSessionError, match="available"):
        streamlit_business_ui_app.resolve_runtime_tenant_id(tenants)


def test_business_ui_fixture_session_uses_local_role_selection(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    monkeypatch.delenv("SCAS_UI_AUTH_MODE", raising=False)
    monkeypatch.setenv("SCAS_UI_ROLE_IDS", "liquisto-owner")

    session = streamlit_business_ui_app.authenticated_session_from_env(tenants["liquisto"])

    assert session.source == "local-fixture"
    assert session.role_ids == ("liquisto-owner",)
    assert "tenant-admin" in session.capabilities


def test_business_ui_required_auth_fails_closed_without_session_context(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "required")
    monkeypatch.delenv("SCAS_UI_SESSION_CONTEXT_JSON", raising=False)

    with pytest.raises(streamlit_business_ui_app.TenantSessionError, match="required"):
        streamlit_business_ui_app.authenticated_session_from_env(tenants["liquisto"])


def test_business_ui_required_auth_uses_session_roles_not_ui_env_roles(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "required")
    monkeypatch.setenv("SCAS_UI_UPSTREAM_AUTH_TRUSTED", "true")
    monkeypatch.setenv("SCAS_UI_ROLE_IDS", "liquisto-owner")
    monkeypatch.setenv(
        "SCAS_UI_SESSION_CONTEXT_JSON",
        json.dumps(
            {
                "tenant_id": "liquisto",
                "principal_id": "liquisto-research-user",
                "membership_id": "liquisto-membership-researcher",
                "role_ids": ["liquisto-researcher"],
            }
        ),
    )

    session = streamlit_business_ui_app.authenticated_session_from_env(tenants["liquisto"])

    assert session.source == "trusted-upstream"
    assert session.role_ids == ("liquisto-researcher",)
    assert "tenant-admin" not in session.capabilities


def test_business_ui_required_auth_rejects_unknown_session_role(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "required")
    monkeypatch.setenv("SCAS_UI_UPSTREAM_AUTH_TRUSTED", "true")
    monkeypatch.setenv(
        "SCAS_UI_SESSION_CONTEXT_JSON",
        json.dumps(
            {
                "tenant_id": "liquisto",
                "principal_id": "liquisto-research-user",
                "membership_id": "liquisto-membership-researcher",
                "role_ids": ["demo-tenant-admin"],
            }
        ),
    )

    with pytest.raises(streamlit_business_ui_app.TenantSessionError, match="unknown"):
        streamlit_business_ui_app.authenticated_session_from_env(tenants["liquisto"])


def test_business_ui_required_auth_rejects_missing_trusted_upstream(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "required")
    monkeypatch.delenv("SCAS_UI_UPSTREAM_AUTH_TRUSTED", raising=False)
    monkeypatch.setenv(
        "SCAS_UI_SESSION_CONTEXT_JSON",
        json.dumps(
            {
                "tenant_id": "liquisto",
                "principal_id": "liquisto-owner-user",
                "membership_id": "liquisto-membership-owner",
                "role_ids": ["liquisto-owner"],
            }
        ),
    )

    with pytest.raises(streamlit_business_ui_app.TenantSessionError, match="upstream"):
        streamlit_business_ui_app.authenticated_session_from_env(tenants["liquisto"])


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
        captured["user_agent"] = request.headers["User-agent"]
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
        "user_agent": "scas-streamlit-business-ui/1.0",
        "timeout": 3.0,
    }
    assert shell.role_names == ("Tenant Owner",)
    assert shell.data_sources == ("Liquisto Website",)
    assert "Backend-geprüfte" in shell.isolation_summary
    assert admin.users[0]["membership_id"] == "liquisto-membership-owner"
    assert admin.roles[0]["capabilities"] == "research, tenant-admin"
    assert admin.workflows[0]["mode"] == "Control API"
    assert "Control API audit events" in admin.audit_summary
