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
class CrmAdminBlueprintPage:
    section: str
    page: str
    route: str
    depth: int
    controls: str
    write_policy: str


@dataclass(frozen=True)
class AdminCenterPage:
    group: str
    label: str
    page_id: str
    crm_route: str
    supported: bool


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


CRM_ADMIN_CENTER_BLUEPRINT: tuple[CrmAdminBlueprintPage, ...] = (
    CrmAdminBlueprintPage(
        "Meine Daten",
        "Stammdaten",
        "/user_settings",
        1,
        "Profilfoto, Vorname, Nachname, Login-E-Mail",
        "Read-only mirror; profile writes require an identity backend.",
    ),
    CrmAdminBlueprintPage(
        "Meine Daten",
        "Login-E-Mail ändern",
        "/user_settings/edit_login",
        2,
        "Aktuelles Passwort, neue Login-E-Mail",
        "Disabled until a trusted identity provider exists.",
    ),
    CrmAdminBlueprintPage(
        "Meine Daten",
        "Passwort & Sicherheit",
        "/user_settings/security",
        1,
        "Passwortstatus und Sicherheitsnavigation",
        "Read-only; local password hashes are generated separately below.",
    ),
    CrmAdminBlueprintPage(
        "Meine Daten",
        "Passwort ändern",
        "/user_settings/edit_password",
        2,
        "Aktuelles Passwort, Passwort, Wiederholung",
        "No direct password write from Streamlit; hash generation only.",
    ),
    CrmAdminBlueprintPage(
        "Meine Daten",
        "Sprache, Zeitzone & Arbeitstag",
        "/user_settings/localisation",
        1,
        "Sprache, Zeitzone, Arbeitswoche, Arbeitstag",
        "Read-only until per-user preferences are persisted.",
    ),
    CrmAdminBlueprintPage(
        "Meine Einstellungen",
        "E-Mail-Benachrichtigungen",
        "/account_user_settings/mails",
        1,
        "Aufgaben-/Termin-Mails, Benachrichtigungsfrequenz",
        "Read-only until notification delivery is implemented.",
    ),
    CrmAdminBlueprintPage(
        "Meine Einstellungen",
        "E-Mail-Ablage",
        "/account_user_settings/mailin",
        1,
        "Mailablage-Adresse, ignorierte Dateien",
        "Read-only; mailbox ingestion needs a tenant mail boundary.",
    ),
    CrmAdminBlueprintPage(
        "Meine Einstellungen",
        "Microsoft 365",
        "/account_user_settings/microsoft365",
        1,
        "Microsoft-365-E-Mail-Synchronisation",
        "Disabled until OAuth consent and token storage are implemented.",
    ),
    CrmAdminBlueprintPage(
        "Meine Einstellungen",
        "Persönliche externe Zugriffe",
        "/account_user_settings/api_keys",
        1,
        "Persönliche API-Schlüssel",
        "Read-only; secret material is never rendered by Streamlit.",
    ),
    CrmAdminBlueprintPage(
        "Meine Einstellungen",
        "Persönlichen API-Schlüssel erstellen",
        "/account_user_settings/api_keys/new",
        2,
        "Nutzer, Beschreibung",
        "Backend-governed secret creation only.",
    ),
    CrmAdminBlueprintPage(
        "Meine Einstellungen",
        "Beobachtete Seiten",
        "/account_user_settings/userobservers",
        1,
        "Beobachtete Seiten und Löschfunktion",
        "Read-only; bulk cleanup requires an audited backend action.",
    ),
    CrmAdminBlueprintPage(
        "Accounteinstellungen",
        "Accountdaten",
        "/account_settings",
        1,
        "Kundennummer, Benutzer, Kontakte, Dateispeicher",
        "Read-only tenant/account overview.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Pipelines verwalten",
        "/account_settings/deal_types",
        1,
        "Pipeline-Liste, Pipeline erstellen, Vorlagen",
        "Read-only until tenant workflow schema writes exist.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Pipeline bearbeiten",
        "/account_settings/deal_types/43851/edit",
        2,
        "Name, Eintragsnamen, Geldwert, Wahrscheinlichkeit, Zieldatum",
        "Schema changes require audited tenant-admin writes.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Phasen verwalten",
        "/account_settings/deal_types/43851/deal_type_stages",
        2,
        "Eigene Phasen, gewonnen, verloren",
        "Read-only mirror of current phase model.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Phase anlegen",
        "/account_settings/deal_types/43851/deal_type_stages/new",
        3,
        "Phasenname und Pipeline-Felder",
        "Disabled until phase creation is backed by the tenant database.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Pipeline-Vorlagen",
        "/account_settings/deal_types/43851/templates",
        3,
        "B2B, Agentur, Immobilien, Recruiting, Projekte",
        "Template application requires an audited backend action.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Eigene Felder",
        "/account_settings/custom_fields_types",
        1,
        "Feldtypen und neue Felder",
        "Read-only until tenant schema registry writes are available.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Eigenes Feld erstellen",
        "/account_settings/custom_fields_types/new",
        2,
        "Feldname, Objektart, Feldtyp",
        "Disabled; requires tenant schema migration support.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Ziele verwalten",
        "/account_settings/conversion_step_types",
        1,
        "Telefonat, Meeting, Gespräch, Chancen-Ziele",
        "Read-only until analytics goal writes are implemented.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Ziel erstellen",
        "/account_settings/conversion_step_types/new",
        2,
        "Zielname, Zieltyp, Pipeline-Zuordnung",
        "Disabled until analytics configuration is backend-governed.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Dubletten finden und entfernen",
        "/account_settings/show_dublets",
        1,
        "Personen, Firmen, Chancen, Vorschau-Modus",
        "Read-only; merging/removal needs explicit audited jobs.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Karteileichen finden",
        "/account_settings/data_cleanup",
        1,
        "Inaktivitätszeitraum, Personen, Firmen, Angebote",
        "Read-only; cleanup jobs are backend-only.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Webformulare",
        "/account_settings/web_forms",
        1,
        "Formularliste und Formular erstellen",
        "Read-only until public form routing is implemented.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Webformular erstellen",
        "/account_settings/web_forms/new",
        2,
        "Formularname und Zielobjekt",
        "Disabled until form publication and validation exist.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Vorlagen für Aufgabenlisten",
        "/account_settings/task_list_templates",
        1,
        "Aufgabenlisten-Vorlagen",
        "Read-only until workflow template writes exist.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Webadresse ändern",
        "/account_settings/edit",
        1,
        "Account-Name / Webadresse",
        "Disabled; hostname changes require DNS and tenant routing checks.",
    ),
    CrmAdminBlueprintPage(
        "Account anpassen",
        "Stammdaten bearbeiten",
        "/account_settings/edit_org_data",
        1,
        "Branche, Mitarbeitende, Firmenalter",
        "Read-only until organization profile persistence is implemented.",
    ),
    CrmAdminBlueprintPage(
        "Nutzer & Zugriffsrechte",
        "Nutzerverwaltung",
        "/account_settings/users",
        1,
        "Aktive/deaktivierte Nutzer, Rechteerklärung",
        "Uses tenant-admin context when available.",
    ),
    CrmAdminBlueprintPage(
        "Nutzer & Zugriffsrechte",
        "NutzerIn einladen",
        "/account_settings/users/new",
        2,
        "Vorname, Nachname, Login-E-Mail, Rechte",
        "Disabled until invitation delivery is implemented.",
    ),
    CrmAdminBlueprintPage(
        "Nutzer & Zugriffsrechte",
        "Mehrere NutzerInnen einladen",
        "/account_settings/users/new_multi",
        2,
        "Mehrfach-Einladung",
        "Disabled until invitation delivery is implemented.",
    ),
    CrmAdminBlueprintPage(
        "Nutzer & Zugriffsrechte",
        "Zwei-Faktor-Sicherheit",
        "/account_settings/two_factor",
        2,
        "2FA-Account-Regel",
        "Disabled until identity provider enforcement exists.",
    ),
    CrmAdminBlueprintPage(
        "Nutzer & Zugriffsrechte",
        "Nutzeraktivitäten-Logbuch",
        "/account_settings/user_actions",
        2,
        "Login, Upload, Löschung, Export, Admin-Aktivitäten",
        "Read-only audit mirror.",
    ),
    CrmAdminBlueprintPage(
        "Nutzer & Zugriffsrechte",
        "Nutzeraktivitäten ohne Login",
        "/account_settings/user_actions?scope=without_session_actions",
        3,
        "Nicht-Login-Aktivitäten",
        "Read-only audit mirror.",
    ),
    CrmAdminBlueprintPage(
        "Nutzer & Zugriffsrechte",
        "Gruppen verwalten",
        "/account_settings/groups",
        2,
        "Gruppenliste und Nutzeranzeige",
        "Read-only until group grants are in the role model.",
    ),
    CrmAdminBlueprintPage(
        "Nutzer & Zugriffsrechte",
        "Gruppen mit Nutzern anzeigen",
        "/account_settings/groups?list_users=true",
        3,
        "Gruppen inklusive Nutzer",
        "Read-only until group grants are in the role model.",
    ),
    CrmAdminBlueprintPage(
        "Externe Zugriffe & Integrationen",
        "Account-API-Schlüssel",
        "/account_settings/api_keys",
        1,
        "API-Schlüssel und OAuth-Integrationen",
        "Read-only; secrets are backend-governed.",
    ),
    CrmAdminBlueprintPage(
        "Externe Zugriffe & Integrationen",
        "API-Schlüssel erstellen",
        "/account_settings/api_keys/new",
        2,
        "Beschreibung und Scope",
        "Disabled; secret creation requires backend audit.",
    ),
    CrmAdminBlueprintPage(
        "Externe Zugriffe & Integrationen",
        "OAuth-Integrationen",
        "/account_settings/api_keys?active_tab=oauth_access_tokens",
        2,
        "OAuth-Zugriffe",
        "Read-only; token storage is never exposed.",
    ),
    CrmAdminBlueprintPage(
        "Externe Zugriffe & Integrationen",
        "Webhooks",
        "/account_settings/hooks",
        1,
        "Webhook-Liste und Ereignisüberwachung",
        "Read-only until webhook delivery is implemented.",
    ),
    CrmAdminBlueprintPage(
        "Externe Zugriffe & Integrationen",
        "Webhook anlegen",
        "/account_settings/hooks/new",
        2,
        "Ziel-URL, Ereignisse, Aktivstatus",
        "Disabled; outbound callbacks require validation and audit.",
    ),
    CrmAdminBlueprintPage(
        "Externe Zugriffe & Integrationen",
        "Integrationen",
        "/integrations",
        1,
        "Microsoft 365, Lexware, FastBill, Helpspace und weitere",
        "Operational setup pages only; marketing pages are ignored.",
    ),
    CrmAdminBlueprintPage(
        "Externe Zugriffe & Integrationen",
        "Microsoft 365 Integration",
        "/integrations/microsoft365",
        2,
        "E-Mail-Synchronisation verbinden",
        "Disabled until OAuth connect flow is available.",
    ),
    CrmAdminBlueprintPage(
        "Externe Zugriffe & Integrationen",
        "Lexware Office Integration",
        "/integrations/lexware_office",
        2,
        "Lexware-Verbindung",
        "Disabled until OAuth/API credential storage exists.",
    ),
    CrmAdminBlueprintPage(
        "Externe Zugriffe & Integrationen",
        "FastBill Integration",
        "/account_settings/api_key_externals/fastbill",
        2,
        "FastBill E-Mail, API-Schlüssel",
        "Disabled; integration secrets are backend-only.",
    ),
    CrmAdminBlueprintPage(
        "Externe Zugriffe & Integrationen",
        "Helpspace Integration",
        "/account_settings/api_key_externals/helpspace",
        2,
        "Helpspace Client ID, Zugriffstoken",
        "Disabled; integration secrets are backend-only.",
    ),
    CrmAdminBlueprintPage(
        "Paketverwaltung",
        "Paket wechseln",
        "/account_settings/show_upgrade",
        1,
        "Starter, Team, Benutzer, Kontakte, Dateien",
        "Read-only; commercial changes require billing workflow.",
    ),
    CrmAdminBlueprintPage(
        "Paketverwaltung",
        "Erweiterungen verwalten",
        "/account_settings/account_addon_purchases",
        1,
        "Pipelines, Gruppen, Ziele, Lexware, Kontakte, Dateispeicher",
        "Read-only; purchases require billing workflow.",
    ),
    CrmAdminBlueprintPage(
        "Paketverwaltung",
        "Kontakte erweitern",
        "/account_settings/account_addon_purchases?tab=contacts",
        2,
        "Kontaktpakete",
        "Read-only commercial option.",
    ),
    CrmAdminBlueprintPage(
        "Paketverwaltung",
        "Dateispeicher erweitern",
        "/account_settings/account_addon_purchases?tab=attachments",
        2,
        "Speicherpakete",
        "Read-only commercial option.",
    ),
    CrmAdminBlueprintPage(
        "Daten & Compliance",
        "Alle Daten exportieren",
        "/account_settings/show_export",
        1,
        "Komplettexport starten und Downloadhinweis",
        "Export jobs are disabled in UI and require backend approval.",
    ),
    CrmAdminBlueprintPage(
        "Daten & Compliance",
        "Auftragsverarbeitung (DSGVO)",
        "/gdpr/data_processing_agreements/new",
        1,
        "Personengruppen, verarbeitete Daten, AVV-Abschluss",
        "Read-only until legal approval workflow exists.",
    ),
    CrmAdminBlueprintPage(
        "Daten & Compliance",
        "Account zurücksetzen",
        "/account_settings/confirm_reset",
        1,
        "Passwortbestätigung",
        "Destructive action disabled; requires explicit backend workflow.",
    ),
    CrmAdminBlueprintPage(
        "Daten & Compliance",
        "Account kündigen & Daten löschen",
        "/account_settings/confirmdelete",
        1,
        "Passwortbestätigung",
        "Destructive action disabled; requires explicit backend workflow.",
    ),
    CrmAdminBlueprintPage(
        "Rechnungsverwaltung",
        "Adresse & Zahlungsdaten",
        "/bill/billing_infos/new",
        1,
        "Firmendaten, IBAN/Karte, Rechnungs-E-Mail",
        "Payment data is never collected by Streamlit.",
    ),
    CrmAdminBlueprintPage(
        "Papierkorb",
        "Personen",
        "/trash/people",
        1,
        "Gelöschte Personen",
        "Read-only; restore/delete requires backend audit.",
    ),
    CrmAdminBlueprintPage(
        "Papierkorb",
        "Firmen",
        "/trash/companies",
        1,
        "Gelöschte Firmen",
        "Read-only; restore/delete requires backend audit.",
    ),
    CrmAdminBlueprintPage(
        "Papierkorb",
        "Pipeline-Einträge",
        "/trash/deals",
        1,
        "Gelöschte Pipeline-Einträge",
        "Read-only; restore/delete requires backend audit.",
    ),
    CrmAdminBlueprintPage(
        "Papierkorb",
        "Dateien",
        "/trash/attachments",
        1,
        "Gelöschte Dateien und Wiederherstellen-Links",
        "Read-only; restore/delete requires backend audit.",
    ),
)


ADMIN_CENTER_PAGES: tuple[AdminCenterPage, ...] = (
    AdminCenterPage("Meine Daten", "Stammdaten", "profile", "/user_settings", True),
    AdminCenterPage(
        "Meine Daten",
        "Passwort & Sicherheit",
        "security",
        "/user_settings/security",
        True,
    ),
    AdminCenterPage(
        "Meine Daten",
        "Sprache, Zeitzone & Arbeitstag",
        "localisation",
        "/user_settings/localisation",
        True,
    ),
    AdminCenterPage(
        "Meine Einstellungen",
        "E-Mail-Benachrichtigungen",
        "mail_notifications",
        "/account_user_settings/mails",
        True,
    ),
    AdminCenterPage(
        "Meine Einstellungen",
        "E-Mail-Ablage",
        "mail_archive",
        "/account_user_settings/mailin",
        True,
    ),
    AdminCenterPage(
        "Meine Einstellungen",
        "Microsoft 365",
        "microsoft365",
        "/account_user_settings/microsoft365",
        False,
    ),
    AdminCenterPage(
        "Meine Einstellungen",
        "Externe Zugriffe",
        "personal_api_keys",
        "/account_user_settings/api_keys",
        False,
    ),
    AdminCenterPage(
        "Meine Einstellungen",
        "Beobachtete Seiten",
        "observed_pages",
        "/account_user_settings/userobservers",
        True,
    ),
    AdminCenterPage(
        "Accounteinstellungen",
        "Accountdaten",
        "account_data",
        "/account_settings",
        False,
    ),
    AdminCenterPage(
        "Accounteinstellungen",
        "Nutzer & Rechte",
        "users_rights",
        "/account_settings/users",
        False,
    ),
    AdminCenterPage(
        "Accounteinstellungen",
        "API, Webhooks & Integrationen",
        "account_integrations",
        "/account_settings/api_keys",
        False,
    ),
    AdminCenterPage(
        "Accounteinstellungen",
        "Paket, Export, DSGVO & Billing",
        "account_compliance",
        "/account_settings/show_upgrade",
        False,
    ),
    AdminCenterPage("Papierkorb", "Personen", "trash_people", "/trash/people", False),
    AdminCenterPage("Papierkorb", "Firmen", "trash_companies", "/trash/companies", False),
    AdminCenterPage(
        "Papierkorb",
        "Pipeline-Einträge",
        "trash_deals",
        "/trash/deals",
        False,
    ),
    AdminCenterPage("Papierkorb", "Dateien", "trash_files", "/trash/attachments", False),
)

ADMIN_CENTER_FORM_DEFAULTS: dict[str, dict[str, Any]] = {
    "profile": {
        "first_name": "Konstantin",
        "last_name": "Milonas",
        "login_email": "k.milonas@schober-daskuechenhaus.de",
    },
    "security": {
        "force_two_factor": False,
    },
    "localisation": {
        "language": "Deutsch",
        "timezone": "Europe/Berlin",
        "workweek": "Montag bis Freitag",
        "workday_start": "08:00",
        "workday_end": "17:00",
    },
    "mail_notifications": {
        "upcoming_mails": "zu Beginn jedes Arbeitstages",
        "notification_mails": "zeitnah während meines Arbeitstages",
    },
    "mail_archive": {
        "mail_archive_enabled": True,
        "ignored_attachments": "logo.png, image001.png, smime.p7s",
    },
    "observed_pages": {
        "digest_enabled": True,
    },
}

MAIL_UPCOMING_PROMPT = (
    "Wann möchtest du per E-Mail über anstehende Aufgaben, Termine, "
    "Angebote & Projekte informiert werden?"
)
MAIL_NOTIFICATION_PROMPT = (
    "Wann möchtest du per E-Mail über ungelesene Benachrichtigungen informiert werden?"
)


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
            description="Statusseite mit den dem Benutzer zugeordneten Ereignissen",
            required_capability=None,
            admin_only=False,
        )
    ]
    has_admin_area = any(
        area.admin_only or area.required_capability == "tenant-admin"
        for area in workspace_areas
    )
    if has_admin_area:
        navigation_items.append(
            TenantNavigationItem(
                label="Admin Center",
                route="/admin",
                description="Tenant administration",
                required_capability="tenant-admin",
                admin_only=True,
            )
        )
    return tuple(navigation_items)


def current_route_from_query_params(st: Any) -> str:
    query_params = getattr(st, "query_params", None)
    raw_route = query_params.get("route") if query_params is not None else None
    if isinstance(raw_route, list):
        raw_route = raw_route[0] if raw_route else "/"
    route = str(raw_route).strip()
    if route.startswith("/"):
        return route
    stored_route = st.session_state.get("scas_active_route")
    if isinstance(stored_route, str) and stored_route.startswith("/"):
        return stored_route
    return "/"


def activate_navigation_route(st: Any, route: str) -> None:
    st.session_state["scas_active_route"] = route
    query_params = getattr(st, "query_params", None)
    if query_params is not None:
        query_params["route"] = route


def render_sidebar_navigation(
    st: Any,
    navigation_items: tuple[TenantNavigationItem, ...],
    active_route: str,
) -> str:
    st.sidebar.caption("Navigation")
    selected_route = active_route
    for item in navigation_items:
        button_type = "primary" if item.route == active_route else "secondary"
        if st.sidebar.button(
            item.label,
            key=f"nav-{item.route}",
            type=button_type,
        ):
            activate_navigation_route(st, item.route)
            selected_route = item.route
    return selected_route


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


def create_customer_case_note_in_api(
    config: CustomerCasesApiConfig,
    *,
    actor: str,
    case_id: str,
    content: str,
) -> dict[str, Any]:
    payload = json.dumps(
        {
            "content": content,
            "note_type": "manual",
            "source": "manual",
        }
    ).encode("utf-8")
    api_request = urlrequest.Request(
        f"{config.base_url}/tenant-cases/{quote(case_id, safe='')}/notes",
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


def create_customer_case_task_in_api(
    config: CustomerCasesApiConfig,
    *,
    actor: str,
    case_id: str,
    title: str,
    due_date: str,
    assigned_to: str,
) -> dict[str, Any]:
    raw_payload = {
        "title": title,
        "due_date": due_date,
        "assigned_to": assigned_to,
        "source": "manual",
    }
    payload = json.dumps(
        {key: value for key, value in raw_payload.items() if str(value).strip()}
    ).encode("utf-8")
    api_request = urlrequest.Request(
        f"{config.base_url}/tenant-cases/{quote(case_id, safe='')}/tasks",
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


def load_customer_case_audit_from_api(
    config: CustomerCasesApiConfig,
    case_id: str,
) -> dict[str, Any]:
    api_request = urlrequest.Request(
        f"{config.base_url}/tenant-cases/{quote(case_id, safe='')}/audit",
        headers={
            "authorization": f"Bearer {config.token}",
            "accept": "application/json",
            "user-agent": "scas-streamlit-business-ui/1.0",
        },
        method="GET",
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


def customer_case_assigned_user_id(case: dict[str, Any]) -> str:
    for key in ("responsible_user_id", "assigned_to", "owner_id"):
        value = str(case.get(key) or "").strip()
        if value:
            return value
    return ""


def customer_case_is_assigned_to_user(case: dict[str, Any], principal_id: str) -> bool:
    return customer_case_assigned_user_id(case) == principal_id


def customer_case_display_label(case: dict[str, Any]) -> str:
    case_number = str(case.get("case_number") or "ohne Vorgangs-Nr.").strip()
    customer_name = str(case.get("customer_full_name") or "ohne Name").strip()
    carat_order_number = str(case.get("carat_order_number") or "").strip()
    if carat_order_number:
        return f"{case_number} · {customer_name} · CARAT-Auftrags-Nr. {carat_order_number}"
    return f"{case_number} · {customer_name}"


def customer_case_id(case: dict[str, Any]) -> str:
    return str(case.get("id") or case.get("case_number") or "").strip()


def customer_case_phase_label(case: dict[str, Any]) -> str:
    phase = customer_case_phase_number(case)
    return str(case.get("phase_label") or dict(CUSTOMER_CASE_PHASES)[phase])


def customer_case_timestamp(case: dict[str, Any]) -> str:
    return str(case.get("updated_at") or case.get("created_at") or "kein Datum")


def customer_case_actor(case: dict[str, Any]) -> str:
    return str(
        case.get("updated_by")
        or case.get("created_by_user_id")
        or case.get("responsible_user_id")
        or case.get("assigned_to")
        or "System"
    )


def customer_case_event_text(case: dict[str, Any]) -> str:
    if customer_case_needs_attention(case):
        return "Vorgang benötigt Aufmerksamkeit"
    if str(case.get("status") or "") == "won":
        return "Vorgang wurde gewonnen"
    if str(case.get("status") or "") == "lost":
        return "Vorgang wurde verloren"
    if case.get("updated_at") and case.get("created_at") != case.get("updated_at"):
        return "Vorgang wurde aktualisiert"
    return "Vorgang wurde angelegt"


def customer_case_priority_label(case: dict[str, Any]) -> str:
    raw_priority = str(case.get("priority") or "normal")
    return CUSTOMER_CASE_PRIORITY_LABELS.get(raw_priority, raw_priority)


def customer_case_status_label(case: dict[str, Any]) -> str:
    labels = {
        "active": "Offen",
        "paused": "Pausiert",
        "won": "Gewonnen",
        "lost": "Verloren",
        "closed": "Abgeschlossen",
    }
    raw_status = str(case.get("status") or "active")
    return labels.get(raw_status, raw_status)


def customer_case_matches_search(case: dict[str, Any], search_term: str) -> bool:
    normalized_search = search_term.strip().casefold()
    if not normalized_search:
        return True

    searchable_values = (
        case.get("customer_last_name"),
        case.get("last_name"),
        case.get("customer_full_name"),
        case.get("customer_name"),
        case.get("company_name"),
        case.get("carat_order_number"),
    )
    return any(
        normalized_search in str(value or "").casefold()
        for value in searchable_values
    )


def customer_case_matches_status_feed_search(
    case: dict[str, Any],
    search_term: str,
) -> bool:
    normalized_search = search_term.strip().casefold()
    if not normalized_search:
        return True
    searchable_values = (
        case.get("case_number"),
        case.get("customer_number"),
        case.get("customer_full_name"),
        case.get("company_name"),
        case.get("first_name"),
        case.get("last_name"),
        case.get("carat_order_number"),
        customer_case_event_text(case),
        customer_case_phase_label(case),
    )
    return any(
        normalized_search in str(value or "").casefold()
        for value in searchable_values
    )


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


def render_status_feed_sidebar(
    st: Any,
    cases: list[dict[str, Any]],
    session: TenantSession,
) -> None:
    assigned_cases = [
        case for case in cases if customer_case_is_assigned_to_user(case, session.principal_id)
    ]
    attention_cases = [case for case in assigned_cases if customer_case_needs_attention(case)]
    won_cases = [case for case in cases if str(case.get("status") or "") == "won"]

    st.markdown("### Anstehende Aufgaben")
    if attention_cases:
        for case in attention_cases[:4]:
            st.markdown(
                f"**{escape(customer_case_display_label(case))}**  \n"
                f"{escape(customer_case_phase_label(case))}"
            )
    else:
        st.info("Keine überfälligen oder markierten Aufgaben.")

    st.markdown("### Erreichte Ziele")
    if won_cases:
        for case in won_cases[:3]:
            st.markdown(f"**{escape(customer_case_display_label(case))}**")
    else:
        st.caption("In der aktuellen Ansicht wurden noch keine Ziele erreicht.")

    st.markdown("### Neuigkeiten")
    st.caption("Statusänderungen, neue Vorgänge und exportrelevante Hinweise erscheinen hier.")


def render_customer_case_event_card(st: Any, case: dict[str, Any]) -> None:
    case_id = customer_case_id(case)
    if not case_id:
        return
    event_text = customer_case_event_text(case)
    attention_marker = " · Handlungsbedarf" if customer_case_needs_attention(case) else ""
    timestamp = escape(customer_case_timestamp(case))
    actor = escape(customer_case_actor(case))
    title = escape(customer_case_display_label(case))
    body = (
        f"{escape(event_text)} · {escape(customer_case_phase_label(case))}"
        f"{escape(attention_marker)}"
    )
    st.markdown(
        f"""
        <div class="status-event-card">
            <div class="status-event-meta">{timestamp} · von {actor}</div>
            <div class="status-event-title">{title}</div>
            <div class="status-event-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Öffnen", key=f"customer-case-open-{case_id}"):
        st.session_state["scas_customer_case_selected_id"] = case_id
        if hasattr(st, "rerun"):
            st.rerun()


def render_customer_case_status_form(
    st: Any,
    config: CustomerCasesApiConfig,
    session: TenantSession,
    case: dict[str, Any],
) -> None:
    case_id = customer_case_id(case)
    if not case_id:
        st.warning("Dieser Vorgang hat keine stabile ID und kann nicht gespeichert werden.")
        return

    with st.form(f"scas-customer-case-status-{case_id}"):
        st.caption(f"Kunden-Nr.: {case.get('customer_number') or 'automatisch'}")
        case_number = st.text_input(
            "Vorgangs-Nr.",
            value=str(case.get("case_number", "")),
            key=f"status-case-number-{case_id}",
        )
        carat_order_number = st.text_input(
            "CARAT-Auftrags-Nr.",
            value=str(case.get("carat_order_number") or ""),
            key=f"status-carat-order-number-{case_id}",
        )
        phase_options = [label for _phase, label in CUSTOMER_CASE_PHASES]
        phase_label = st.selectbox(
            "Statusphase",
            options=phase_options,
            index=max(customer_case_phase_number(case) - 1, 0),
            key=f"status-phase-{case_id}",
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
            key=f"status-priority-{case_id}",
        )
        status_labels = {
            "Offen": "active",
            "Pausiert": "paused",
            "Gewonnen": "won",
            "Verloren": "lost",
            "Abgeschlossen": "closed",
        }
        current_status = str(case.get("status", "active"))
        current_status_label = next(
            (
                label
                for label, value in status_labels.items()
                if value == current_status
            ),
            "Offen",
        )
        status_label = st.selectbox(
            "Status",
            options=list(status_labels),
            index=list(status_labels).index(current_status_label),
            key=f"status-state-{case_id}",
        )
        responsible_user_id = st.text_input(
            "Verantwortlich",
            value=str(case.get("responsible_user_id") or case.get("assigned_to") or ""),
            key=f"status-responsible-{case_id}",
        )
        needs_attention = st.checkbox(
            "Handlungsbedarf",
            value=customer_case_needs_attention(case),
            key=f"status-attention-{case_id}",
        )
        save_clicked = st.form_submit_button("Speichern", key=f"status-save-{case_id}")
        cancel_clicked = st.form_submit_button("Abbrechen", key=f"status-cancel-{case_id}")

    if cancel_clicked:
        st.info("Änderungen verworfen.")
        if hasattr(st, "rerun"):
            st.rerun()
        return
    if not save_clicked:
        return

    if not case_number.strip():
        st.error("Vorgangs-Nr. ist erforderlich.")
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
            status=status_labels[status_label],
            responsible_user_id=responsible_user_id,
            needs_attention=needs_attention,
        )
    except Exception:
        st.error("Vorgang konnte nicht gespeichert werden.")
    else:
        st.success("Vorgang gespeichert.")
        if hasattr(st, "rerun"):
            st.rerun()


def render_customer_case_task_and_note_forms(
    st: Any,
    config: CustomerCasesApiConfig,
    session: TenantSession,
    case: dict[str, Any],
) -> None:
    case_id = customer_case_id(case)
    if not case_id:
        st.warning("Dieser Vorgang hat keine stabile ID.")
        return

    st.markdown("#### Notiz schreiben")
    with st.form(f"scas-customer-case-note-{case_id}"):
        note_content = st.text_input(
            "Notiz",
            key=f"status-note-{case_id}",
            placeholder="Notiz schreiben ...",
        )
        note_submitted = st.form_submit_button("Notiz speichern", key=f"note-save-{case_id}")
    if note_submitted:
        if not note_content.strip():
            st.error("Bitte eine Notiz eingeben.")
        else:
            try:
                create_customer_case_note_in_api(
                    config,
                    actor=session.principal_id,
                    case_id=case_id,
                    content=note_content,
                )
            except Exception:
                st.error("Notiz konnte nicht gespeichert werden.")
            else:
                st.success("Notiz gespeichert.")
                if hasattr(st, "rerun"):
                    st.rerun()

    st.markdown("#### Aufgabe anlegen")
    with st.form(f"scas-customer-case-task-{case_id}"):
        task_title = st.text_input(
            "Aufgabe",
            key=f"status-task-title-{case_id}",
            placeholder="Aufgabe anlegen ...",
        )
        due_date = st.text_input(
            "Fällig am",
            key=f"status-task-due-{case_id}",
            placeholder="YYYY-MM-DD",
        )
        assigned_to = st.text_input(
            "Zuständig",
            value=str(case.get("responsible_user_id") or case.get("assigned_to") or ""),
            key=f"status-task-assigned-{case_id}",
        )
        task_submitted = st.form_submit_button("Aufgabe speichern", key=f"task-save-{case_id}")
    if task_submitted:
        if not task_title.strip():
            st.error("Bitte eine Aufgabe eingeben.")
        else:
            try:
                create_customer_case_task_in_api(
                    config,
                    actor=session.principal_id,
                    case_id=case_id,
                    title=task_title,
                    due_date=due_date,
                    assigned_to=assigned_to,
                )
            except Exception:
                st.error("Aufgabe konnte nicht gespeichert werden.")
            else:
                st.success("Aufgabe gespeichert.")
                if hasattr(st, "rerun"):
                    st.rerun()


def render_customer_case_audit(
    st: Any,
    config: CustomerCasesApiConfig,
    case: dict[str, Any],
) -> None:
    case_id = customer_case_id(case)
    if not case_id:
        st.warning("Dieser Vorgang hat keine stabile ID.")
        return
    try:
        payload = load_customer_case_audit_from_api(config, case_id)
    except Exception:
        st.warning("Verlauf konnte nicht geladen werden.")
        return

    events = payload.get("data", [])
    if not isinstance(events, list) or not events:
        st.info("Noch kein Verlauf vorhanden.")
        return
    for event in events[:12]:
        action = str(event.get("action") or "Ereignis")
        actor = str(event.get("actor") or "System")
        created_at = str(event.get("created_at") or "")
        field = str(event.get("field_name") or "")
        old_value = str(event.get("old_value") or "")
        new_value = str(event.get("new_value") or "")
        detail = f" · {escape(field)}: {escape(old_value)} → {escape(new_value)}" if field else ""
        st.markdown(f"**{escape(action)}**  \n{escape(created_at)} · {escape(actor)}{detail}")


def render_customer_case_detail_panel(
    st: Any,
    config: CustomerCasesApiConfig,
    session: TenantSession,
    case: dict[str, Any] | None,
) -> None:
    st.markdown("### Kundenkarte")
    if case is None:
        st.info("Wähle links ein Ereignis aus.")
        return

    st.markdown(f"## {escape(str(case.get('customer_full_name') or 'Ohne Name'))}")
    st.caption(customer_case_display_label(case))
    phase_summary = (
        f"{customer_case_phase_number(case)} · {escape(customer_case_phase_label(case))}"
    )
    st.markdown(
        f"**Status:** {escape(customer_case_status_label(case))}  \n"
        f"**Statusphase:** {phase_summary}  \n"
        f"**Priorität:** {escape(customer_case_priority_label(case))}"
    )

    detail_page = st.selectbox(
        "Kartenbereich",
        options=["Vorgang", "Kontaktdaten", "Aufgaben & Notizen", "Verlauf"],
        index=0,
        key=f"status-detail-page-{customer_case_id(case)}",
    )

    if detail_page == "Vorgang":
        render_customer_case_status_form(st, config, session, case)
    elif detail_page == "Kontaktdaten":
        st.text_input("Kunden-Nr.", value=str(case.get("customer_number") or ""), disabled=True)
        st.text_input("Telefon", value=str(case.get("customer_phone") or ""), disabled=True)
        st.text_input("Mobil", value=str(case.get("customer_mobile") or ""), disabled=True)
        st.text_input("E-Mail", value=str(case.get("customer_email") or ""), disabled=True)
        st.text_input("PLZ", value=str(case.get("postal_code") or ""), disabled=True)
        st.text_input("Ort", value=str(case.get("city") or ""), disabled=True)
        st.info("Kontaktdaten sind in v1 sichtbar, aber noch nicht über diese Karte speicherbar.")
    elif detail_page == "Aufgaben & Notizen":
        render_customer_case_task_and_note_forms(st, config, session, case)
        st.warning("Dateiablage benötigt noch einen Upload-/Storage-Workflow.")
    else:
        render_customer_case_audit(st, config, case)


def render_customer_cases_area(
    st: Any,
    session: TenantSession,
) -> None:
    st.subheader("Übersicht")
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

    st.markdown(
        """
        <style>
        .status-event-card {
            border: 1px solid rgba(17, 17, 17, 0.12);
            border-radius: 8px;
            padding: 12px 14px;
            margin: 0 0 8px 0;
            background: #ffffff;
        }
        .status-event-meta {
            color: #555;
            font-size: 0.84rem;
            margin-bottom: 4px;
        }
        .status-event-title {
            font-weight: 700;
            margin-bottom: 2px;
        }
        .status-event-body {
            color: #222;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    status_filter = st.selectbox(
        "Status filtern",
        options=["Meine Ereignisse", "Alle Ereignisse"],
        index=0,
    )
    if status_filter == "Meine Ereignisse":
        status_cases = [
            case
            for case in cases
            if customer_case_is_assigned_to_user(case, session.principal_id)
        ]
    else:
        status_cases = cases

    if st.button("Neuen Vorgang anlegen", key="customer-case-create-open"):
        render_dialog(
            st,
            "Neuen Vorgang anlegen",
            lambda: render_customer_case_create_form(st, config, session),
        )

    st.caption("Statusfeed")
    if not status_cases:
        st.info("Für den aktuellen Filter sind keine Ereignisse vorhanden.")
        return

    search_term = st.text_input(
        "Ereignisse suchen",
        key="customer-case-search",
        placeholder="z. B. Name, Vorgangs-Nr., CARAT-Auftrags-Nr. oder Ereignis",
    )
    if search_term.strip():
        visible_cases = [
            case
            for case in status_cases
            if customer_case_matches_status_feed_search(case, search_term)
        ]
    else:
        visible_cases = status_cases[:25]

    if not visible_cases:
        st.info("Keine Ereignisse zur aktuellen Suche gefunden.")
        return

    selected_case_id = str(
        st.session_state.get("scas_customer_case_selected_id", "")
    )
    visible_case_ids = tuple(
        str(case.get("id") or case.get("case_number") or "")
        for case in visible_cases
        if case.get("id") or case.get("case_number")
    )
    if selected_case_id and selected_case_id not in visible_case_ids:
        selected_case_id = ""
        st.session_state.pop("scas_customer_case_selected_id", None)
    if not selected_case_id and visible_case_ids:
        selected_case_id = visible_case_ids[0]
        st.session_state["scas_customer_case_selected_id"] = selected_case_id

    selected_case = next(
        (
            case
            for case in visible_cases
            if customer_case_id(case) == selected_case_id
        ),
        None,
    )

    feed_column, detail_column = st.columns([0.58, 0.42])
    with feed_column:
        st.markdown(f"### {status_filter}")
        for case in visible_cases:
            render_customer_case_event_card(st, case)

    with detail_column:
        render_status_feed_sidebar(st, status_cases, session)
        st.divider()
        render_customer_case_detail_panel(st, config, session, selected_case)


def render_password_change_admin_tool(st: Any) -> None:
    st.markdown("### Passwort ändern")
    st.info(
        "Die UI speichert Passwörter nicht selbst. Für eine dauerhafte Änderung "
        "muss der erzeugte Hash in `SCAS_UI_LOGIN_USERS_JSON` übernommen und die "
        "UI neu deployed werden."
    )
    with st.form("scas-admin-password-change"):
        username = st.text_input("Benutzername")
        new_password = st.text_input("Neues Passwort", type="password")
        repeat_password = st.text_input("Neues Passwort wiederholen", type="password")
        submitted = st.form_submit_button("Passwort-Hash erzeugen")

    if not submitted:
        return

    if not username.strip():
        st.error("Bitte Benutzername eingeben.")
        return
    if new_password != repeat_password:
        st.error("Die Passwörter stimmen nicht überein.")
        return
    if len(new_password) < 12:
        st.error("Das neue Passwort muss mindestens 12 Zeichen haben.")
        return

    password_hash = encode_login_password_hash(new_password)
    st.success("Passwort-Hash erzeugt.")
    st.code(
        json.dumps(
            {
                "username": username.strip(),
                "password_hash": password_hash,
            },
            ensure_ascii=False,
            indent=2,
        ),
        language="json",
    )


def admin_center_groups() -> tuple[str, ...]:
    return tuple(dict.fromkeys(page.group for page in ADMIN_CENTER_PAGES))


def admin_center_pages_for_group(group: str) -> tuple[AdminCenterPage, ...]:
    return tuple(page for page in ADMIN_CENTER_PAGES if page.group == group)


def admin_center_page_by_id(page_id: str) -> AdminCenterPage:
    for page in ADMIN_CENTER_PAGES:
        if page.page_id == page_id:
            return page
    return ADMIN_CENTER_PAGES[0]


def admin_center_saved_state(st: Any, page_id: str) -> dict[str, Any]:
    key = f"scas_admin_center_saved_{page_id}"
    if key not in st.session_state:
        st.session_state[key] = dict(ADMIN_CENTER_FORM_DEFAULTS.get(page_id, {}))
    return dict(st.session_state[key])


def reset_admin_widget_state_if_requested(
    st: Any,
    page_id: str,
    widget_values: dict[str, Any],
) -> None:
    if not st.session_state.pop(f"scas_admin_center_reset_{page_id}", False):
        return

    for widget_key, value in widget_values.items():
        st.session_state[widget_key] = value


def render_admin_center_flash(st: Any) -> None:
    message = st.session_state.pop("scas_admin_center_flash", "")
    if message:
        st.info(str(message))


def option_index(options: tuple[str, ...], selected: Any) -> int:
    try:
        return options.index(str(selected))
    except ValueError:
        return 0


def handle_admin_form_submission(
    st: Any,
    page_id: str,
    draft: dict[str, Any],
    *,
    save_clicked: bool,
    cancel_clicked: bool,
    validate: Any | None = None,
    supports_save: bool = True,
) -> None:
    if cancel_clicked:
        st.session_state[f"scas_admin_center_reset_{page_id}"] = True
        st.session_state["scas_admin_center_flash"] = "Änderungen verworfen."
        st.info("Änderungen verworfen.")
        st.rerun()
        return

    if not save_clicked:
        return

    if validate is not None:
        validation_error = validate(draft)
        if validation_error:
            st.error(validation_error)
            return

    if not supports_save:
        st.warning(
            "Diese Aktion benötigt einen auditierten Backend-Workflow und wurde "
            "nicht gespeichert."
        )
        return

    st.session_state[f"scas_admin_center_saved_{page_id}"] = dict(draft)
    st.session_state[f"scas_admin_center_draft_{page_id}"] = dict(draft)
    st.success("Einstellungen gespeichert.")


def render_admin_center_navigation(st: Any) -> AdminCenterPage:
    groups = admin_center_groups()
    active_group = str(st.session_state.get("scas_admin_center_group", groups[0]))
    if active_group not in groups:
        active_group = groups[0]

    active_page_id = str(
        st.session_state.get(
            "scas_admin_center_page",
            admin_center_pages_for_group(active_group)[0].page_id,
        )
    )
    active_page = admin_center_page_by_id(active_page_id)
    if active_page.group != active_group:
        active_page = admin_center_pages_for_group(active_group)[0]
        active_page_id = active_page.page_id

    for group in groups:
        st.markdown(f"**{group}**")
        for page in admin_center_pages_for_group(group):
            label = f"• {page.label}" if page.page_id != active_page_id else f"▸ {page.label}"
            if st.button(label, key=f"admin-nav-{page.page_id}"):
                st.session_state["scas_admin_center_group"] = group
                st.session_state["scas_admin_center_page"] = page.page_id
                active_page = page
                active_page_id = page.page_id
        st.markdown("")

    st.session_state["scas_admin_center_group"] = active_page.group
    st.session_state["scas_admin_center_page"] = active_page.page_id
    return active_page


def render_profile_admin_page(st: Any) -> None:
    saved = admin_center_saved_state(st, "profile")
    reset_admin_widget_state_if_requested(
        st,
        "profile",
        {
            "admin-profile-first-name": str(saved.get("first_name", "")),
            "admin-profile-last-name": str(saved.get("last_name", "")),
            "admin-profile-login-email": str(saved.get("login_email", "")),
        },
    )
    st.markdown("### Stammdaten")
    st.caption("Name, Login und Profilangaben für den aktuellen Zugang.")
    with st.form("scas-admin-profile"):
        first_name = st.text_input(
            "Vorname",
            value=str(saved.get("first_name", "")),
            key="admin-profile-first-name",
        )
        last_name = st.text_input(
            "Nachname",
            value=str(saved.get("last_name", "")),
            key="admin-profile-last-name",
        )
        login_email = st.text_input(
            "E-Mail-Adresse (Login)",
            value=str(saved.get("login_email", "")),
            key="admin-profile-login-email",
        )
        save_clicked = st.form_submit_button("Speichern", key="admin-profile-save")
        cancel_clicked = st.form_submit_button("Abbrechen", key="admin-profile-cancel")

    draft = {
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "login_email": login_email.strip(),
    }

    def validate_profile(values: dict[str, Any]) -> str:
        if not values["first_name"] or not values["last_name"]:
            return "Vorname und Nachname sind erforderlich."
        if "@" not in values["login_email"]:
            return "Bitte eine gültige Login-E-Mail-Adresse eingeben."
        return ""

    handle_admin_form_submission(
        st,
        "profile",
        draft,
        save_clicked=save_clicked,
        cancel_clicked=cancel_clicked,
        validate=validate_profile,
    )


def render_security_admin_page(st: Any) -> None:
    saved = admin_center_saved_state(st, "security")
    reset_admin_widget_state_if_requested(
        st,
        "security",
        {"admin-security-force-2fa": bool(saved.get("force_two_factor", False))},
    )
    st.markdown("### Passwort & Sicherheit")
    st.caption("Passwort-Hash erzeugen und spätere 2FA-Erzwingung vorbereiten.")
    with st.form("scas-admin-security"):
        force_two_factor = st.checkbox(
            "Zwei-Faktor-Authentifizierung für diesen Zugang erzwingen",
            value=bool(saved.get("force_two_factor", False)),
            key="admin-security-force-2fa",
        )
        save_clicked = st.form_submit_button("Speichern", key="admin-security-save")
        cancel_clicked = st.form_submit_button("Abbrechen", key="admin-security-cancel")
    handle_admin_form_submission(
        st,
        "security",
        {"force_two_factor": force_two_factor},
        save_clicked=save_clicked,
        cancel_clicked=cancel_clicked,
    )
    render_password_change_admin_tool(st)


def render_localisation_admin_page(st: Any) -> None:
    saved = admin_center_saved_state(st, "localisation")
    reset_admin_widget_state_if_requested(
        st,
        "localisation",
        {
            "admin-localisation-language": saved.get("language"),
            "admin-localisation-timezone": saved.get("timezone"),
            "admin-localisation-workweek": saved.get("workweek"),
            "admin-localisation-workday-start": saved.get("workday_start"),
            "admin-localisation-workday-end": saved.get("workday_end"),
        },
    )
    languages = ("Deutsch", "Englisch")
    timezones = ("Europe/Berlin", "UTC")
    workweeks = ("Montag bis Freitag", "Montag bis Sonntag")
    starts = ("06:00", "07:00", "08:00", "09:00", "10:00")
    ends = ("15:00", "16:00", "17:00", "18:00", "19:00")

    st.markdown("### Sprache, Zeitzone & Arbeitstag")
    with st.form("scas-admin-localisation"):
        language = st.selectbox(
            "Sprache",
            options=list(languages),
            index=option_index(languages, saved.get("language")),
            key="admin-localisation-language",
        )
        timezone = st.selectbox(
            "Zeitzone",
            options=list(timezones),
            index=option_index(timezones, saved.get("timezone")),
            key="admin-localisation-timezone",
        )
        workweek = st.radio(
            "Arbeitswoche",
            options=list(workweeks),
            index=option_index(workweeks, saved.get("workweek")),
            key="admin-localisation-workweek",
        )
        workday_start = st.selectbox(
            "Arbeitstag Beginn",
            options=list(starts),
            index=option_index(starts, saved.get("workday_start")),
            key="admin-localisation-workday-start",
        )
        workday_end = st.selectbox(
            "Arbeitstag Ende",
            options=list(ends),
            index=option_index(ends, saved.get("workday_end")),
            key="admin-localisation-workday-end",
        )
        save_clicked = st.form_submit_button("Speichern", key="admin-localisation-save")
        cancel_clicked = st.form_submit_button("Abbrechen", key="admin-localisation-cancel")

    draft = {
        "language": language,
        "timezone": timezone,
        "workweek": workweek,
        "workday_start": workday_start,
        "workday_end": workday_end,
    }

    def validate_workday(values: dict[str, Any]) -> str:
        if str(values["workday_start"]) >= str(values["workday_end"]):
            return "Der Arbeitstag muss vor seinem Ende beginnen."
        return ""

    handle_admin_form_submission(
        st,
        "localisation",
        draft,
        save_clicked=save_clicked,
        cancel_clicked=cancel_clicked,
        validate=validate_workday,
    )


def render_mail_notifications_admin_page(st: Any) -> None:
    saved = admin_center_saved_state(st, "mail_notifications")
    reset_admin_widget_state_if_requested(
        st,
        "mail_notifications",
        {
            "admin-mail-notifications-upcoming": saved.get("upcoming_mails"),
            "admin-mail-notifications-notifications": saved.get("notification_mails"),
        },
    )
    upcoming_options = (
        "zu Beginn jedes Arbeitstages",
        "Montags, zu Beginn der Arbeitswoche",
        "gar nicht",
    )
    notification_options = (
        "zeitnah - maximal eine Stunde nach dem Ereignis",
        "zeitnah während meines Arbeitstages",
        "zu Beginn meines Arbeitstages",
        "gar nicht",
    )

    st.markdown("### E-Mail-Benachrichtigungen")
    with st.form("scas-admin-mail-notifications"):
        upcoming_mails = st.radio(
            MAIL_UPCOMING_PROMPT,
            options=list(upcoming_options),
            index=option_index(upcoming_options, saved.get("upcoming_mails")),
            key="admin-mail-notifications-upcoming",
        )
        notification_mails = st.radio(
            MAIL_NOTIFICATION_PROMPT,
            options=list(notification_options),
            index=option_index(notification_options, saved.get("notification_mails")),
            key="admin-mail-notifications-notifications",
        )
        save_clicked = st.form_submit_button(
            "Speichern",
            key="admin-mail-notifications-save",
        )
        cancel_clicked = st.form_submit_button(
            "Abbrechen",
            key="admin-mail-notifications-cancel",
        )
    handle_admin_form_submission(
        st,
        "mail_notifications",
        {
            "upcoming_mails": upcoming_mails,
            "notification_mails": notification_mails,
        },
        save_clicked=save_clicked,
        cancel_clicked=cancel_clicked,
    )


def render_mail_archive_admin_page(st: Any) -> None:
    saved = admin_center_saved_state(st, "mail_archive")
    reset_admin_widget_state_if_requested(
        st,
        "mail_archive",
        {
            "admin-mail-archive-enabled": bool(saved.get("mail_archive_enabled", True)),
            "admin-mail-archive-ignored": str(saved.get("ignored_attachments", "")),
        },
    )
    st.markdown("### E-Mail-Ablage")
    st.caption("Persönliche Ablageeinstellungen für E-Mails und Anhänge.")
    with st.form("scas-admin-mail-archive"):
        mail_archive_enabled = st.checkbox(
            "E-Mail-Ablage aktivieren",
            value=bool(saved.get("mail_archive_enabled", True)),
            key="admin-mail-archive-enabled",
        )
        ignored_attachments = st.text_input(
            "Folgende Dateien ignorieren",
            value=str(saved.get("ignored_attachments", "")),
            key="admin-mail-archive-ignored",
        )
        save_clicked = st.form_submit_button("Speichern", key="admin-mail-archive-save")
        cancel_clicked = st.form_submit_button("Abbrechen", key="admin-mail-archive-cancel")
    handle_admin_form_submission(
        st,
        "mail_archive",
        {
            "mail_archive_enabled": mail_archive_enabled,
            "ignored_attachments": ignored_attachments.strip(),
        },
        save_clicked=save_clicked,
        cancel_clicked=cancel_clicked,
    )


def render_microsoft365_admin_page(st: Any) -> None:
    st.markdown("### Microsoft 365")
    st.info("Microsoft 365 ist noch nicht verbunden.")
    if st.button("Integration einrichten", key="admin-microsoft365-connect"):
        st.warning("OAuth-Verbindungen benötigen einen auditierten Backend-Workflow.")


def render_personal_api_keys_admin_page(st: Any) -> None:
    st.markdown("### Externe Zugriffe")
    st.dataframe(
        [{"Typ": "Persönlicher API-Schlüssel", "Status": "Noch kein Schlüssel"}],
        hide_index=True,
        use_container_width=True,
    )
    if st.button("Neuen API-Schlüssel erstellen", key="admin-personal-api-key-new"):
        st.warning("API-Schlüssel werden nicht in Streamlit erzeugt oder angezeigt.")


def render_observed_pages_admin_page(st: Any) -> None:
    saved = admin_center_saved_state(st, "observed_pages")
    reset_admin_widget_state_if_requested(
        st,
        "observed_pages",
        {"admin-observed-pages-digest": bool(saved.get("digest_enabled", True))},
    )
    st.markdown("### Beobachtete Seiten")
    st.dataframe(
        [{"Seite": "Keine beobachteten Seiten", "Status": "leer"}],
        hide_index=True,
        use_container_width=True,
    )
    with st.form("scas-admin-observed-pages"):
        digest_enabled = st.checkbox(
            "Aktivitätszusammenfassung für beobachtete Seiten anzeigen",
            value=bool(saved.get("digest_enabled", True)),
            key="admin-observed-pages-digest",
        )
        save_clicked = st.form_submit_button("Speichern", key="admin-observed-pages-save")
        cancel_clicked = st.form_submit_button("Abbrechen", key="admin-observed-pages-cancel")
    handle_admin_form_submission(
        st,
        "observed_pages",
        {"digest_enabled": digest_enabled},
        save_clicked=save_clicked,
        cancel_clicked=cancel_clicked,
    )
    if st.button("Alle Beobachtungen entfernen", key="admin-observed-pages-clear"):
        st.warning("Das Entfernen aller Beobachtungen benötigt einen Backend-Audit-Workflow.")


def render_account_data_admin_page(
    st: Any,
    tenant_shell: TenantShell,
    admin_section: TenantAdminSection,
) -> None:
    st.markdown("### Accountdaten")
    st.dataframe(
        [
            {"Feld": "Tenant", "Wert": tenant_shell.display_name},
            {"Feld": "Rechtlicher Name", "Wert": tenant_shell.legal_name},
            {"Feld": "Hostname", "Wert": tenant_shell.hostname},
            {"Feld": "Status", "Wert": tenant_shell.status},
            {"Feld": "Admin-Routen", "Wert": str(admin_section.settings.get("admin_routes", ""))},
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.info("Account-Stammdaten werden in v1 angezeigt, aber nicht direkt gespeichert.")


def render_users_rights_admin_page(st: Any, admin_section: TenantAdminSection) -> None:
    st.markdown("### Nutzer & Rechte")
    st.dataframe(list(admin_section.users), hide_index=True, use_container_width=True)
    st.dataframe(list(admin_section.roles), hide_index=True, use_container_width=True)
    if st.button("NutzerIn einladen", key="admin-users-invite"):
        st.warning("Einladungen benötigen einen Mail-/Identity-Backend-Workflow.")


def render_account_integrations_admin_page(st: Any) -> None:
    st.markdown("### API, Webhooks & Integrationen")
    st.dataframe(
        [
            {"Bereich": "API-Schlüssel", "Status": "Backend erforderlich"},
            {"Bereich": "Webhooks", "Status": "Backend erforderlich"},
            {"Bereich": "Microsoft 365", "Status": "Nicht verbunden"},
            {"Bereich": "FastBill / Helpspace", "Status": "Secret-Speicher erforderlich"},
        ],
        hide_index=True,
        use_container_width=True,
    )
    if st.button("Webhook anlegen", key="admin-webhook-new"):
        st.warning("Webhooks benötigen validierte Ziel-URLs und Audit-Events.")


def render_account_compliance_admin_page(st: Any) -> None:
    st.markdown("### Paket, Export, DSGVO & Billing")
    st.dataframe(
        [
            {"Bereich": "Paket wechseln", "Aktion": "nur anzeigen"},
            {"Bereich": "Alle Daten exportieren", "Aktion": "Backend-Job erforderlich"},
            {"Bereich": "Auftragsverarbeitung", "Aktion": "rechtlicher Workflow erforderlich"},
            {"Bereich": "Adresse & Zahlungsdaten", "Aktion": "nie in Streamlit speichern"},
            {"Bereich": "Account zurücksetzen/löschen", "Aktion": "deaktiviert"},
        ],
        hide_index=True,
        use_container_width=True,
    )


def render_trash_admin_page(st: Any, page: AdminCenterPage) -> None:
    st.markdown(f"### Papierkorb: {page.label}")
    st.dataframe(
        [{"Eintrag": "Keine wiederherstellbaren Einträge", "Status": "leer"}],
        hide_index=True,
        use_container_width=True,
    )
    if st.button(
        "Alle Einträge auf dieser Seite wiederherstellen",
        key=f"admin-{page.page_id}-restore",
    ):
        st.warning("Wiederherstellungen benötigen einen auditierten Backend-Workflow.")


def render_admin_center_page(
    st: Any,
    page: AdminCenterPage,
    tenant_shell: TenantShell,
    admin_section: TenantAdminSection,
) -> None:
    st.markdown(f"## {page.label}")
    st.caption(f"CRM-Referenz: {page.crm_route}")
    render_admin_center_flash(st)
    if page.page_id == "profile":
        render_profile_admin_page(st)
    elif page.page_id == "security":
        render_security_admin_page(st)
    elif page.page_id == "localisation":
        render_localisation_admin_page(st)
    elif page.page_id == "mail_notifications":
        render_mail_notifications_admin_page(st)
    elif page.page_id == "mail_archive":
        render_mail_archive_admin_page(st)
    elif page.page_id == "microsoft365":
        render_microsoft365_admin_page(st)
    elif page.page_id == "personal_api_keys":
        render_personal_api_keys_admin_page(st)
    elif page.page_id == "observed_pages":
        render_observed_pages_admin_page(st)
    elif page.page_id == "account_data":
        render_account_data_admin_page(st, tenant_shell, admin_section)
    elif page.page_id == "users_rights":
        render_users_rights_admin_page(st, admin_section)
    elif page.page_id == "account_integrations":
        render_account_integrations_admin_page(st)
    elif page.page_id == "account_compliance":
        render_account_compliance_admin_page(st)
    elif page.group == "Papierkorb":
        render_trash_admin_page(st, page)
    else:
        st.warning("Diese Admin-Seite ist noch nicht umgesetzt.")


def crm_admin_blueprint_rows(
    pages: Iterable[CrmAdminBlueprintPage] = CRM_ADMIN_CENTER_BLUEPRINT,
) -> list[dict[str, Any]]:
    return [
        {
            "Bereich": page.section,
            "Ebene": page.depth,
            "Seite": page.page,
            "CRM-Route": page.route,
            "Felder / Controls": page.controls,
            "Schreibmodus": page.write_policy,
        }
        for page in pages
    ]


def render_crm_admin_blueprint(st: Any) -> None:
    rows = crm_admin_blueprint_rows()
    sections = tuple(dict.fromkeys(row["Bereich"] for row in rows))
    protected_actions = sum(
        1
        for row in rows
        if "disabled" in row["Schreibmodus"].lower()
        or "backend" in row["Schreibmodus"].lower()
        or "destructive" in row["Schreibmodus"].lower()
    )
    st.markdown("### CentralStationCRM-Adminstruktur")
    st.caption(
        "Read-only nachgebaut aus dem Browser-Audit. Marketing- und reine "
        "Partner-Landingpages sind ausgelassen; operative Integrations-Setups "
        "bleiben sichtbar."
    )
    blueprint_columns = st.columns(3)
    blueprint_columns[0].metric("Bereiche", len(sections))
    blueprint_columns[1].metric("Seiten", len(rows))
    blueprint_columns[2].metric("Geschützte Aktionen", protected_actions)

    for section in sections:
        st.markdown(f"#### {section}")
        st.dataframe(
            [row for row in rows if row["Bereich"] == section],
            hide_index=True,
            use_container_width=True,
        )


def render_admin_dashboard(
    st: Any,
    session: TenantSession,
    tenant_shell: TenantShell,
    admin_section: TenantAdminSection,
) -> None:
    st.subheader("Admin Center")
    if "tenant-admin" not in session.capabilities:
        st.error("Admin Center ist für diese Sitzung nicht freigeschaltet.")
        return

    st.caption(f"Angemeldet als: {session.principal_id}")
    nav_column, content_column = st.columns([0.28, 0.72])
    with nav_column:
        active_page = render_admin_center_navigation(st)
    with content_column:
        render_admin_center_page(st, active_page, tenant_shell, admin_section)


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
    tenant_admin_section = build_tenant_admin_section(selected_tenant)
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
            tenant_admin_section = build_tenant_admin_section_from_context(admin_context)
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

    active_route = render_sidebar_navigation(st, navigation_items, active_route)

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
    if active_route == "/" and "customer-cases" in tenant_session.capabilities:
        render_customer_cases_area(st, tenant_session)
        return
    if active_route == "/admin":
        render_admin_dashboard(st, tenant_session, tenant_shell, tenant_admin_section)
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
