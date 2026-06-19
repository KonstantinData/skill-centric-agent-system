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


class StreamlitStop(Exception):
    pass


class FakeSidebar:
    def __init__(self, streamlit: FakeStreamlit) -> None:
        self._streamlit = streamlit

    def title(self, text: str) -> None:
        self._streamlit.events.append(("sidebar_title", text))

    def caption(self, text: str) -> None:
        self._streamlit.events.append(("sidebar_caption", text))

    def write(self, value: Any) -> None:
        self._streamlit.events.append(("sidebar_write", value))

    def selectbox(self, label: str, *, options: list[str], index: int) -> str:
        self._streamlit.events.append(("sidebar_selectbox", label, tuple(options), index))
        return options[index]

    def button(self, label: str, **kwargs: Any) -> bool:
        self._streamlit.events.append(("sidebar_button", label, kwargs))
        return self._streamlit.sidebar_button_values.get(label, False)

    def markdown(self, *args: Any, **kwargs: Any) -> None:
        self._streamlit.events.append(("sidebar_markdown", args, kwargs))


class FakeColumn:
    def __init__(self, streamlit: FakeStreamlit, index: int) -> None:
        self._streamlit = streamlit
        self._index = index

    def __enter__(self) -> FakeColumn:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def markdown(self, *args: Any, **kwargs: Any) -> None:
        self._streamlit.events.append(("column_markdown", self._index, args, kwargs))

    def metric(self, label: str, value: Any) -> None:
        self._streamlit.events.append(("column_metric", self._index, label, value))


class FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {}
        self.events: list[tuple[Any, ...]] = []
        self.text_input_values: dict[str, str] = {}
        self.selectbox_values: dict[str, str] = {}
        self.checkbox_values: dict[str, bool] = {}
        self.sidebar_button_values: dict[str, bool] = {}
        self.form_submitted = False
        self.query_params: dict[str, str] = {}
        self.sidebar = FakeSidebar(self)

    def set_page_config(self, **kwargs: Any) -> None:
        self.events.append(("set_page_config", kwargs))

    def __enter__(self) -> FakeStreamlit:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def form(self, key: str) -> FakeStreamlit:
        self.events.append(("form", key))
        return self

    def dialog(self, title: str, **kwargs: Any) -> Any:
        self.events.append(("dialog", title, kwargs))

        def decorator(func: Any) -> Any:
            def wrapper(*args: Any, **inner_kwargs: Any) -> Any:
                self.events.append(("dialog_open", title))
                return func(*args, **inner_kwargs)

            return wrapper

        return decorator

    def expander(self, label: str) -> FakeStreamlit:
        self.events.append(("expander", label))
        return self

    def markdown(self, *args: Any, **kwargs: Any) -> None:
        self.events.append(("markdown", args, kwargs))

    def caption(self, text: str) -> None:
        self.events.append(("caption", text))

    def info(self, text: str) -> None:
        self.events.append(("info", text))

    def success(self, text: str) -> None:
        self.events.append(("success", text))

    def error(self, text: str) -> None:
        self.events.append(("error", text))

    def warning(self, text: str) -> None:
        self.events.append(("warning", text))

    def link_button(self, label: str, url: str) -> None:
        self.events.append(("link_button", label, url))

    def button(self, label: str, **kwargs: Any) -> bool:
        self.events.append(("button", label, kwargs))
        return False

    def image(self, *args: Any, **kwargs: Any) -> None:
        self.events.append(("image", args, kwargs))

    def title(self, text: str) -> None:
        self.events.append(("title", text))

    def divider(self) -> None:
        self.events.append(("divider",))

    def subheader(self, text: str) -> None:
        self.events.append(("subheader", text))

    def columns(self, spec: int | list[float]) -> list[FakeColumn]:
        count = spec if isinstance(spec, int) else len(spec)
        self.events.append(("columns", spec))
        return [FakeColumn(self, index) for index in range(count)]

    def dataframe(self, *args: Any, **kwargs: Any) -> None:
        self.events.append(("dataframe", args, kwargs))

    def table(self, value: Any) -> None:
        self.events.append(("table", value))

    def code(self, body: str, **kwargs: Any) -> None:
        self.events.append(("code", body, kwargs))

    def text_input(self, label: str, **kwargs: Any) -> str:
        self.events.append(("text_input", label, kwargs))
        return self.text_input_values.get(label, str(kwargs.get("value", "")))

    def selectbox(self, label: str, *, options: list[str], index: int) -> str:
        self.events.append(("selectbox", label, tuple(options), index))
        return self.selectbox_values.get(label, options[index])

    def checkbox(self, label: str, **kwargs: Any) -> bool:
        self.events.append(("checkbox", label, kwargs))
        return self.checkbox_values.get(label, bool(kwargs.get("value", False)))

    def form_submit_button(self, label: str) -> bool:
        self.events.append(("form_submit_button", label))
        return self.form_submitted

    def rerun(self) -> None:
        self.events.append(("rerun",))

    def stop(self) -> None:
        raise StreamlitStop


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
    assert shell.logo_path == "assets/images/daskuechenhaus/logo_daskuechenhaus.png"
    assert shell.admin_routes == ("/admin/users", "/admin/roles", "/admin/settings")
    assert shell.role_names == ("Tenant Owner", "Tenant Admin", "Researcher")
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
    assert (
        daskuechenhaus_branding.logo_path
        == "assets/images/daskuechenhaus/logo_daskuechenhaus.png"
    )
    assert daskuechenhaus_branding.landing_type == "internal-operations-dashboard"
    assert daskuechenhaus_branding.theme == streamlit_business_ui_app.TenantTheme(
        background="#fff",
        surface="#fff",
        text="#111",
        secondary_text="#333",
        accent="#76b726",
        border="#76b726",
    )
    assert demo_branding.display_name == "Demo Tenant"
    assert demo_branding.hostname == "demo-tenant.example.invalid"
    assert demo_branding.logo_path is None
    assert "Liquisto" not in demo_branding.display_name


def test_business_ui_renders_tenant_theme_css_from_branding_metadata() -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    branding = streamlit_business_ui_app.build_tenant_branding(
        tenants["daskuechenhaus"]
    )

    css = streamlit_business_ui_app.render_tenant_theme_css(branding.theme)

    assert "--tenant-background: #fff;" in css
    assert "--tenant-text: #111;" in css
    assert "--tenant-secondary-text: #333;" in css
    assert "--tenant-accent: #76b726;" in css
    assert "letter-spacing: 0;" in css
    assert "border-right: 4px solid var(--tenant-accent);" in css
    assert '[data-testid="stMainMenuButton"]' in css
    assert "color: var(--tenant-text) !important;" in css
    assert "background: var(--tenant-surface) !important;" in css


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


def test_business_ui_daskuechenhaus_admin_role_has_no_research_or_filesystem_grants() -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    tenant = tenants["daskuechenhaus"]

    admin_role = next(
        role for role in tenant["role_bundles"] if role["id"] == "daskuechenhaus-admin"
    )
    admin_areas = streamlit_business_ui_app.build_workspace_areas(
        tenant,
        ("daskuechenhaus-admin",),
    )

    assert admin_role["capability_grants"] == ["tenant-admin", "customer-cases"]
    assert admin_role["data_source_grants"] == []
    assert admin_role["derived_runtime_modules"]["tools"] == []
    assert [area.area_id for area in admin_areas] == ["customer-cases", "tenant-admin"]


def test_business_ui_daskuechenhaus_customer_cases_area_is_role_gated() -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    tenant = tenants["daskuechenhaus"]

    owner_areas = streamlit_business_ui_app.build_workspace_areas(
        tenant,
        ("daskuechenhaus-owner",),
    )
    admin_areas = streamlit_business_ui_app.build_workspace_areas(
        tenant,
        ("daskuechenhaus-admin",),
    )
    researcher_areas = streamlit_business_ui_app.build_workspace_areas(
        tenant,
        ("daskuechenhaus-researcher",),
    )

    assert [area.area_id for area in owner_areas] == [
        "customer-cases",
        "research",
        "tenant-admin",
    ]
    assert [area.area_id for area in admin_areas] == ["customer-cases", "tenant-admin"]
    assert [area.area_id for area in researcher_areas] == ["research"]
    assert owner_areas[0].display_name == "Kunden-Vorgänge"
    assert owner_areas[0].route == "/customer-cases"
    assert owner_areas[0].required_capability == "customer-cases"


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


def test_business_ui_sidebar_navigation_sets_route_without_login_reset() -> None:
    fake_st = FakeStreamlit()
    fake_st.sidebar_button_values["Kunden-Vorgänge"] = True
    navigation_items = (
        streamlit_business_ui_app.TenantNavigationItem(
            label="Übersicht",
            route="/",
            description="",
            required_capability=None,
            admin_only=False,
        ),
        streamlit_business_ui_app.TenantNavigationItem(
            label="Kunden-Vorgänge",
            route="/customer-cases",
            description="",
            required_capability="customer-cases",
            admin_only=False,
        ),
    )

    selected_route = streamlit_business_ui_app.render_sidebar_navigation(
        fake_st,
        navigation_items,
        "/",
    )

    assert selected_route == "/customer-cases"
    assert fake_st.session_state["scas_active_route"] == "/customer-cases"
    assert fake_st.query_params["route"] == "/customer-cases"
    assert [event for event in fake_st.events if event[0] == "sidebar_button"]
    assert not [event for event in fake_st.events if event[0] == "sidebar_markdown"]


def test_business_ui_current_route_rejects_invalid_query_route() -> None:
    fake_st = FakeStreamlit()
    fake_st.query_params = {"route": "https://example.invalid"}

    assert streamlit_business_ui_app.current_route_from_query_params(fake_st) == "/"


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

    with pytest.raises(
        streamlit_business_ui_app.TenantSessionError,
        match="authenticated auth modes",
    ):
        streamlit_business_ui_app.resolve_runtime_tenant_id(tenants)


def test_business_ui_local_login_mode_requires_server_bound_tenant(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "local-login")
    monkeypatch.delenv("SCAS_UI_TENANT_ID", raising=False)

    with pytest.raises(
        streamlit_business_ui_app.TenantSessionError,
        match="authenticated auth modes",
    ):
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


def test_business_ui_local_login_hash_round_trip() -> None:
    encoded_hash = streamlit_business_ui_app.encode_login_password_hash(
        "correct horse battery staple",
        salt=b"stable-test-salt!",
    )

    assert encoded_hash.startswith("pbkdf2_sha256$600000$")
    assert streamlit_business_ui_app.verify_login_password(
        "correct horse battery staple",
        encoded_hash,
    )
    assert not streamlit_business_ui_app.verify_login_password("wrong", encoded_hash)


def test_business_ui_local_login_builds_tenant_session(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    password_hash = streamlit_business_ui_app.encode_login_password_hash(
        "tenant-password",
        salt=b"stable-test-salt!",
    )
    monkeypatch.setenv(
        "SCAS_UI_LOGIN_USERS_JSON",
        json.dumps(
            [
                {
                    "username": "daskuechenhaus-admin",
                    "tenant_id": "daskuechenhaus",
                    "principal_id": "daskuechenhaus-admin-principal",
                    "membership_id": "tm-daskuechenhaus-admin-01",
                    "role_ids": ["daskuechenhaus-admin"],
                    "password_hash": password_hash,
                }
            ]
        ),
    )

    session = streamlit_business_ui_app.local_login_session_from_credentials(
        tenants["daskuechenhaus"],
        "daskuechenhaus-admin",
        "tenant-password",
    )

    assert session.source == "local-login"
    assert session.principal_id == "daskuechenhaus-admin-principal"
    assert session.role_ids == ("daskuechenhaus-admin",)
    assert session.capabilities == frozenset({"tenant-admin", "customer-cases"})


def test_business_ui_local_login_rejects_wrong_password(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    password_hash = streamlit_business_ui_app.encode_login_password_hash(
        "tenant-password",
        salt=b"stable-test-salt!",
    )
    monkeypatch.setenv(
        "SCAS_UI_LOGIN_USERS_JSON",
        json.dumps(
            [
                {
                    "username": "daskuechenhaus-admin",
                    "tenant_id": "daskuechenhaus",
                    "principal_id": "daskuechenhaus-admin-principal",
                    "membership_id": "tm-daskuechenhaus-admin-01",
                    "role_ids": ["daskuechenhaus-admin"],
                    "password_hash": password_hash,
                }
            ]
        ),
    )

    with pytest.raises(streamlit_business_ui_app.TenantSessionError, match="Invalid"):
        streamlit_business_ui_app.local_login_session_from_credentials(
            tenants["daskuechenhaus"],
            "daskuechenhaus-admin",
            "wrong-password",
        )


def test_business_ui_local_login_rejects_unknown_role(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    password_hash = streamlit_business_ui_app.encode_login_password_hash(
        "tenant-password",
        salt=b"stable-test-salt!",
    )
    monkeypatch.setenv(
        "SCAS_UI_LOGIN_USERS_JSON",
        json.dumps(
            [
                {
                    "username": "daskuechenhaus-admin",
                    "tenant_id": "daskuechenhaus",
                    "principal_id": "daskuechenhaus-admin-principal",
                    "membership_id": "tm-daskuechenhaus-admin-01",
                    "role_ids": ["liquisto-owner"],
                    "password_hash": password_hash,
                }
            ]
        ),
    )

    with pytest.raises(streamlit_business_ui_app.TenantSessionError, match="unknown"):
        streamlit_business_ui_app.local_login_session_from_credentials(
            tenants["daskuechenhaus"],
            "daskuechenhaus-admin",
            "tenant-password",
        )


def test_business_ui_local_login_gate_accepts_submitted_credentials(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    fake_st = FakeStreamlit()
    fake_st.text_input_values = {
        "Benutzername": "daskuechenhaus-admin",
        "Passwort": "tenant-password",
    }
    fake_st.form_submitted = True
    password_hash = streamlit_business_ui_app.encode_login_password_hash(
        "tenant-password",
        salt=b"stable-test-salt!",
    )
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "local-login")
    monkeypatch.setenv(
        "SCAS_UI_LOGIN_USERS_JSON",
        json.dumps(
            [
                {
                    "username": "daskuechenhaus-admin",
                    "tenant_id": "daskuechenhaus",
                    "principal_id": "daskuechenhaus-admin-principal",
                    "membership_id": "tm-daskuechenhaus-admin-01",
                    "role_ids": ["daskuechenhaus-admin"],
                    "password_hash": password_hash,
                }
            ]
        ),
    )

    with pytest.raises(StreamlitStop):
        streamlit_business_ui_app.render_session_gate(
            fake_st,
            tenants["daskuechenhaus"],
        )

    assert fake_st.session_state["scas_tenant_session"]["source"] == "local-login"
    assert ("form_submit_button", "Einloggen") in fake_st.events
    assert ("rerun",) in fake_st.events


def test_business_ui_local_login_main_renders_standalone_page_before_sidebar(
    monkeypatch,
) -> None:
    fake_st = FakeStreamlit()
    password_hash = streamlit_business_ui_app.encode_login_password_hash(
        "tenant-password",
        salt=b"stable-test-salt!",
    )
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "local-login")
    monkeypatch.setenv("SCAS_UI_TENANT_ID", "daskuechenhaus")
    monkeypatch.setenv(
        "SCAS_UI_LOGIN_USERS_JSON",
        json.dumps(
            [
                {
                    "username": "daskuechenhaus-admin",
                    "tenant_id": "daskuechenhaus",
                    "principal_id": "daskuechenhaus-admin-principal",
                    "membership_id": "tm-daskuechenhaus-admin-01",
                    "role_ids": ["daskuechenhaus-admin"],
                    "password_hash": password_hash,
                }
            ]
        ),
    )

    with pytest.raises(StreamlitStop):
        streamlit_business_ui_app.main()

    assert ("form", "scas-local-login") in fake_st.events
    assert not [event for event in fake_st.events if event[0].startswith("sidebar_")]


def test_business_ui_main_hides_internal_tenant_metadata_after_login(
    monkeypatch,
) -> None:
    fake_st = FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "local-login")
    monkeypatch.setenv("SCAS_UI_TENANT_ID", "daskuechenhaus")
    fake_st.session_state["scas_tenant_session"] = {
        "principal_id": "daskuechenhaus-owner-principal",
        "tenant_id": "daskuechenhaus",
        "membership_id": "tm-daskuechenhaus-owner-01",
        "role_ids": ["daskuechenhaus-owner"],
        "capabilities": ["research", "tenant-admin"],
        "source": "local-login",
    }

    streamlit_business_ui_app.main()

    def iter_strings(value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            return [
                item
                for nested in value.items()
                for item in iter_strings(nested)
            ]
        if isinstance(value, (list, tuple)):
            return [item for nested in value for item in iter_strings(nested)]
        return []

    rendered_text = "\n".join(
        item for event in fake_st.events for item in iter_strings(event)
    )
    assert "das küchenhaus" in rendered_text
    assert "Kunden-Vorgänge" in rendered_text
    for hidden_text in (
        "Tenant Authority",
        "Tenant\n\ndaskuechenhaus",
        "Status\n\nsetup",
        "Hostname",
        "daskuechenhaus.condata.io",
        "Server-seitige Hostname-Autorität",
        "/admin/users",
        "/admin/roles",
        "/admin/settings",
        "Tenant Owner",
        "Tenant Admin",
        "Researcher",
        "Daskuechenhaus Website",
        "Capability:",
        "Route:",
    ):
        assert hidden_text not in rendered_text


def test_business_ui_main_hides_optional_admin_api_failures(
    monkeypatch,
) -> None:
    fake_st = FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "local-login")
    monkeypatch.setenv("SCAS_UI_TENANT_ID", "daskuechenhaus")
    monkeypatch.setenv("SCAS_CONTROL_API_URL", "https://control-api.example.invalid")
    monkeypatch.setenv("SCAS_TENANT_ADMIN_TOKEN", "test-token")
    fake_st.session_state["scas_tenant_session"] = {
        "principal_id": "daskuechenhaus-owner-principal",
        "tenant_id": "daskuechenhaus",
        "membership_id": "tm-daskuechenhaus-owner-01",
        "role_ids": ["daskuechenhaus-owner"],
        "capabilities": ["research", "tenant-admin"],
        "source": "local-login",
    }

    def failing_urlopen(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("HTTP Error 404: Not Found")

    monkeypatch.setattr(streamlit_business_ui_app.urlrequest, "urlopen", failing_urlopen)

    streamlit_business_ui_app.main()

    assert not [event for event in fake_st.events if event[0] == "warning"]


def test_business_ui_admin_dashboard_route_uses_existing_session(monkeypatch) -> None:
    fake_st = FakeStreamlit()
    fake_st.query_params = {"route": "/admin"}
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "local-login")
    monkeypatch.setenv("SCAS_UI_TENANT_ID", "daskuechenhaus")
    fake_st.session_state["scas_tenant_session"] = {
        "principal_id": "daskuechenhaus-owner-principal",
        "tenant_id": "daskuechenhaus",
        "membership_id": "tm-daskuechenhaus-owner-01",
        "role_ids": ["daskuechenhaus-owner"],
        "capabilities": ["research", "tenant-admin", "customer-cases"],
        "source": "local-login",
    }

    streamlit_business_ui_app.main()

    assert ("subheader", "Admin-Dashboard") in fake_st.events
    assert ("form", "scas-admin-password-change") in fake_st.events
    assert not [event for event in fake_st.events if event == ("form", "scas-local-login")]


def test_business_ui_admin_password_tool_generates_hash() -> None:
    fake_st = FakeStreamlit()
    fake_st.form_submitted = True
    fake_st.text_input_values = {
        "Benutzername": "konstantin",
        "Neues Passwort": "new-secure-password",
        "Neues Passwort wiederholen": "new-secure-password",
    }

    streamlit_business_ui_app.render_password_change_admin_tool(fake_st)

    code_events = [event for event in fake_st.events if event[0] == "code"]
    assert code_events
    payload = json.loads(code_events[0][1])
    assert payload["username"] == "konstantin"
    assert payload["password_hash"].startswith("pbkdf2_sha256$")
    assert streamlit_business_ui_app.verify_login_password(
        "new-secure-password",
        payload["password_hash"],
    )


def test_business_ui_local_login_renders_password_reset_fallback(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    fake_st = FakeStreamlit()
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "local-login")
    monkeypatch.delenv("SCAS_UI_PASSWORD_RESET_URL", raising=False)

    with pytest.raises(StreamlitStop):
        streamlit_business_ui_app.render_session_gate(fake_st, tenants["daskuechenhaus"])

    assert ("info", "Bitte mit Ihrem Benutzernamen anmelden") in fake_st.events
    assert ("expander", "Passwort vergessen?") in fake_st.events
    assert any(
        event == (
            "info",
            "Bitte wenden Sie sich an Ihren Administrator. "
            "Ein automatischer Passwort-Reset ist noch nicht eingerichtet.",
        )
        for event in fake_st.events
    )


def test_business_ui_local_login_renders_configured_password_reset_link(
    monkeypatch,
) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    fake_st = FakeStreamlit()
    reset_url = "https://identity.example.invalid/reset-password/daskuechenhaus"
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "local-login")
    monkeypatch.setenv("SCAS_UI_PASSWORD_RESET_URL", reset_url)

    with pytest.raises(StreamlitStop):
        streamlit_business_ui_app.render_session_gate(fake_st, tenants["daskuechenhaus"])

    assert ("link_button", "Passwort vergessen?", reset_url) in fake_st.events
    assert ("expander", "Passwort vergessen?") not in fake_st.events


def test_business_ui_builds_login_view_from_tenant_and_upstream_url(monkeypatch) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    monkeypatch.setenv(
        "SCAS_UI_LOGIN_URL",
        "https://identity.example.invalid/login/daskuechenhaus",
    )

    login_view = streamlit_business_ui_app.build_tenant_login_view(
        tenants["daskuechenhaus"]
    )

    assert login_view.tenant_id == "daskuechenhaus"
    assert login_view.display_name == "das küchenhaus"
    assert login_view.hostname == "daskuechenhaus.condata.io"
    assert login_view.login_url == "https://identity.example.invalid/login/daskuechenhaus"


def test_business_ui_required_gate_renders_login_entry_without_trusted_session(
    monkeypatch,
) -> None:
    tenants = streamlit_business_ui_app.load_tenant_registry()
    fake_st = FakeStreamlit()
    login_url = "https://identity.example.invalid/login/daskuechenhaus"
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "required")
    monkeypatch.setenv("SCAS_UI_LOGIN_URL", login_url)
    monkeypatch.delenv("SCAS_UI_UPSTREAM_AUTH_TRUSTED", raising=False)
    monkeypatch.delenv("SCAS_UI_SESSION_CONTEXT_JSON", raising=False)

    with pytest.raises(StreamlitStop):
        streamlit_business_ui_app.render_session_gate(fake_st, tenants["daskuechenhaus"])

    assert ("link_button", "Einloggen", login_url) in fake_st.events
    assert not [event for event in fake_st.events if event[0] == "error"]


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


def test_business_ui_customer_cases_api_config_from_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "SCAS_CUSTOMER_CASES_API_URL",
        "https://cases.example.invalid",
    )
    monkeypatch.setenv("SCAS_CUSTOMER_CASES_API_SECRET", "token")

    config = streamlit_business_ui_app.customer_cases_api_config_from_env()

    assert config == streamlit_business_ui_app.CustomerCasesApiConfig(
        base_url="https://cases.example.invalid",
        token="token",
    )


def test_business_ui_loads_customer_cases_from_api(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return (
                b'{"data":[{"case_number":"VG-2026-0001",'
                b'"customer_number":"K-2026-0001",'
                b'"customer_full_name":"Maria Hoffmann",'
                b'"phase":1,"phase_label":"Neuer Kontakt","priority":"normal",'
                b'"status":"active","has_attention":1}],"count":1}'
            )

    def fake_urlopen(request, timeout: float) -> FakeResponse:
        captured["url"] = request.full_url
        captured["authorization"] = request.headers["Authorization"]
        captured["user_agent"] = request.headers["User-agent"]
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(streamlit_business_ui_app.urlrequest, "urlopen", fake_urlopen)
    config = streamlit_business_ui_app.CustomerCasesApiConfig(
        base_url="https://cases.example.invalid",
        token="token",
        timeout_seconds=2.0,
    )

    payload = streamlit_business_ui_app.load_customer_cases_from_api(config)

    assert captured == {
        "url": "https://cases.example.invalid/tenant-cases",
        "authorization": "Bearer token",
        "user_agent": "scas-streamlit-business-ui/1.0",
        "timeout": 2.0,
    }
    assert payload["count"] == 1


def test_business_ui_creates_customer_case_with_actor_header(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"data":{"id":"case-001"}}'

    def fake_urlopen(request, timeout: float) -> FakeResponse:
        captured["url"] = request.full_url
        captured["authorization"] = request.headers["Authorization"]
        captured["content_type"] = request.headers["Content-type"]
        captured["actor"] = request.headers["X-actor"]
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(streamlit_business_ui_app.urlrequest, "urlopen", fake_urlopen)
    config = streamlit_business_ui_app.CustomerCasesApiConfig(
        base_url="https://cases.example.invalid",
        token="token",
        timeout_seconds=2.0,
    )

    payload = streamlit_business_ui_app.create_customer_case_in_api(
        config,
        actor="daskuechenhaus-owner-principal",
        carat_order_number="",
        customer_type="private",
        salutation="Frau",
        first_name="Maria",
        last_name="Hoffmann",
        company_name="",
        company_name_2="",
        company_name_3="",
        company_name_4="",
        vat_id="",
        tax_number="",
        customer_phone="0711 123456",
        customer_mobile="0171 123456",
        customer_email="maria@example.invalid",
        iso_country_code="DE",
        postal_code="70173",
        city="Stuttgart",
        is_nato=False,
        has_custom_vat=True,
        custom_vat_rate="17.5",
        custom_vat_rate_label="Individuell",
        reverse_charge=False,
        marketing_allowed=True,
        e_invoice=True,
        priority="high",
    )

    assert captured == {
        "url": "https://cases.example.invalid/tenant-cases",
        "authorization": "Bearer token",
        "content_type": "application/json",
        "actor": "daskuechenhaus-owner-principal",
        "body": {
            "customer_type": "private",
            "salutation": "Frau",
            "first_name": "Maria",
            "last_name": "Hoffmann",
            "customer_phone": "0711 123456",
            "customer_mobile": "0171 123456",
            "customer_email": "maria@example.invalid",
            "country": "DE",
            "iso_country_code": "DE",
            "postal_code": "70173",
            "city": "Stuttgart",
            "is_nato": False,
            "has_custom_vat": True,
            "custom_vat_rate": "17.5",
            "custom_vat_rate_label": "Individuell",
            "reverse_charge": False,
            "marketing_allowed": True,
            "e_invoice": True,
            "priority": "high",
        },
        "timeout": 2.0,
    }
    assert payload["data"]["id"] == "case-001"


def test_business_ui_updates_customer_case_in_api(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"data":{"id":"case-001","phase":4}}'

    def fake_urlopen(request, timeout: float) -> FakeResponse:
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["authorization"] = request.headers["Authorization"]
        captured["actor"] = request.headers["X-actor"]
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(streamlit_business_ui_app.urlrequest, "urlopen", fake_urlopen)
    config = streamlit_business_ui_app.CustomerCasesApiConfig(
        base_url="https://cases.example.invalid",
        token="token",
        timeout_seconds=2.0,
    )

    payload = streamlit_business_ui_app.update_customer_case_in_api(
        config,
        actor="daskuechenhaus-owner-principal",
        case_id="case-001",
        case_number="VG-2026-0001",
        carat_order_number="CARAT-1",
        phase=4,
        priority="high",
        status="active",
        responsible_user_id="konstantin",
        needs_attention=True,
    )

    assert captured == {
        "url": "https://cases.example.invalid/tenant-cases/case-001",
        "method": "PATCH",
        "authorization": "Bearer token",
        "actor": "daskuechenhaus-owner-principal",
        "body": {
            "case_number": "VG-2026-0001",
            "carat_order_number": "CARAT-1",
            "phase": 4,
            "priority": "high",
            "status": "active",
            "responsible_user_id": "konstantin",
            "needs_attention": 1,
        },
        "timeout": 2.0,
    }
    assert payload["data"]["phase"] == 4


def test_business_ui_main_renders_customer_cases_route(
    monkeypatch,
) -> None:
    fake_st = FakeStreamlit()
    fake_st.query_params = {"route": "/customer-cases"}
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    monkeypatch.setenv("SCAS_UI_AUTH_MODE", "local-login")
    monkeypatch.setenv("SCAS_UI_TENANT_ID", "daskuechenhaus")
    monkeypatch.setenv("SCAS_CUSTOMER_CASES_API_URL", "https://cases.example.invalid")
    monkeypatch.setenv("SCAS_CUSTOMER_CASES_API_SECRET", "token")
    fake_st.session_state["scas_tenant_session"] = {
        "principal_id": "daskuechenhaus-owner-principal",
        "tenant_id": "daskuechenhaus",
        "membership_id": "tm-daskuechenhaus-owner-01",
        "role_ids": ["daskuechenhaus-owner"],
        "capabilities": ["research", "tenant-admin", "customer-cases"],
        "source": "local-login",
    }

    monkeypatch.setattr(
        streamlit_business_ui_app,
        "load_customer_cases_from_api",
        lambda _config: {
            "data": [
                {
                    "case_number": "VG-2026-0001",
                    "customer_number": "K-2026-0001",
                    "customer_full_name": "Maria Hoffmann",
                    "phase": 1,
                    "phase_label": "Neuer Kontakt",
                    "priority": "normal",
                    "status": "active",
                    "assigned_to": None,
                    "has_attention": 1,
                }
            ],
            "count": 1,
        },
    )

    streamlit_business_ui_app.main()

    assert ("subheader", "Kunden-Vorgänge") in fake_st.events
    assert ("caption", "Prozessübersicht") in fake_st.events
    assert [
        event
        for event in fake_st.events
        if event[0] == "button" and "Neuer Kontakt" in event[1]
    ]
    assert [event for event in fake_st.events if event[0] == "dataframe"]
