from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any
from urllib import request as urlrequest

REPO_ROOT = Path(__file__).resolve().parents[2]
TENANTS_DIR = REPO_ROOT / "examples" / "tenants"
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
LOGIN_CREDENTIAL_HASH_SCHEME = "pbkdf2_sha256"
LOGIN_CREDENTIAL_HASH_ITERATIONS = 600_000
MIN_LOGIN_CREDENTIAL_HASH_ITERATIONS = 100_000


@dataclass(frozen=True)
class TenantTheme:
    background: str
    surface: str
    text: str
    secondary_text: str
    accent: str
    border: str


DEFAULT_TENANT_THEME = TenantTheme(
    background="#f6f8fb",
    surface="#ffffff",
    text="#0b1b35",
    secondary_text="#415572",
    accent="#2f654d",
    border="#dbe4f0",
)


@dataclass(frozen=True)
class TenantShell:
    tenant_id: str
    area_id: str
    display_name: str
    legal_name: str
    status: str
    hostname: str
    logo_path: str | None
    admin_routes: tuple[str, ...]
    role_names: tuple[str, ...]
    data_sources: tuple[str, ...]
    isolation_summary: str


@dataclass(frozen=True)
class TenantBranding:
    display_name: str
    legal_name: str
    hostname: str
    logo_path: str | None
    landing_type: str
    area_presentation: str
    theme: TenantTheme


@dataclass(frozen=True)
class TenantAdminSection:
    users: tuple[dict[str, Any], ...]
    roles: tuple[dict[str, Any], ...]
    workflows: tuple[dict[str, Any], ...]
    settings: dict[str, Any]
    audit_summary: str


@dataclass(frozen=True)
class TenantAdminApiConfig:
    base_url: str
    token: str
    timeout_seconds: float = 8.0


@dataclass(frozen=True)
class TenantWorkspaceArea:
    area_id: str
    display_name: str
    description: str
    route: str
    required_capability: str
    admin_only: bool
    status: str


@dataclass(frozen=True)
class TenantNavigationItem:
    label: str
    route: str
    description: str
    required_capability: str | None
    admin_only: bool


@dataclass(frozen=True)
class TenantSession:
    principal_id: str
    tenant_id: str
    membership_id: str
    role_ids: tuple[str, ...]
    capabilities: frozenset[str]
    source: str


@dataclass(frozen=True)
class TenantLoginView:
    tenant_id: str
    display_name: str
    hostname: str
    login_url: str | None


@dataclass(frozen=True)
class LocalLoginUser:
    username: str
    tenant_id: str
    principal_id: str
    membership_id: str
    role_ids: tuple[str, ...]
    password_hash: str


class TenantSessionError(ValueError):
    """Raised when the UI cannot establish tenant session authority."""


def auth_mode_from_env() -> str:
    return os.environ.get("SCAS_UI_AUTH_MODE", "fixture").strip().lower()


def configured_tenant_id_from_env() -> str | None:
    configured = os.environ.get("SCAS_UI_TENANT_ID", "").strip()
    return configured or None


def login_url_from_env() -> str | None:
    configured = os.environ.get("SCAS_UI_LOGIN_URL", "").strip()
    return configured or None


def password_reset_url_from_env() -> str | None:
    configured = os.environ.get("SCAS_UI_PASSWORD_RESET_URL", "").strip()
    return configured or None


def resolve_runtime_tenant_id(tenants: dict[str, dict[str, Any]]) -> str | None:
    configured_tenant_id = configured_tenant_id_from_env()
    if configured_tenant_id:
        if configured_tenant_id not in tenants:
            raise TenantSessionError(
                f"Configured SCAS_UI_TENANT_ID is not available: {configured_tenant_id}"
            )
        return configured_tenant_id

    if auth_mode_from_env() in {"required", "local-login"}:
        raise TenantSessionError(
            "SCAS_UI_TENANT_ID is required in authenticated auth modes."
        )

    return None


def load_tenant_registry(tenants_dir: Path = TENANTS_DIR) -> dict[str, dict[str, Any]]:
    tenants: dict[str, dict[str, Any]] = {}
    for path in sorted(tenants_dir.glob("*.json")):
        tenant = json.loads(path.read_text(encoding="utf-8"))
        tenants[str(tenant["tenant_id"])] = tenant
    return tenants


def build_tenant_shell(tenant: dict[str, Any]) -> TenantShell:
    hostnames = tenant.get("hostnames", [])
    primary_hostname = hostnames[0]["hostname"] if hostnames else "unknown"
    admin_model = tenant.get("admin_model", {})
    role_bundles = tenant.get("role_bundles", [])
    data_sources = tenant.get("data_sources", [])
    ui_profile = tenant.get("ui_profile", {})
    return TenantShell(
        tenant_id=str(tenant["tenant_id"]),
        area_id=str(tenant["area_id"]),
        display_name=str(tenant["display_name"]),
        legal_name=str(tenant.get("legal_profile", {}).get("legal_name", tenant["display_name"])),
        status=str(tenant["status"]),
        hostname=str(primary_hostname),
        logo_path=(
            str(ui_profile["logo_path"])
            if isinstance(ui_profile, dict) and ui_profile.get("logo_path")
            else None
        ),
        admin_routes=tuple(str(route) for route in admin_model.get("admin_routes", [])),
        role_names=tuple(str(role["display_name"]) for role in role_bundles),
        data_sources=tuple(str(source["display_name"]) for source in data_sources),
        isolation_summary=(
            "Server-seitige Hostname-Autorität, Rollen statt Direktrechten, "
            "keine Cross-Tenant- oder Cross-Area-Freigaben."
        ),
    )


def build_tenant_branding(
    tenant: dict[str, Any],
    shell: TenantShell | None = None,
) -> TenantBranding:
    tenant_shell = shell if shell is not None else build_tenant_shell(tenant)
    ui_profile = tenant.get("ui_profile", {})
    landing = ui_profile.get("landing", {}) if isinstance(ui_profile, dict) else {}
    if not isinstance(landing, dict):
        landing = {}
    return TenantBranding(
        display_name=tenant_shell.display_name,
        legal_name=tenant_shell.legal_name,
        hostname=tenant_shell.hostname,
        logo_path=tenant_shell.logo_path,
        landing_type=str(landing.get("type", "tenant-operations-dashboard")),
        area_presentation=str(landing.get("area_presentation", "list")),
        theme=build_tenant_theme(ui_profile),
    )


def build_tenant_login_view(tenant: dict[str, Any]) -> TenantLoginView:
    shell = build_tenant_shell(tenant)
    return TenantLoginView(
        tenant_id=shell.tenant_id,
        display_name=shell.display_name,
        hostname=shell.hostname,
        login_url=login_url_from_env(),
    )


def theme_color(ui_theme: dict[str, Any], key: str, fallback: str) -> str:
    value = ui_theme.get(key)
    if isinstance(value, str) and HEX_COLOR_RE.fullmatch(value):
        return value.lower()
    return fallback


def build_tenant_theme(ui_profile: dict[str, Any]) -> TenantTheme:
    ui_theme = ui_profile.get("theme", {}) if isinstance(ui_profile, dict) else {}
    if not isinstance(ui_theme, dict):
        ui_theme = {}
    return TenantTheme(
        background=theme_color(ui_theme, "background", DEFAULT_TENANT_THEME.background),
        surface=theme_color(ui_theme, "surface", DEFAULT_TENANT_THEME.surface),
        text=theme_color(ui_theme, "text", DEFAULT_TENANT_THEME.text),
        secondary_text=theme_color(
            ui_theme,
            "secondary_text",
            DEFAULT_TENANT_THEME.secondary_text,
        ),
        accent=theme_color(ui_theme, "accent", DEFAULT_TENANT_THEME.accent),
        border=theme_color(ui_theme, "border", DEFAULT_TENANT_THEME.border),
    )


def render_tenant_theme_css(theme: TenantTheme) -> str:
    return f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap');
        :root {{
            --tenant-background: {theme.background};
            --tenant-surface: {theme.surface};
            --tenant-text: {theme.text};
            --tenant-secondary-text: {theme.secondary_text};
            --tenant-accent: {theme.accent};
            --tenant-border: {theme.border};
        }}
        .stApp {{
            background: var(--tenant-background);
            color: var(--tenant-text);
        }}
        h1, h2, h3, h4 {{
            color: var(--tenant-text);
            font-family: "Manrope", sans-serif;
            letter-spacing: 0;
        }}
        p, div, span, label {{ font-family: "Manrope", sans-serif; }}
        [data-testid="stSidebar"] {{
            background: var(--tenant-surface);
            border-right: 4px solid var(--tenant-accent);
        }}
        [data-testid="stSidebar"] * {{ color: var(--tenant-text) !important; }}
        [data-testid="stMainMenuButton"] {{
            color: var(--tenant-text) !important;
            background: var(--tenant-surface) !important;
            border: 1px solid var(--tenant-border) !important;
            border-radius: 8px !important;
        }}
        [data-testid="stMainMenuButton"]:hover {{
            color: var(--tenant-accent) !important;
        }}
        .area-tile {{
            min-height: 154px;
            border-radius: 8px;
            background: var(--tenant-surface);
            border: 1px solid var(--tenant-border);
            padding: 16px 18px;
        }}
        .area-title {{
            color: var(--tenant-text);
            font-size: 1.05rem;
            font-weight: 800;
            margin-bottom: 6px;
        }}
        .area-description {{
            color: var(--tenant-secondary-text);
            font-size: 0.9rem;
            min-height: 48px;
            margin-bottom: 12px;
        }}
        .area-meta {{
            color: var(--tenant-accent);
            font-size: 0.78rem;
            font-weight: 700;
        }}
        .tenant-subtitle {{
            color: var(--tenant-secondary-text);
            font-size: 0.95rem;
            margin-top: -8px;
        }}
        </style>
        """


def build_tenant_admin_section(tenant: dict[str, Any]) -> TenantAdminSection:
    admin_model = tenant.get("admin_model", {})
    admin_routes = tuple(str(route) for route in admin_model.get("admin_routes", []))
    role_bundles = tuple(
        {
            "role": str(role["display_name"]),
            "role_id": str(role["id"]),
            "type": str(role["role_type"]),
            "capabilities": ", ".join(str(item) for item in role.get("capability_grants", [])),
            "data_sources": ", ".join(
                str(grant["data_source_id"]) for grant in role.get("data_source_grants", [])
            ),
        }
        for role in tenant.get("role_bundles", [])
    )
    initial_owner = admin_model.get("initial_owner")
    users = (
        {
            "user": "Initial owner pending",
            "status": "pending",
            "roles": "Tenant Owner",
        },
    )
    if initial_owner is not None:
        users = (
            {
                "user": str(initial_owner["user_id"]),
                "status": "planned",
                "roles": "Tenant Owner",
            },
        )
    return TenantAdminSection(
        users=users,
        roles=role_bundles,
        workflows=tuple(
            {
                "workflow": route.removeprefix("/admin/").replace("-", " ").title(),
                "route": route,
                "authority": "tenant-admin",
                "mode": "read-only fixture",
            }
            for route in admin_routes
        ),
        settings={
            "assignment_model": str(admin_model.get("assignment_model", "")),
            "admin_routes": ", ".join(admin_routes),
            "shared_promotion_allowed": str(
                tenant.get("memory", {}).get("shared_promotion_allowed", False)
            ),
            "policy_bundle": ", ".join(str(policy) for policy in tenant.get("policy_bundle", [])),
        },
        audit_summary=(
            "Fixture mode is read-only. Tenant admin writes must go through the "
            "Control API audit event path."
        ),
    )


def default_role_ids(tenant: dict[str, Any]) -> tuple[str, ...]:
    role_bundles = tenant.get("role_bundles", [])
    non_admin_roles = tuple(
        str(role["id"])
        for role in role_bundles
        if "tenant-admin" not in role.get("capability_grants", [])
    )
    if non_admin_roles:
        return non_admin_roles
    return tuple(str(role["id"]) for role in role_bundles[:1])


def role_ids_from_env(tenant: dict[str, Any]) -> tuple[str, ...]:
    configured = os.environ.get("SCAS_UI_ROLE_IDS", "").strip()
    if not configured:
        return default_role_ids(tenant)
    available = {
        str(role["id"])
        for role in tenant.get("role_bundles", [])
        if isinstance(role, dict) and role.get("id")
    }
    requested = tuple(
        role_id.strip()
        for role_id in configured.split(",")
        if role_id.strip() in available
    )
    return requested or default_role_ids(tenant)


def granted_capabilities_for_roles(
    tenant: dict[str, Any],
    role_ids: Iterable[str],
) -> frozenset[str]:
    selected_role_ids = set(role_ids)
    capabilities: set[str] = set()
    for role in tenant.get("role_bundles", []):
        if str(role.get("id")) not in selected_role_ids:
            continue
        capabilities.update(str(item) for item in role.get("capability_grants", []))
    return frozenset(capabilities)


def build_fixture_session(tenant: dict[str, Any]) -> TenantSession:
    role_ids = role_ids_from_env(tenant)
    return TenantSession(
        principal_id="local-fixture-user",
        tenant_id=str(tenant["tenant_id"]),
        membership_id="local-fixture-membership",
        role_ids=role_ids,
        capabilities=granted_capabilities_for_roles(tenant, role_ids),
        source="local-fixture",
    )


def build_session_from_context(
    tenant: dict[str, Any],
    context: dict[str, Any],
    *,
    source: str,
) -> TenantSession:
    tenant_id = str(context.get("tenant_id", ""))
    if tenant_id != str(tenant["tenant_id"]):
        raise TenantSessionError("Session tenant does not match the selected tenant.")
    principal_id = str(context.get("principal_id", "")).strip()
    membership_id = str(context.get("membership_id", "")).strip()
    if not principal_id or not membership_id:
        raise TenantSessionError("Session principal_id and membership_id are required.")

    available_roles = {
        str(role["id"])
        for role in tenant.get("role_bundles", [])
        if isinstance(role, dict) and role.get("id")
    }
    role_ids = tuple(str(role_id) for role_id in context.get("role_ids", []))
    if not role_ids:
        raise TenantSessionError("Session role_ids are required.")
    unknown_roles = sorted(set(role_ids) - available_roles)
    if unknown_roles:
        raise TenantSessionError(
            "Session references unknown tenant roles: " + ", ".join(unknown_roles)
        )

    return TenantSession(
        principal_id=principal_id,
        tenant_id=tenant_id,
        membership_id=membership_id,
        role_ids=role_ids,
        capabilities=granted_capabilities_for_roles(tenant, role_ids),
        source=source,
    )


def authenticated_session_from_env(tenant: dict[str, Any]) -> TenantSession:
    mode = auth_mode_from_env()
    if mode in {"", "fixture", "local"}:
        return build_fixture_session(tenant)
    if mode != "required":
        raise TenantSessionError(f"Unsupported SCAS_UI_AUTH_MODE: {mode}")

    raw_context = os.environ.get("SCAS_UI_SESSION_CONTEXT_JSON", "").strip()
    if not raw_context:
        raise TenantSessionError("SCAS_UI_SESSION_CONTEXT_JSON is required.")
    try:
        context = json.loads(raw_context)
    except json.JSONDecodeError as error:
        raise TenantSessionError("SCAS_UI_SESSION_CONTEXT_JSON is invalid JSON.") from error
    if not isinstance(context, dict):
        raise TenantSessionError("SCAS_UI_SESSION_CONTEXT_JSON must be an object.")

    trusted_upstream = (
        os.environ.get("SCAS_UI_UPSTREAM_AUTH_TRUSTED", "").strip().lower()
        in {"1", "true", "yes"}
    )
    if not trusted_upstream:
        raise TenantSessionError("Trusted upstream authentication is required.")

    return build_session_from_context(tenant, context, source="trusted-upstream")


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + padding)


def encode_login_password_hash(
    password: str,
    *,
    salt: bytes | None = None,
    iterations: int = LOGIN_CREDENTIAL_HASH_ITERATIONS,
) -> str:
    if iterations < MIN_LOGIN_CREDENTIAL_HASH_ITERATIONS:
        raise ValueError("login password hash iterations are too low")
    password_salt = salt if salt is not None else os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        password_salt,
        iterations,
    )
    return "$".join(
        (
            LOGIN_CREDENTIAL_HASH_SCHEME,
            str(iterations),
            _base64url_encode(password_salt),
            _base64url_encode(digest),
        )
    )


def verify_login_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt_raw, digest_raw = encoded_hash.split("$")
        iterations = int(iterations_raw)
        salt = _base64url_decode(salt_raw)
        expected_digest = _base64url_decode(digest_raw)
    except (ValueError, binascii.Error):
        return False
    if algorithm != LOGIN_CREDENTIAL_HASH_SCHEME:
        return False
    if iterations < MIN_LOGIN_CREDENTIAL_HASH_ITERATIONS:
        return False
    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def local_login_users_from_env() -> tuple[LocalLoginUser, ...]:
    raw_users = os.environ.get("SCAS_UI_LOGIN_USERS_JSON", "").strip()
    if not raw_users:
        raise TenantSessionError("SCAS_UI_LOGIN_USERS_JSON is required for local-login mode.")
    try:
        users = json.loads(raw_users)
    except json.JSONDecodeError as error:
        raise TenantSessionError("SCAS_UI_LOGIN_USERS_JSON is invalid JSON.") from error
    if not isinstance(users, list):
        raise TenantSessionError("SCAS_UI_LOGIN_USERS_JSON must be an array.")

    parsed_users: list[LocalLoginUser] = []
    for user in users:
        if not isinstance(user, dict):
            raise TenantSessionError("SCAS_UI_LOGIN_USERS_JSON entries must be objects.")
        username = str(user.get("username", "")).strip()
        tenant_id = str(user.get("tenant_id", "")).strip()
        principal_id = str(user.get("principal_id", "")).strip()
        membership_id = str(user.get("membership_id", "")).strip()
        password_hash = str(user.get("password_hash", "")).strip()
        role_ids = tuple(str(role_id) for role_id in user.get("role_ids", []))
        if not all((username, tenant_id, principal_id, membership_id, password_hash)):
            raise TenantSessionError("Local login users require username and session fields.")
        if not role_ids:
            raise TenantSessionError("Local login users require role_ids.")
        parsed_users.append(
            LocalLoginUser(
                username=username,
                tenant_id=tenant_id,
                principal_id=principal_id,
                membership_id=membership_id,
                role_ids=role_ids,
                password_hash=password_hash,
            )
        )
    return tuple(parsed_users)


def local_login_session_from_credentials(
    tenant: dict[str, Any],
    username: str,
    password: str,
) -> TenantSession:
    normalized_username = username.strip()
    matching_user = next(
        (
            user
            for user in local_login_users_from_env()
            if user.username == normalized_username and user.tenant_id == str(tenant["tenant_id"])
        ),
        None,
    )
    if matching_user is None or not verify_login_password(password, matching_user.password_hash):
        raise TenantSessionError("Invalid username or password.")

    return build_session_from_context(
        tenant,
        {
            "tenant_id": matching_user.tenant_id,
            "principal_id": matching_user.principal_id,
            "membership_id": matching_user.membership_id,
            "role_ids": list(matching_user.role_ids),
        },
        source="local-login",
    )


def _session_to_state(session: TenantSession) -> dict[str, Any]:
    return {
        "principal_id": session.principal_id,
        "tenant_id": session.tenant_id,
        "membership_id": session.membership_id,
        "role_ids": list(session.role_ids),
        "capabilities": sorted(session.capabilities),
        "source": session.source,
    }


def _session_from_state(state: dict[str, Any]) -> TenantSession:
    return TenantSession(
        principal_id=str(state["principal_id"]),
        tenant_id=str(state["tenant_id"]),
        membership_id=str(state["membership_id"]),
        role_ids=tuple(str(role_id) for role_id in state.get("role_ids", [])),
        capabilities=frozenset(str(item) for item in state.get("capabilities", [])),
        source=str(state["source"]),
    )


def render_login_area(st: Any, tenant: dict[str, Any]) -> None:
    login_view = build_tenant_login_view(tenant)
    st.markdown(f"### Login {login_view.display_name}")
    st.caption(login_view.hostname)
    st.info(
        "Bitte ueber den freigegebenen Identitaetsdienst anmelden. "
        "Danach laedt die UI die serverseitig gepruefte Tenant-Session."
    )
    if login_view.login_url:
        if hasattr(st, "link_button"):
            st.link_button("Einloggen", login_view.login_url)
        else:  # pragma: no cover - compatibility for older Streamlit runtimes.
            st.markdown(f"[Einloggen]({login_view.login_url})")
    else:
        st.error("Tenant-Session nicht verfuegbar: trusted upstream authentication is required.")


def render_local_login_area(st: Any, tenant: dict[str, Any]) -> TenantSession | None:
    login_view = build_tenant_login_view(tenant)
    st.markdown(f"### Login {login_view.display_name}")
    st.caption(login_view.hostname)
    st.info("Bitte mit Ihrem Benutzernamen anmelden")
    with st.form("scas-local-login"):
        username = st.text_input("Benutzername")
        password = st.text_input("Passwort", type="password")
        submitted = st.form_submit_button("Einloggen")
    reset_url = password_reset_url_from_env()
    if reset_url:
        if hasattr(st, "link_button"):
            st.link_button("Passwort vergessen?", reset_url)
        else:  # pragma: no cover - compatibility for older Streamlit runtimes.
            st.markdown(f"[Passwort vergessen?]({reset_url})")
    else:
        with st.expander("Passwort vergessen?"):
            st.info(
                "Bitte wenden Sie sich an Ihren Administrator. "
                "Ein automatischer Passwort-Reset ist noch nicht eingerichtet."
            )
    if not submitted:
        return None
    try:
        return local_login_session_from_credentials(tenant, username, password)
    except TenantSessionError:
        st.error("Login fehlgeschlagen.")
        return None


def render_session_gate(st: Any, tenant: dict[str, Any]) -> TenantSession:
    mode = auth_mode_from_env()
    if mode in {"", "fixture", "local"}:
        return build_fixture_session(tenant)

    stored = st.session_state.get("scas_tenant_session")
    if isinstance(stored, dict) and stored.get("tenant_id") == tenant.get("tenant_id"):
        return _session_from_state(stored)

    if mode == "local-login":
        session = render_local_login_area(st, tenant)
        if session is not None:
            st.session_state["scas_tenant_session"] = _session_to_state(session)
            if hasattr(st, "rerun"):
                st.rerun()
                st.stop()
            return session
        st.stop()
        raise RuntimeError("streamlit stop did not halt execution")

    if mode != "required":
        st.error(f"Tenant-Session nicht verfuegbar: unsupported auth mode {mode}.")
        st.stop()
        raise RuntimeError("streamlit stop did not halt execution")

    trusted_upstream = (
        os.environ.get("SCAS_UI_UPSTREAM_AUTH_TRUSTED", "").strip().lower()
        in {"1", "true", "yes"}
    )
    if trusted_upstream:
        try:
            session = authenticated_session_from_env(tenant)
        except TenantSessionError as error:
            st.error(f"Tenant-Session nicht verfuegbar: {error}")
            st.stop()
        st.session_state["scas_tenant_session"] = _session_to_state(session)
        return session

    if login_url_from_env():
        render_login_area(st, tenant)
    else:
        st.error("Tenant-Session nicht verfuegbar: trusted upstream authentication is required.")
    st.stop()
    raise RuntimeError("streamlit stop did not halt execution")


def build_workspace_areas(
    tenant: dict[str, Any],
    role_ids: Iterable[str],
) -> tuple[TenantWorkspaceArea, ...]:
    ui_profile = tenant.get("ui_profile", {})
    configured_areas = (
        ui_profile.get("workspace_areas", [])
        if isinstance(ui_profile, dict)
        else []
    )
    granted_capabilities = granted_capabilities_for_roles(tenant, role_ids)
    visible_areas: list[TenantWorkspaceArea] = []
    for area in configured_areas:
        if not isinstance(area, dict) or area.get("status") != "active":
            continue
        required_capability = str(area["required_capability"])
        if required_capability not in granted_capabilities:
            continue
        if area.get("admin_only") is True and "tenant-admin" not in granted_capabilities:
            continue
        visible_areas.append(
            TenantWorkspaceArea(
                area_id=str(area["id"]),
                display_name=str(area["display_name"]),
                description=str(area["description"]),
                route=str(area["route"]),
                required_capability=required_capability,
                admin_only=bool(area["admin_only"]),
                status=str(area["status"]),
            )
        )
    return tuple(visible_areas)


def build_tenant_navigation_items(
    workspace_areas: Iterable[TenantWorkspaceArea],
) -> tuple[TenantNavigationItem, ...]:
    navigation_items = [
        TenantNavigationItem(
            label="Übersicht",
            route="/",
            description="Tenant landing dashboard",
            required_capability=None,
            admin_only=False,
        )
    ]
    navigation_items.extend(
        TenantNavigationItem(
            label=area.display_name,
            route=area.route,
            description=area.description,
            required_capability=area.required_capability,
            admin_only=area.admin_only,
        )
        for area in workspace_areas
    )
    return tuple(navigation_items)


def tenant_admin_api_config_from_env() -> TenantAdminApiConfig | None:
    base_url = os.environ.get("SCAS_CONTROL_API_URL", "").strip()
    token = os.environ.get("SCAS_TENANT_ADMIN_TOKEN", "").strip()
    if not base_url or not token:
        return None
    return TenantAdminApiConfig(base_url=base_url.rstrip("/"), token=token)


def load_tenant_admin_context_from_api(
    config: TenantAdminApiConfig,
    tenant_id: str,
    hostname: str,
) -> dict[str, Any]:
    api_request = urlrequest.Request(
        f"{config.base_url}/tenant-admin/tenants/{tenant_id}",
        headers={
            "authorization": f"Bearer {config.token}",
            "x-scas-tenant-hostname": hostname,
            "accept": "application/json",
            "user-agent": "scas-streamlit-business-ui/1.0",
        },
        method="GET",
    )
    with urlrequest.urlopen(api_request, timeout=config.timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def build_tenant_shell_from_admin_context(context: dict[str, Any]) -> TenantShell:
    tenant = context["tenant"]
    admin = context["admin"]
    return TenantShell(
        tenant_id=str(tenant["tenant_id"]),
        area_id=str(tenant["area_id"]),
        display_name=str(tenant["display_name"]),
        legal_name=str(tenant.get("legal_name", tenant["display_name"])),
        status=str(tenant["status"]),
        hostname=str(tenant["hostname"]["hostname"]),
        logo_path=str(tenant["logo_path"]) if tenant.get("logo_path") else None,
        admin_routes=tuple(str(route) for route in admin.get("admin_routes", [])),
        role_names=tuple(str(role["display_name"]) for role in context.get("roles", [])),
        data_sources=tuple(
            str(source["display_name"]) for source in context.get("data_sources", [])
        ),
        isolation_summary=(
            "Backend-geprüfte Hostname-Autorität, Rollen statt Direktrechten, "
            "keine Cross-Tenant- oder Cross-Area-Freigaben."
        ),
    )


def build_tenant_admin_section_from_context(context: dict[str, Any]) -> TenantAdminSection:
    admin = context.get("admin", {})
    admin_routes = tuple(str(route) for route in admin.get("admin_routes", []))
    audit_events = context.get("audit_events", [])
    users = tuple(
        {
            "user": str(user["principal_id"]),
            "membership_id": str(user["membership_id"]),
            "status": str(user["status"]),
            "roles": ", ".join(str(role_id) for role_id in user.get("role_ids", [])),
        }
        for user in context.get("users", [])
    )
    roles = tuple(
        {
            "role": str(role["display_name"]),
            "role_id": str(role["id"]),
            "type": str(role["role_type"]),
            "capabilities": ", ".join(str(item) for item in role.get("capability_grants", [])),
            "data_sources": ", ".join(
                str(grant["data_source_id"]) for grant in role.get("data_source_grants", [])
            ),
        }
        for role in context.get("roles", [])
    )
    return TenantAdminSection(
        users=users,
        roles=roles,
        workflows=tuple(
            {
                "workflow": route.removeprefix("/admin/").replace("-", " ").title(),
                "route": route,
                "authority": "tenant-admin",
                "mode": "Control API",
            }
            for route in admin_routes
        ),
        settings=dict(context.get("settings", {})),
        audit_summary=(
            f"{len(audit_events)} audit event(s) returned by the tenant admin context."
            if isinstance(audit_events, list) and audit_events
            else "Tenant admin write actions are traceable through Control API audit events."
        ),
    )


def main() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="SCAS Tenant Operations",
        page_icon=":material/monitoring:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    tenants = load_tenant_registry()

    try:
        runtime_tenant_id = resolve_runtime_tenant_id(tenants)
    except TenantSessionError as error:
        st.error(f"Tenant-Konfiguration nicht verfuegbar: {error}")
        st.stop()
        raise RuntimeError("streamlit stop did not halt execution") from error

    if runtime_tenant_id is None:
        st.sidebar.title("Steuerung")
        tenant_id = st.sidebar.selectbox(
            "Tenant",
            options=sorted(tenants),
            index=sorted(tenants).index("liquisto") if "liquisto" in tenants else 0,
        )
    else:
        tenant_id = runtime_tenant_id

    selected_tenant = tenants[tenant_id]
    tenant_session = render_session_gate(st, selected_tenant)
    if runtime_tenant_id is not None:
        st.sidebar.title("Steuerung")
    selected_role_ids = tenant_session.role_ids
    if tenant_session.source != "local-fixture" and st.sidebar.button("Logout"):
        st.session_state.pop("scas_tenant_session", None)
        st.rerun()

    tenant_shell = build_tenant_shell(tenants[tenant_id])
    workspace_areas = build_workspace_areas(selected_tenant, selected_role_ids)
    api_config = tenant_admin_api_config_from_env()
    if api_config is not None:
        try:
            admin_context = load_tenant_admin_context_from_api(
                api_config,
                tenant_shell.tenant_id,
                tenant_shell.hostname,
            )
            tenant_shell = build_tenant_shell_from_admin_context(admin_context)
        except Exception:  # pragma: no cover - defensive Streamlit runtime fallback.
            # The backend context is optional for this landing page; do not expose
            # internal Control API failures on the user-facing tenant UI.
            pass

    branding = build_tenant_branding(selected_tenant, tenant_shell)
    st.markdown(render_tenant_theme_css(branding.theme), unsafe_allow_html=True)
    navigation_items = build_tenant_navigation_items(workspace_areas)

    st.sidebar.caption("Navigation")
    for item in navigation_items:
        st.sidebar.markdown(
            f"[{escape(item.label)}]({escape(item.route)})",
            unsafe_allow_html=True,
        )

    if branding.logo_path:
        logo_path = REPO_ROOT / branding.logo_path
        if logo_path.exists():
            st.image(str(logo_path), width=160)

    st.title(branding.display_name)
    st.markdown(
        f"<div class='tenant-subtitle'>{escape(branding.legal_name)}</div>",
        unsafe_allow_html=True,
    )

    st.divider()
    st.subheader("Freigeschaltete Bereiche")
    if not workspace_areas:
        st.error("Keine Bereiche für die aktuelle Tenant-Rolle freigeschaltet.")
    else:
        area_columns = st.columns(min(3, len(workspace_areas)))
        for index, area in enumerate(workspace_areas):
            with area_columns[index % len(area_columns)]:
                st.markdown(
                    f"""
                    <div class="area-tile">
                        <div class="area-title">{escape(area.display_name)}</div>
                        <div class="area-meta">Freigeschaltet</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


if __name__ == "__main__":
    main()
