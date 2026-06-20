#!/usr/bin/env python3
"""
What: Hetzner-only IMAP to PostgreSQL mail importer for es-daskuechenhaus.de.
Does: Fetches new inbound mail per active app.email_accounts mailbox over IMAP,
      deduplicates on the Message-ID, and writes messages, participants, and
      attachments into the tenant_daskuechenhaus runtime database.
Why: The Uebersicht (index.php) shows E-Mail-Eingaenge only when mail rows exist
     in PostgreSQL; runtime mail data and credentials must never leave Hetzner.
Who: Run by the daskuechenhaus-mail-importer.service systemd unit on a timer.
Depends: Python 3.11+ stdlib (imaplib, email, ssl, subprocess), psql peer auth as
         tenant_daskuechenhaus_app, /etc/daskuechenhaus/mail.env secret values.
"""
from __future__ import annotations

import argparse
import contextlib
import imaplib
import json
import logging
import re
import ssl
import subprocess
import sys
from dataclasses import dataclass
from email import message_from_bytes
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.policy import default as default_policy
from email.utils import getaddresses, parsedate_to_datetime
from html import unescape
from os import environ
from pathlib import Path
from typing import Any
from uuid import uuid4

LOGGER = logging.getLogger("daskuechenhaus_mail_importer")

DATABASE = environ.get("DKH_ADMIN_DATABASE", "tenant_daskuechenhaus")
MAIL_ENV_FILE = Path(environ.get("DKH_MAIL_ENV_FILE", "/etc/daskuechenhaus/mail.env"))
UPLOAD_ROOT = Path(environ.get("DKH_ADMIN_UPLOAD_ROOT", "/var/lib/daskuechenhaus/uploads"))

SNIPPET_LENGTH = 280
BODY_TEXT_MAX = 1_000_000
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
DEFAULT_MAX_MESSAGES = 200
NO_SUBJECT = "(Kein Betreff)"  # German UI fallback shown on the Uebersicht.

PARTICIPANT_HEADERS = (
    ("from", "From"),
    ("to", "To"),
    ("cc", "Cc"),
    ("bcc", "Bcc"),
    ("reply_to", "Reply-To"),
)

HTML_TAG_RE = re.compile(r"<[^>]+>")
UIDVALIDITY_RE = re.compile(r"UIDVALIDITY\s+(\d+)")


class ImporterError(Exception):
    """Raised for recoverable per-account import failures."""


@dataclass(frozen=True)
class MailAccount:
    id: int
    display_name: str
    email_address: str
    import_folder: str
    import_uidvalidity: int | None
    last_imported_uid: int
    imap_host_ref: str | None
    imap_port_ref: str | None
    imap_username_ref: str | None
    imap_password_ref: str | None


@dataclass(frozen=True)
class ImapSettings:
    host: str
    port: int
    username: str
    password: str


@dataclass(frozen=True)
class ParsedAttachment:
    original_filename: str
    content_type: str
    content: bytes


def load_mail_env(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE secret values from the Hetzner-local mail.env file."""
    if not path.exists():
        raise ImporterError(f"mail env file not found: {path}")
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, separator, value = line.partition("=")
        if not separator:
            continue
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def decode_mime_header(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value))).strip()
    except (ValueError, LookupError):
        return value.strip()


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_html(html: str) -> str:
    return unescape(HTML_TAG_RE.sub(" ", html))


def _part_text(part: Any) -> str:
    try:
        content = part.get_content()
    except (LookupError, ValueError):
        payload = part.get_payload(decode=True)
        if not payload:
            return ""
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")
    return str(content)


def extract_body_text(message: EmailMessage) -> str:
    plain = message.get_body(preferencelist=("plain",))
    if plain is not None:
        text = _part_text(plain)
    else:
        html_part = message.get_body(preferencelist=("html",))
        text = strip_html(_part_text(html_part)) if html_part is not None else ""
    return text[:BODY_TEXT_MAX]


def build_snippet(body_text: str, subject: str) -> str:
    return collapse_whitespace(body_text or subject)[:SNIPPET_LENGTH]


def extract_participants(message: EmailMessage) -> list[dict[str, str]]:
    participants: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for participant_type, header in PARTICIPANT_HEADERS:
        raw_values = [str(value) for value in message.get_all(header, [])]
        for raw_name, raw_email in getaddresses(raw_values):
            address = raw_email.strip().lower()
            if not address or "@" not in address:
                continue
            key = (participant_type, address)
            if key in seen:
                continue
            seen.add(key)
            participants.append(
                {
                    "participant_type": participant_type,
                    "display_name": decode_mime_header(raw_name),
                    "email_address": address,
                }
            )
    return participants


def extract_attachments(message: EmailMessage) -> list[ParsedAttachment]:
    attachments: list[ParsedAttachment] = []
    for part in message.iter_attachments():
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        if len(payload) > MAX_ATTACHMENT_BYTES:
            LOGGER.warning("skipping oversized attachment (%d bytes)", len(payload))
            continue
        filename = decode_mime_header(part.get_filename()) or f"attachment-{uuid4().hex}"
        attachments.append(
            ParsedAttachment(
                original_filename=filename,
                content_type=part.get_content_type(),
                content=bytes(payload),
            )
        )
    return attachments


def parse_received_at(message: EmailMessage) -> str | None:
    raw = message.get("Date")
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(str(raw))
    except (TypeError, ValueError):
        return None
    return parsed.isoformat() if parsed is not None else None


def message_external_id(
    message: EmailMessage, account: MailAccount, uidvalidity: int, uid: int
) -> str:
    raw = message.get("Message-ID") or message.get("Message-Id")
    if raw:
        candidate = collapse_whitespace(str(raw))
        if candidate:
            return candidate
    return f"<imap-{account.id}-{uidvalidity}-{uid}@es-daskuechenhaus.de>"


def safe_storage_name(filename: str) -> str:
    name = Path(filename).name
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return safe or f"attachment-{uuid4().hex}"


def sql_jsonb_literal(payload: dict[str, Any]) -> str:
    """Build a safely quoted PostgreSQL jsonb literal for stdin-delivered SQL.

    Large mail bodies can exceed the per-argument size limit of psql ``-v``
    variables, so the payload is embedded into the SQL stream instead. Only
    single quotes need doubling because standard_conforming_strings is on.
    """
    raw = json.dumps(payload, ensure_ascii=False)
    return "'" + raw.replace("'", "''") + "'::jsonb"


def run_psql(sql: str, variables: dict[str, str] | None = None) -> str:
    command = ["psql", "-X", "-q", "-t", "-A", "-v", "ON_ERROR_STOP=1", "-d", DATABASE]
    for key, value in (variables or {}).items():
        command.extend(["-v", f"{key}={value}"])
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        input=sql,
        text=True,
    )
    if result.returncode != 0:
        raise ImporterError(result.stderr.strip() or "database_error")
    return result.stdout.strip()


def psql_json(sql: str, variables: dict[str, str] | None = None) -> Any:
    text = run_psql(sql, variables)
    if not text:
        return None
    return json.loads(text)


def load_accounts(only_email: str | None) -> list[MailAccount]:
    rows = (
        psql_json(
            """
            SELECT COALESCE(jsonb_agg(jsonb_build_object(
              'id', a.id,
              'display_name', a.display_name,
              'email_address', a.email_address,
              'import_folder', a.import_folder,
              'import_uidvalidity', a.import_uidvalidity,
              'last_imported_uid', a.last_imported_uid,
              'imap_host_ref', a.imap_host_secret_ref,
              'imap_port_ref', a.imap_port_secret_ref,
              'imap_username_ref', a.imap_username_secret_ref,
              'imap_password_ref', a.imap_password_secret_ref
            ) ORDER BY a.id), '[]'::jsonb)::text
            FROM app.email_accounts a
            WHERE a.is_active = TRUE
              AND a.imap_username_secret_ref IS NOT NULL
              AND a.imap_password_secret_ref IS NOT NULL;
            """
        )
        or []
    )
    accounts = [_account_from_row(row) for row in rows]
    if only_email:
        target = only_email.strip().lower()
        accounts = [account for account in accounts if account.email_address == target]
    return accounts


def _account_from_row(row: dict[str, Any]) -> MailAccount:
    uidvalidity = row.get("import_uidvalidity")
    return MailAccount(
        id=int(row["id"]),
        display_name=row["display_name"],
        email_address=row["email_address"],
        import_folder=row.get("import_folder") or "INBOX",
        import_uidvalidity=int(uidvalidity) if uidvalidity is not None else None,
        last_imported_uid=int(row.get("last_imported_uid") or 0),
        imap_host_ref=row.get("imap_host_ref"),
        imap_port_ref=row.get("imap_port_ref"),
        imap_username_ref=row.get("imap_username_ref"),
        imap_password_ref=row.get("imap_password_ref"),
    )


def resolve_imap_settings(account: MailAccount, env: dict[str, str]) -> ImapSettings:
    def required(ref: str | None, label: str) -> str:
        if not ref:
            raise ImporterError(f"missing secret reference for {label}")
        value = env.get(ref)
        if not value:
            raise ImporterError(f"missing mail.env value for {label} ({ref})")
        return value

    host = required(account.imap_host_ref, "imap_host")
    port_raw = required(account.imap_port_ref, "imap_port")
    username = required(account.imap_username_ref, "imap_username")
    password = required(account.imap_password_ref, "imap_password")
    try:
        port = int(port_raw)
    except ValueError as error:
        raise ImporterError(f"imap_port is not numeric: {port_raw}") from error
    return ImapSettings(host=host, port=port, username=username, password=password)


def _quote_folder(folder: str) -> str:
    return '"' + folder.replace('"', '\\"') + '"'


def connect_imap(settings: ImapSettings) -> imaplib.IMAP4:
    context = ssl.create_default_context()
    if settings.port == 143:
        client: imaplib.IMAP4 = imaplib.IMAP4(settings.host, settings.port)
        client.starttls(ssl_context=context)
    else:
        client = imaplib.IMAP4_SSL(settings.host, settings.port, ssl_context=context)
    client.login(settings.username, settings.password)
    return client


def folder_uidvalidity(client: imaplib.IMAP4, folder: str) -> int:
    status, data = client.status(_quote_folder(folder), "(UIDVALIDITY)")
    if status != "OK" or not data or data[0] is None:
        raise ImporterError(f"cannot read UIDVALIDITY for folder {folder}")
    raw = data[0].decode("utf-8", errors="replace") if isinstance(data[0], bytes) else str(data[0])
    match = UIDVALIDITY_RE.search(raw)
    if not match:
        raise ImporterError(f"unexpected UIDVALIDITY response: {raw}")
    return int(match.group(1))


def search_new_uids(client: imaplib.IMAP4, start_uid: int) -> list[int]:
    status, data = client.uid("search", None, f"UID {start_uid}:*")
    if status != "OK":
        raise ImporterError("IMAP UID search failed")
    if not data or not data[0]:
        return []
    raw = data[0].decode("utf-8", errors="replace") if isinstance(data[0], bytes) else str(data[0])
    uids = sorted({int(token) for token in raw.split() if token.isdigit()})
    # `UID n:*` can return the highest UID even when it is below n; drop those.
    return [uid for uid in uids if uid >= start_uid]


def fetch_message(client: imaplib.IMAP4, uid: int) -> EmailMessage | None:
    status, data = client.uid("fetch", str(uid), "(RFC822)")
    if status != "OK" or not data:
        return None
    for item in data:
        if isinstance(item, tuple) and len(item) >= 2 and item[1]:
            parsed = message_from_bytes(bytes(item[1]), policy=default_policy)
            if isinstance(parsed, EmailMessage):
                return parsed
    return None


def insert_message(
    account: MailAccount, uid: int, external_id: str, message: EmailMessage
) -> int | None:
    subject = decode_mime_header(message.get("Subject")) or NO_SUBJECT
    body_text = extract_body_text(message)
    payload = {
        "email_account_id": account.id,
        "external_message_id": external_id,
        "imap_uid": uid,
        "direction": "inbound",
        "subject": subject,
        "snippet": build_snippet(body_text, subject),
        "body_text": body_text,
        "received_at": parse_received_at(message) or "",
        "participants": extract_participants(message),
    }
    result = psql_json(
        f"""
        WITH payload AS (SELECT {sql_jsonb_literal(payload)} AS data),
        inserted AS (
          INSERT INTO app.email_messages (
            email_account_id, external_message_id, imap_uid, direction,
            subject, snippet, body_text, received_at
          )
          SELECT
            (data->>'email_account_id')::bigint,
            data->>'external_message_id',
            NULLIF(data->>'imap_uid', '')::bigint,
            data->>'direction',
            data->>'subject',
            NULLIF(data->>'snippet', ''),
            NULLIF(data->>'body_text', ''),
            NULLIF(data->>'received_at', '')::timestamptz
          FROM payload
          ON CONFLICT (email_account_id, external_message_id)
            WHERE external_message_id IS NOT NULL
            DO NOTHING
          RETURNING id
        ),
        participants AS (
          INSERT INTO app.email_participants (
            email_message_id, participant_type, display_name, email_address
          )
          SELECT
            inserted.id,
            part.participant_type,
            NULLIF(part.display_name, ''),
            part.email_address
          FROM inserted
          CROSS JOIN payload
          CROSS JOIN LATERAL jsonb_to_recordset(payload.data->'participants') AS part(
            participant_type text, display_name text, email_address text
          )
          RETURNING email_message_id
        )
        SELECT jsonb_build_object('id', (SELECT id FROM inserted))::text;
        """
    )
    if not result or result.get("id") is None:
        return None
    return int(result["id"])


def insert_attachment(message_id: int, attachment: ParsedAttachment, storage_path: Path) -> None:
    payload = {
        "email_message_id": message_id,
        "original_filename": attachment.original_filename,
        "storage_path": str(storage_path),
        "content_type": attachment.content_type,
        "file_size_bytes": len(attachment.content),
    }
    run_psql(
        f"""
        WITH payload AS (SELECT {sql_jsonb_literal(payload)} AS data)
        INSERT INTO app.email_attachments (
          email_message_id, original_filename, storage_path,
          content_type, file_size_bytes
        )
        SELECT
          (data->>'email_message_id')::bigint,
          data->>'original_filename',
          data->>'storage_path',
          data->>'content_type',
          (data->>'file_size_bytes')::bigint
        FROM payload;
        """
    )


def store_attachments(message_id: int, message: EmailMessage) -> int:
    attachments = extract_attachments(message)
    if not attachments:
        return 0
    target_dir = UPLOAD_ROOT / "emails" / str(message_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    for attachment in attachments:
        safe_name = safe_storage_name(attachment.original_filename)
        storage_path = target_dir / f"{uuid4().hex}-{safe_name}"
        storage_path.write_bytes(attachment.content)
        insert_attachment(message_id, attachment, storage_path)
    return len(attachments)


def update_account_success(
    account: MailAccount, uidvalidity: int, last_uid: int
) -> None:
    run_psql(
        """
        UPDATE app.email_accounts
        SET import_uidvalidity = :uidvalidity,
            last_imported_uid = :last_uid,
            last_imported_at = now(),
            last_import_status = 'ok',
            last_import_error = NULL,
            updated_at = now()
        WHERE id = :account_id;
        """,
        {
            "uidvalidity": str(uidvalidity),
            "last_uid": str(last_uid),
            "account_id": str(account.id),
        },
    )


def update_account_error(account: MailAccount, error: str) -> None:
    run_psql(
        """
        UPDATE app.email_accounts
        SET last_import_status = 'error',
            last_import_error = :'error',
            updated_at = now()
        WHERE id = :account_id;
        """,
        {"error": error[:500], "account_id": str(account.id)},
    )


def _safe_logout(client: imaplib.IMAP4) -> None:
    with contextlib.suppress(imaplib.IMAP4.error, OSError):  # best effort
        client.logout()


def import_account(
    account: MailAccount, env: dict[str, str], max_messages: int, dry_run: bool
) -> int:
    settings = resolve_imap_settings(account, env)
    client = connect_imap(settings)
    imported = 0
    try:
        uidvalidity = folder_uidvalidity(client, account.import_folder)
        start_uid = account.last_imported_uid + 1
        if account.import_uidvalidity is not None and account.import_uidvalidity != uidvalidity:
            LOGGER.warning(
                "UIDVALIDITY changed for %s (%s -> %s); restarting from UID 1",
                account.email_address,
                account.import_uidvalidity,
                uidvalidity,
            )
            start_uid = 1
        status, _ = client.select(_quote_folder(account.import_folder), readonly=True)
        if status != "OK":
            raise ImporterError(f"cannot select folder {account.import_folder}")
        uids = search_new_uids(client, start_uid)
        if max_messages > 0:
            uids = uids[:max_messages]
        highest_uid = account.last_imported_uid
        for uid in uids:
            highest_uid = max(highest_uid, uid)
            message = fetch_message(client, uid)
            if message is None:
                LOGGER.warning("could not fetch UID %d for %s", uid, account.email_address)
                continue
            external_id = message_external_id(message, account, uidvalidity, uid)
            if dry_run:
                LOGGER.info("[dry-run] would import UID %d (%s)", uid, external_id)
                continue
            message_id = insert_message(account, uid, external_id, message)
            if message_id is None:
                LOGGER.debug("duplicate skipped: %s", external_id)
                continue
            store_attachments(message_id, message)
            imported += 1
        if not dry_run:
            update_account_success(account, uidvalidity, highest_uid)
    finally:
        _safe_logout(client)
    LOGGER.info("imported %d new message(s) for %s", imported, account.email_address)
    return imported


def _record_failure(account: MailAccount, error: str) -> None:
    try:
        update_account_error(account, error)
    except ImporterError as state_error:  # pragma: no cover - best effort
        LOGGER.error("could not record failure for %s: %s", account.email_address, state_error)


def run_import(only_email: str | None, max_messages: int, dry_run: bool) -> int:
    env = load_mail_env(MAIL_ENV_FILE)
    accounts = load_accounts(only_email)
    if not accounts:
        LOGGER.info("no active IMAP mail accounts configured")
        return 0
    total = 0
    failures = 0
    for account in accounts:
        try:
            total += import_account(account, env, max_messages, dry_run)
        except (ImporterError, imaplib.IMAP4.error, OSError, ssl.SSLError) as error:
            failures += 1
            LOGGER.error("import failed for %s: %s", account.email_address, error)
            if not dry_run:
                _record_failure(account, str(error))
    LOGGER.info(
        "import finished: %d message(s) across %d account(s), %d failure(s)",
        total,
        len(accounts),
        failures,
    )
    return failures


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hetzner-only IMAP to PostgreSQL mail importer."
    )
    parser.add_argument(
        "--once", action="store_true", help="Run a single import pass (default behavior)."
    )
    parser.add_argument(
        "--account", default=None, help="Limit the run to a single mailbox email address."
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=DEFAULT_MAX_MESSAGES,
        help="Maximum messages to import per mailbox per run (0 = no limit).",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Connect and report without writing to PostgreSQL."
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        failures = run_import(args.account, args.max_messages, args.dry_run)
    except ImporterError as error:
        LOGGER.error("import aborted: %s", error)
        return 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
