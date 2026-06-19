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
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parents[2]
TENANTS_DIR = REPO_ROOT / "examples" / "tenants"
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
LOGIN_CREDENTIAL_HASH_SCHEME = "pbkdf2_sha256"
LOGIN_CREDENTIAL_HASH_ITERATIONS = 600_000
MIN_LOGIN_CREDENTIAL_HASH_ITERATIONS = 100_000
CUSTOMER_CASE_PHASES = (
    (1, "Neuer Kontakt"),
    (2, "Erstberatung geplant"),
    (3, "Beratung abgeschlossen"),
    (4, "Aufmaß / Planung"),
    (5, "Angebot erstellt"),
    (6, "Auftrag erteilt"),
    (7, "Bestellung / Produktion"),
    (8, "Lieferung / Montage"),
    (9, "Abnahme / Rechnung"),
    (10, "Aftersales / Abgeschlossen"),
)
CUSTOMER_CASE_PRIORITY_LABELS = {
    "normal": "Normal",
    "high": "Hoch",
    "urgent": "Dringend",
    "low": "Niedrig",
}


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
class CustomerCasesApiConfig:
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
        button[data-testid="stMainMenuButton"],
        [data-testid="stToolbar"] button[kind="headerNoPadding"],
        [data-testid="stHeader"] button[kind="headerNoPadding"] {{
            color: var(--tenant-text) !important;
            background: var(--tenant-surface) !important;
            border: 1px solid var(--tenant-border) !important;
            border-radius: 8px !important;
        }}
        button[data-testid="stMainMenuButton"] svg,
        [data-testid="stToolbar"] button[kind="headerNoPadding"] svg,
        [data-testid="stHeader"] button[kind="headerNoPadding"] svg {{
            color: var(--tenant-text) !important;
            fill: var(--tenant-text) !important;
        }}
        button[data-testid="stMainMenuButton"]:hover,
        [data-testid="stToolbar"] button[kind="headerNoPadding"]:hover,
        [data-testid="stHeader"] button[kind="headerNoPadding"]:hover {{
            color: var(--tenant-accent) !important;
        }}
        button[data-testid="stMainMenuButton"]:hover svg,
        [data-testid="stToolbar"] button[kind="headerNoPadding"]:hover svg,
        [data-testid="stHeader"] button[kind="headerNoPadding"]:hover svg {{
            color: var(--tenant-accent) !important;
            fill: var(--tenant-accent) !important;
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
        .case-pill {{
            display: inline-block;
            border: 1px solid var(--tenant-border);
            border-radius: 999px;
            color: var(--tenant-text);
            padding: 3px 10px;
            font-size: 0.78rem;
            font-weight: 700;
            margin-right: 6px;
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


def navigation_href(route: str) -> str:
    return f"?route={quote(route, safe='')}"


def current_route_from_query_params(st: Any) -> str:
    query_params = getattr(st, "query_params", None)
    if query_params is None:
        return "/"
    raw_route = query_params.get("route", "/")
    if isinstance(raw_route, list):
        raw_route = raw_route[0] if raw_route else "/"
    route = str(raw_route).strip()
    if not route.startswith("/"):
        return "/"
    return route


def tenant_admin_api_config_from_env() -> TenantAdminApiConfig | None:
    base_url = os.environ.get("SCAS_CONTROL_API_URL", "").strip()
    token = os.environ.get("SCAS_TENANT_ADMIN_TOKEN", "").strip()
    if not base_url or not token:
        return None
    return TenantAdminApiConfig(base_url=base_url.rstrip("/"), token=token)


def customer_cases_api_config_from_env() -> CustomerCasesApiConfig | None:
    base_url = os.environ.get("SCAS_CUSTOMER_CASES_API_URL", "").strip()
    token = os.environ.get("SCAS_CUSTOMER_CASES_API_SECRET", "").strip()
    if not base_url or not token:
        return None
    return CustomerCasesApiConfig(base_url=base_url.rstrip("/"), token=token)


def load_customer_cases_from_api(config: CustomerCasesApiConfig) -> dict[str, Any]:
    api_request = urlrequest.Request(
        f"{config.base_url}/tenant-cases",
        headers={
            "authorization": f"Bearer {config.token}",
            "accept": "application/json",
            "user-agent": "scas-streamlit-business-ui/1.0",
        },
        method="GET",
    )
    with urlrequest.urlopen(api_request, timeout=config.timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def create_customer_case_in_api(
    config: CustomerCasesApiConfig,
    *,
    actor: str,
    carat_order_number: str,
    customer_type: str,
    salutation: str,
    first_name: str,
    last_name: str,
    company_name: str,
    company_name_2: str,
    company_name_3: str,
    company_name_4: str,
    vat_id: str,
    tax_number: str,
    customer_phone: str,
    customer_mobile: str,
    customer_email: str,
    iso_country_code: str,
    postal_code: str,
    city: str,
    is_nato: bool,
    has_custom_vat: bool,
    custom_vat_rate: str,
    custom_vat_rate_label: str,
    reverse_charge: bool,
    marketing_allowed: bool,
    e_invoice: bool,
    priority: str,
) -> dict[str, Any]:
    raw_payload = {
        "carat_order_number": carat_order_number,
        "customer_type": customer_type,
        "salutation": salutation,
        "first_name": first_name,
        "last_name": last_name,
        "company_name": company_name,
        "company_name_2": company_name_2,
        "company_name_3": company_name_3,
        "company_name_4": company_name_4,
        "vat_id": vat_id,
        "tax_number": tax_number,
        "customer_phone": customer_phone,
        "customer_mobile": customer_mobile,
        "customer_email": customer_email,
        "country": iso_country_code,
        "iso_country_code": iso_country_code,
        "postal_code": postal_code,
        "city": city,
        "is_nato": is_nato,
        "has_custom_vat": has_custom_vat,
        "custom_vat_rate": custom_vat_rate,
        "custom_vat_rate_label": custom_vat_rate_label,
        "reverse_charge": reverse_charge,
        "marketing_allowed": marketing_allowed,
        "e_invoice": e_invoice,
        "priority": priority,
    }
    payload = json.dumps(
        {key: value for key, value in raw_payload.items() if str(value).strip()}
    ).encode("utf-8")
    api_request = urlrequest.Request(
        f"{config.base_url}/tenant-cases",
        data=payload,
        headers={
            "authorization": f"Bearer {config.token}",
            "content-type": "application/json",
            "accept": "application/json",
            "x-actor": actor,
            "user-agent": "scas-streamlit-business-ui/1.0",
        },
        method="POST",
    )
    with urlrequest.urlopen(api_request, timeout=config.timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def update_customer_case_in_api(
    config: CustomerCasesApiConfig,
    *,
    actor: str,
    case_id: str,
    case_number: str,
    carat_order_number: str,
    phase: int,
    priority: str,
    status: str,
    responsible_user_id: str,
    needs_attention: bool,
) -> dict[str, Any]:
    raw_payload = {
        "case_number": case_number,
        "carat_order_number": carat_order_number,
        "phase": phase,
        "priority": priority,
        "status": status,
        "responsible_user_id": responsible_user_id,
        "needs_attention": 1 if needs_attention else 0,
    }
    payload = json.dumps(
        {key: value for key, value in raw_payload.items() if str(value).strip()}
    ).encode("utf-8")
    api_request = urlrequest.Request(
        f"{config.base_url}/tenant-cases/{quote(case_id, safe='')}",
        data=payload,
        headers={
            "authorization": f"Bearer {config.token}",
            "content-type": "application/json",
            "accept": "application/json",
            "x-actor": actor,
            "user-agent": "scas-streamlit-business-ui/1.0",
        },
        method="PATCH",
    )
    with urlrequest.urlopen(api_request, timeout=config.timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def customer_case_phase_number(case: dict[str, Any]) -> int:
    raw_phase = case.get("phase")
    try:
        phase = int(raw_phase)
    except (TypeError, ValueError):
        return 1
    return phase if 1 <= phase <= 10 else 1


def customer_case_needs_attention(case: dict[str, Any]) -> bool:
    return bool(case.get("has_attention") or case.get("needs_attention"))


def render_customer_case_phase_tiles(st: Any, cases: list[dict[str, Any]]) -> int:
    selected_phase = int(st.session_state.get("scas_customer_cases_phase", 1))
    counts = {phase: 0 for phase, _label in CUSTOMER_CASE_PHASES}
    attention = {phase: False for phase, _label in CUSTOMER_CASE_PHASES}

    for case in cases:
        phase = customer_case_phase_number(case)
        counts[phase] += 1
        attention[phase] = attention[phase] or customer_case_needs_attention(case)

    st.markdown(
        """
        <style>
        div[data-testid="stButton"] button {
            min-height: 118px;
            height: 118px;
            width: 100%;
            border-radius: 8px;
            border: 1px solid rgba(118, 183, 38, 0.38);
            background: linear-gradient(135deg, #ffffff 0%, #f6faf1 100%);
            color: #111111;
            white-space: pre-line;
            text-align: left;
            font-weight: 650;
            box-shadow: 0 8px 22px rgba(17, 17, 17, 0.08);
            transition: border-color 120ms ease, box-shadow 120ms ease, transform 120ms ease;
        }
        div[data-testid="stButton"] button:hover {
            border-color: #76b726;
            color: #111111;
            box-shadow: 0 10px 26px rgba(118, 183, 38, 0.18);
            transform: translateY(-1px);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    for start in (0, 5):
        cols = st.columns(5)
        for offset, (phase, label) in enumerate(CUSTOMER_CASE_PHASES[start : start + 5]):
            suffix = "  ⚠" if attention[phase] else ""
            count_label = "1 Vorgang" if counts[phase] == 1 else f"{counts[phase]} Vorgänge"
            button_label = f"Phase {phase}\n{label}\n{count_label}{suffix}"
            with cols[offset]:
                if st.button(button_label, key=f"customer-case-phase-{phase}"):
                    selected_phase = phase
                    st.session_state["scas_customer_cases_phase"] = phase

    return selected_phase


def render_dialog(st: Any, title: str, render_content: Any) -> None:
    dialog = getattr(st, "dialog", None)
    if callable(dialog):
        try:
            decorator = dialog(title, width="large")
        except TypeError:  # pragma: no cover - older Streamlit runtimes.
            decorator = dialog(title)

        @decorator
        def _dialog() -> None:
            render_content()

        _dialog()
        return

    render_content()


def render_customer_case_create_form(
    st: Any,
    config: CustomerCasesApiConfig,
    session: TenantSession,
) -> None:
    st.caption("Kunden-Nr. und Vorgangs-Nr. werden automatisch vergeben.")
    with st.form("scas-customer-case-create"):
        customer_type_label = st.selectbox(
            "Kundentyp",
            options=["Privatkunde", "Firmenkunde"],
            index=0,
        )
        customer_type = "company" if customer_type_label == "Firmenkunde" else "private"

        salutation = ""
        first_name = ""
        last_name = ""
        company_name = ""
        company_name_2 = ""
        company_name_3 = ""
        company_name_4 = ""
        vat_id = ""
        tax_number = ""
        if customer_type == "company":
            st.markdown("**Firmenkunde**")
            company_name = st.text_input("Firma")
            company_name_2 = st.text_input("Name 2")
            company_name_3 = st.text_input("Name 3")
            company_name_4 = st.text_input("Name 4")
            vat_id = st.text_input("USt-ID")
            tax_number = st.text_input("Steuernummer")
        else:
            st.markdown("**Privatkunde**")
            salutation = st.selectbox(
                "Anrede",
                options=["", "Frau", "Herr", "Familie"],
                index=0,
            )
            last_name = st.text_input("Nachname")
            first_name = st.text_input("Vorname")

        customer_phone = st.text_input("Telefon")
        customer_mobile = st.text_input("Mobil")
        customer_email = st.text_input("E-Mail")
        iso_country_code = st.text_input("ISO Länder Code")
        postal_code = st.text_input("PLZ")
        city = st.text_input("Ort")
        carat_order_number = st.text_input("CARAT-Auftrags-Nr.")
        priority_label = st.selectbox(
            "Priorität",
            options=["Normal", "Hoch", "Dringend", "Niedrig"],
            index=0,
        )

        st.markdown("**Steuerung**")
        is_nato = st.checkbox("NATO")
        has_custom_vat = st.checkbox("Abweichende MwSt.")
        custom_vat_rate_label = st.selectbox(
            "MwSt. Auswahl",
            options=["", "0 %", "7 %", "19 %", "Individuell"],
            index=0,
        )
        custom_vat_rate = st.text_input("Abweichende MwSt. Eingabe")
        reverse_charge = st.checkbox("Umkehr der Steuerschuldnerschaft")
        marketing_allowed = st.checkbox("Werbezusendung erlaubt")
        e_invoice = st.checkbox("E-Rechnung")
        submitted = st.form_submit_button("Vorgang anlegen")

    priority_by_label = {
        "Normal": "normal",
        "Hoch": "high",
        "Dringend": "urgent",
        "Niedrig": "low",
    }

    if not submitted:
        return

    required_name = company_name if customer_type == "company" else last_name
    if not required_name.strip():
        st.error("Bitte mindestens Firma oder Nachname eingeben.")
        return

    try:
        create_customer_case_in_api(
            config,
            actor=session.principal_id,
            carat_order_number=carat_order_number,
            customer_type=customer_type,
            salutation=salutation,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name,
            company_name_2=company_name_2,
            company_name_3=company_name_3,
            company_name_4=company_name_4,
            vat_id=vat_id,
            tax_number=tax_number,
            customer_phone=customer_phone,
            customer_mobile=customer_mobile,
            customer_email=customer_email,
            iso_country_code=iso_country_code,
            postal_code=postal_code,
            city=city,
            is_nato=is_nato,
            has_custom_vat=has_custom_vat,
            custom_vat_rate=custom_vat_rate,
            custom_vat_rate_label=custom_vat_rate_label,
            reverse_charge=reverse_charge,
            marketing_allowed=marketing_allowed,
            e_invoice=e_invoice,
            priority=priority_by_label[priority_label],
        )
    except Exception:
        st.error("Vorgang konnte nicht angelegt werden.")
    else:
        st.success("Vorgang angelegt.")
        if hasattr(st, "rerun"):
            st.rerun()


def render_customer_case_edit_form(
    st: Any,
    config: CustomerCasesApiConfig,
    session: TenantSession,
    case: dict[str, Any],
) -> None:
    case_id = str(case.get("id", ""))
    with st.form(f"scas-customer-case-edit-{case_id}"):
        st.caption(f"Kunden-Nr.: {case.get('customer_number') or 'automatisch'}")
        case_number = st.text_input(
            "Vorgangs-Nr.",
            value=str(case.get("case_number", "")),
        )
        carat_order_number = st.text_input(
            "CARAT-Auftrags-Nr.",
            value=str(case.get("carat_order_number") or ""),
        )
        phase_options = [label for _phase, label in CUSTOMER_CASE_PHASES]
        current_phase = customer_case_phase_number(case)
        phase_label = st.selectbox(
            "Prozessphase",
            options=phase_options,
            index=max(current_phase - 1, 0),
        )
        priority_options = ["Normal", "Hoch", "Dringend", "Niedrig"]
        priority_by_label = {
            "Normal": "normal",
            "Hoch": "high",
            "Dringend": "urgent",
            "Niedrig": "low",
        }
        current_priority = str(case.get("priority", "normal"))
        current_priority_label = next(
            (
                label
                for label, value in priority_by_label.items()
                if value == current_priority
            ),
            "Normal",
        )
        priority_label = st.selectbox(
            "Priorität",
            options=priority_options,
            index=priority_options.index(current_priority_label),
        )
        status_options = ["active", "paused", "won", "lost", "closed"]
        current_status = str(case.get("status", "active"))
        status = st.selectbox(
            "Status",
            options=status_options,
            index=status_options.index(current_status)
            if current_status in status_options
            else 0,
        )
        responsible_user_id = st.text_input(
            "Verantwortlich",
            value=str(case.get("responsible_user_id") or case.get("assigned_to") or ""),
        )
        needs_attention = st.checkbox(
            "Handlungsbedarf",
            value=customer_case_needs_attention(case),
        )
        submitted = st.form_submit_button("Änderungen speichern")

    if not submitted:
        return

    try:
        update_customer_case_in_api(
            config,
            actor=session.principal_id,
            case_id=case_id,
            case_number=case_number,
            carat_order_number=carat_order_number,
            phase=phase_options.index(phase_label) + 1,
            priority=priority_by_label[priority_label],
            status=status,
            responsible_user_id=responsible_user_id,
            needs_attention=needs_attention,
        )
    except Exception:
        st.error("Vorgang konnte nicht aktualisiert werden.")
    else:
        st.success("Vorgang aktualisiert.")
        if hasattr(st, "rerun"):
            st.rerun()


def render_customer_cases_area(
    st: Any,
    session: TenantSession,
) -> None:
    st.subheader("Kunden-Vorgänge")
    config = customer_cases_api_config_from_env()
    if config is None:
        st.warning("Kunden-Vorgänge API ist noch nicht konfiguriert.")
        return

    try:
        payload = load_customer_cases_from_api(config)
    except Exception:
        st.error("Kunden-Vorgänge konnten nicht geladen werden.")
        return

    cases = payload.get("data", [])
    if not isinstance(cases, list):
        cases = []

    st.caption("Prozessübersicht")
    selected_phase = render_customer_case_phase_tiles(st, cases)
    selected_phase_label = dict(CUSTOMER_CASE_PHASES)[selected_phase]

    if st.button("Neuen Vorgang anlegen", key="customer-case-create-open"):
        render_dialog(
            st,
            "Neuen Vorgang anlegen",
            lambda: render_customer_case_create_form(st, config, session),
        )

    selected_cases = [
        case for case in cases if customer_case_phase_number(case) == selected_phase
    ]

    st.caption(f"Vorgänge in Prozessphase: {selected_phase_label}")

    if not selected_cases:
        st.info("In dieser Prozessphase sind keine Kunden-Vorgänge vorhanden.")
        return

    case_options = {
        f"{case.get('case_number', '')} · {case.get('customer_full_name', '')}".strip(): case
        for case in selected_cases
    }
    selected_case_label = st.selectbox(
        "Vorgang auswählen",
        options=list(case_options.keys()),
        index=0,
    )
    selected_case = case_options[selected_case_label]
    if st.button("Ausgewählten Vorgang bearbeiten", key="customer-case-edit-open"):
        render_dialog(
            st,
            "Vorgang bearbeiten",
            lambda: render_customer_case_edit_form(st, config, session, selected_case),
        )

    table_rows = [
        {
            "Vorgangs-Nr.": str(case.get("case_number", "")),
            "Kunden-Nr.": str(case.get("customer_number", "")),
            "Kunde/Firma": str(case.get("customer_full_name", "")),
            "CARAT-Auftrags-Nr.": str(case.get("carat_order_number") or ""),
            "Priorität": CUSTOMER_CASE_PRIORITY_LABELS.get(
                str(case.get("priority", "")),
                str(case.get("priority", "")),
            ),
            "Status": str(case.get("status", "")),
            "Verantwortlich": str(
                case.get("responsible_user_id") or case.get("assigned_to") or ""
            ),
        }
        for case in selected_cases
    ]
    if hasattr(st, "dataframe"):
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    else:  # pragma: no cover - compatibility for older Streamlit runtimes.
        st.table(table_rows)


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
    tenant_shell = build_tenant_shell(tenants[tenant_id])
    branding = build_tenant_branding(selected_tenant, tenant_shell)
    st.markdown(render_tenant_theme_css(branding.theme), unsafe_allow_html=True)

    tenant_session = render_session_gate(st, selected_tenant)
    if runtime_tenant_id is not None:
        st.sidebar.title("Steuerung")
    selected_role_ids = tenant_session.role_ids
    if tenant_session.source != "local-fixture" and st.sidebar.button("Logout"):
        st.session_state.pop("scas_tenant_session", None)
        st.rerun()

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
    navigation_items = build_tenant_navigation_items(workspace_areas)
    active_route = current_route_from_query_params(st)
    visible_routes = {item.route for item in navigation_items}
    if active_route not in visible_routes:
        active_route = "/"

    st.sidebar.caption("Navigation")
    for item in navigation_items:
        st.sidebar.markdown(
            f"[{escape(item.label)}]({escape(navigation_href(item.route))})",
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
    if active_route == "/customer-cases":
        render_customer_cases_area(st, tenant_session)
        return

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
