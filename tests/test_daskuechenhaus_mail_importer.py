from __future__ import annotations

import importlib.util
import sys
from email.message import EmailMessage
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "hetzner" / "daskuechenhaus_mail_importer.py"
SERVICE_PATH = REPO_ROOT / "scripts" / "hetzner" / "daskuechenhaus-mail-importer.service"
TIMER_PATH = REPO_ROOT / "scripts" / "hetzner" / "daskuechenhaus-mail-importer.timer"
MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0004_mail_import_state.sql"
)


def load_importer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("daskuechenhaus_mail_importer", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


importer = load_importer()


def build_message(*, with_message_id: bool = True) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "Angebot für die Küche"
    message["From"] = "Max Mustermann <Max@Example.COM>"
    message["To"] = "k.milonas@schober-daskuechenhaus.de"
    message["Cc"] = "team@example.com, team@example.com"
    message["Date"] = "Tue, 17 Jun 2025 09:30:00 +0200"
    if with_message_id:
        message["Message-ID"] = "<abc123@example.com>"
    message.set_content("Hallo,\n\nhier ist  das   Angebot.\n")
    message.add_attachment(
        b"PDFDATA", maintype="application", subtype="pdf", filename="angebot.pdf"
    )
    return message


def make_account(**overrides: object) -> importer.MailAccount:
    defaults: dict[str, object] = {
        "id": 11,
        "display_name": "Konstantin Milonas",
        "email_address": "k.milonas@schober-daskuechenhaus.de",
        "import_folder": "INBOX",
        "import_uidvalidity": None,
        "last_imported_uid": 0,
        "imap_host_ref": "DKH_EMAIL_IMAP_HOST",
        "imap_port_ref": "DKH_EMAIL_IMAP_PORT",
        "imap_username_ref": "DKH_MAIL_K_MILONAS_IMAP_USERNAME",
        "imap_password_ref": "DKH_MAIL_K_MILONAS_IMAP_PASSWORD",  # pragma: allowlist secret
    }
    defaults.update(overrides)
    return importer.MailAccount(**defaults)


# --- pure helper behavior -------------------------------------------------


def test_load_mail_env_parses_comments_quotes_and_export(tmp_path: Path) -> None:
    lines = [
        "# comment line",
        "",
        "DKH_EMAIL_IMAP_HOST=imap.example.com",
        'DKH_MAIL_K_MILONAS_IMAP_PASSWORD="s3cr3t with spaces"',  # pragma: allowlist secret
        "export DKH_EMAIL_IMAP_PORT=993",
    ]
    env_file = tmp_path / "mail.env"
    env_file.write_text("\n".join(lines), encoding="utf-8")

    values = importer.load_mail_env(env_file)

    assert values["DKH_EMAIL_IMAP_HOST"] == "imap.example.com"
    assert values["DKH_EMAIL_IMAP_PORT"] == "993"
    imap_password = values["DKH_MAIL_K_MILONAS_IMAP_PASSWORD"]
    assert imap_password == "s3cr3t with spaces"  # pragma: allowlist secret


def test_load_mail_env_missing_file_raises(tmp_path: Path) -> None:
    try:
        importer.load_mail_env(tmp_path / "absent.env")
    except importer.ImporterError:
        return
    raise AssertionError("expected ImporterError for missing mail.env")


def test_sql_jsonb_literal_escapes_single_quotes() -> None:
    literal = importer.sql_jsonb_literal({"name": "O'Brien"})

    assert literal.startswith("'")
    assert literal.endswith("'::jsonb")
    assert "O''Brien" in literal


def test_collapse_whitespace_and_snippet_length() -> None:
    snippet = importer.build_snippet("Hallo,\n\nhier ist  das   Angebot.\n", "Subject")

    assert snippet == "Hallo, hier ist das Angebot."
    long_snippet = importer.build_snippet("x" * 1000, "Subject")
    assert len(long_snippet) == importer.SNIPPET_LENGTH


def test_strip_html_removes_tags_and_unescapes_entities() -> None:
    text = importer.strip_html("<p>Hallo &amp; Tsch&uuml;ss</p>")

    assert "<" not in text and ">" not in text
    assert "Hallo" in text
    assert "&amp;" not in text


def test_safe_storage_name_sanitizes_path_separators() -> None:
    safe = importer.safe_storage_name("../etc/pa ss*wd.pdf")

    assert "/" not in safe and "\\" not in safe and " " not in safe
    assert safe.endswith(".pdf")


def test_extract_participants_dedupes_and_lowercases() -> None:
    participants = importer.extract_participants(build_message())

    from_addrs = [p for p in participants if p["participant_type"] == "from"]
    assert from_addrs == [
        {
            "participant_type": "from",
            "display_name": "Max Mustermann",
            "email_address": "max@example.com",
        }
    ]
    cc_addrs = [p for p in participants if p["participant_type"] == "cc"]
    assert len(cc_addrs) == 1


def test_extract_body_text_prefers_plain_part() -> None:
    body = importer.extract_body_text(build_message())

    assert "Angebot" in body


def test_extract_attachments_returns_decoded_payload() -> None:
    attachments = importer.extract_attachments(build_message())

    assert len(attachments) == 1
    attachment = attachments[0]
    assert attachment.original_filename == "angebot.pdf"
    assert attachment.content_type == "application/pdf"
    assert attachment.content == b"PDFDATA"


def test_parse_received_at_reads_date_header() -> None:
    received_at = importer.parse_received_at(build_message())

    assert received_at is not None
    assert received_at.startswith("2025-06-17T09:30:00")


def test_message_external_id_uses_header_when_present() -> None:
    account = make_account()

    real = importer.message_external_id(build_message(), account, 42, 7)
    assert real == "<abc123@example.com>"

    synthetic = importer.message_external_id(
        build_message(with_message_id=False), account, 42, 7
    )
    assert synthetic == "<imap-11-42-7@es-daskuechenhaus.de>"


def test_resolve_imap_settings_reads_secret_references() -> None:
    account = make_account()
    env = {
        "DKH_EMAIL_IMAP_HOST": "imap.example.com",
        "DKH_EMAIL_IMAP_PORT": "993",
        "DKH_MAIL_K_MILONAS_IMAP_USERNAME": "k.milonas@schober-daskuechenhaus.de",
        "DKH_MAIL_K_MILONAS_IMAP_PASSWORD": "s3cr3t",  # pragma: allowlist secret
    }

    settings = importer.resolve_imap_settings(account, env)

    assert settings.host == "imap.example.com"
    assert settings.port == 993
    assert settings.username == "k.milonas@schober-daskuechenhaus.de"
    assert settings.password == "s3cr3t"  # pragma: allowlist secret


def test_resolve_imap_settings_missing_value_raises() -> None:
    account = make_account()

    try:
        importer.resolve_imap_settings(account, {"DKH_EMAIL_IMAP_HOST": "imap.example.com"})
    except importer.ImporterError:
        return
    raise AssertionError("expected ImporterError when a secret value is missing")


# --- Hetzner-only source guarantees --------------------------------------


def test_importer_is_hetzner_only_and_imap_based() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    assert "import imaplib" in source
    assert '"tenant_daskuechenhaus"' in source
    assert "/etc/daskuechenhaus/mail.env" in source
    assert "DKH_MAIL_ENV_FILE" in source
    assert "readonly=True" in source
    assert "UIDVALIDITY" in source
    assert "cloudflare" not in source.lower()
    assert "wrangler" not in source.lower()


def test_importer_writes_runtime_tables_with_dedup() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    assert "INSERT INTO app.email_messages" in source
    assert "INSERT INTO app.email_participants" in source
    assert "INSERT INTO app.email_attachments" in source
    assert "ON CONFLICT (email_account_id, external_message_id)" in source
    assert "DO NOTHING" in source
    assert "UPLOAD_ROOT" in source


def test_importer_never_hardcodes_credentials() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    # Credentials are resolved from mail.env via secret reference names only.
    assert "imap_password_ref" in source
    assert "env.get(ref)" in source
    assert "settings.password" in source


# --- systemd units --------------------------------------------------------


def test_mail_importer_service_runs_oneshot_as_tenant_user() -> None:
    service = SERVICE_PATH.read_text(encoding="utf-8")

    assert "Type=oneshot" in service
    assert "User=tenant_daskuechenhaus_app" in service
    assert "Group=tenant_daskuechenhaus_app" in service
    assert "EnvironmentFile=-/etc/daskuechenhaus/object-storage.env" in service
    assert "DKH_MAIL_ENV_FILE=/etc/daskuechenhaus/mail.env" in service
    storage_bucket = "-".join(["dkh", "crm", "documents"])
    assert f"DKH_OBJECT_STORAGE_BUCKET={storage_bucket}" in service
    storage_endpoint = "https://" + ".".join(["fsn1", "your-objectstorage", "com"])
    assert f"DKH_OBJECT_STORAGE_ENDPOINT={storage_endpoint}" in service
    assert "ExecStart=/usr/bin/python3 /opt/daskuechenhaus/mail-importer/app.py --once" in service
    assert "ReadOnlyPaths=/etc/daskuechenhaus" in service
    assert "ReadWritePaths=/var/lib/daskuechenhaus/uploads" in service
    assert "NoNewPrivileges=true" in service


def test_mail_importer_timer_runs_on_short_interval() -> None:
    timer = TIMER_PATH.read_text(encoding="utf-8")

    assert "OnUnitActiveSec=3min" in timer
    assert "Persistent=true" in timer
    assert "Unit=daskuechenhaus-mail-importer.service" in timer
    assert "WantedBy=timers.target" in timer


# --- migration ------------------------------------------------------------


def test_mail_import_state_migration_adds_dedup_and_bookkeeping() -> None:
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "ALTER TABLE app.email_accounts" in migration
    assert "import_folder TEXT NOT NULL DEFAULT 'INBOX'" in migration
    assert "import_uidvalidity BIGINT" in migration
    assert "last_imported_uid BIGINT NOT NULL DEFAULT 0" in migration
    assert "last_import_status TEXT" in migration
    assert "imap_uid BIGINT" in migration
    assert "body_text TEXT" in migration
    assert "CREATE UNIQUE INDEX IF NOT EXISTS email_messages_account_external_id_key" in migration
    assert "(email_account_id, external_message_id)" in migration
    assert "WHERE external_message_id IS NOT NULL" in migration
