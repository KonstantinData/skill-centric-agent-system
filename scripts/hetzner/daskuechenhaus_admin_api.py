#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import string
import subprocess
import traceback
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from email.parser import BytesParser
from email.policy import default as email_policy
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4
from zoneinfo import ZoneInfo

DATABASE = os.environ.get("DKH_ADMIN_DATABASE", "tenant_daskuechenhaus")
HOST = os.environ.get("DKH_ADMIN_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("DKH_ADMIN_API_PORT", "8715"))
TOKEN_FILE = os.environ.get("DKH_ADMIN_API_TOKEN_FILE", "/etc/daskuechenhaus/admin-api-token")
UPLOAD_ROOT = Path(os.environ.get("DKH_ADMIN_UPLOAD_ROOT", "/var/lib/daskuechenhaus/uploads"))
OBJECT_STORAGE_BUCKET = os.environ.get("DKH_OBJECT_STORAGE_BUCKET", "dkh-crm-documents").strip()
OBJECT_STORAGE_ENDPOINT = os.environ.get(
    "DKH_OBJECT_STORAGE_ENDPOINT",
    "https://fsn1.your-objectstorage.com",
).strip().rstrip("/")
OBJECT_STORAGE_REGION = os.environ.get("DKH_OBJECT_STORAGE_REGION", "fsn1").strip()
OBJECT_STORAGE_ACCESS_KEY_ID = os.environ.get("DKH_OBJECT_STORAGE_ACCESS_KEY_ID", "").strip()
OBJECT_STORAGE_SECRET_ACCESS_KEY = os.environ.get(
    "DKH_OBJECT_STORAGE_SECRET_ACCESS_KEY",
    "",
).strip()
ALLOWED_EMAILS = {
    email.strip().lower()
    for email in os.environ.get(
        "DKH_ADMIN_ALLOWED_EMAILS",
        "k.milonas@schober-daskuechenhaus.de",
    ).split(",")
    if email.strip()
}

ALLOWED_TASK_ATTACHMENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

ALLOWED_TASK_ATTACHMENT_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

ALLOWED_DOCUMENT_FILE_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip",
    "application/x-zip-compressed",
    "application/octet-stream",
}

ALLOWED_DOCUMENT_FILE_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".prjz": "application/zip",
}

NUMBER_ALPHABET = string.ascii_uppercase + string.digits
CARAT_ORDER_NUMBER_PATTERN = re.compile(r"^[A-Za-z0-9]{1,5}-[A-Za-z0-9]{1,3}$")

DOCUMENT_REGISTERS = {
    "anfrage",
    "beratung",
    "planung",
    "angebot_auftrag",
    "abwicklung",
    "rechnung_abschluss",
    "kommunikation",
}

DOCUMENT_CATEGORIES = {
    "from_customer",
    "measurement",
    "planning",
    "offer",
    "order",
    "order_processing",
    "delivery_installation",
    "complaint_service",
    "invoice",
    "customer_document",
    "drawing_plan",
    "offer_order",
    "invoice_closure",
}

DOCUMENT_TYPES = {
    "offer",
    "measurement",
    "order_confirmation",
    "delivery_note",
    "invoice",
    "plan",
    "photo",
    "contract",
    "email_attachment",
    "customer_document",
    "drawing_plan",
    "offer_order",
    "invoice_closure",
    "carat_project",
    "other",
}

CARAT_PRJZ_PARSER_VERSION = "carat-prjz-v1"

CUSTOMER_EXPORT_SECTION_CODE = "customer_export"
CUSTOMER_EXPORT_CASE_REGISTERS = [
    ("anfrage", "Anfrage", "01_Anfrage"),
    ("beratung", "Beratung", "02_Beratung"),
    ("planung", "Planung", "03_Planung"),
    ("angebot_auftrag", "Angebot / Auftrag", "04_Angebot_Auftrag"),
    ("abwicklung", "Abwicklung", "05_Abwicklung"),
    ("rechnung_abschluss", "Rechnung / Abschluss", "06_Rechnung_Abschluss"),
    ("kommunikation", "Kommunikation", "07_Kommunikation"),
    ("dokumente", "Dokumente", "08_Dokumente"),
]
CUSTOMER_EXPORT_CASE_FOLDERS = [
    folder for _register_code, _label, folder in CUSTOMER_EXPORT_CASE_REGISTERS
]
CUSTOMER_EXPORT_REGISTER_FOLDERS = {
    register_code: folder for register_code, _label, folder in CUSTOMER_EXPORT_CASE_REGISTERS
}
CUSTOMER_EXPORT_REGISTER_LABELS = {
    register_code: label for register_code, label, _folder in CUSTOMER_EXPORT_CASE_REGISTERS
}
CUSTOMER_EXPORT_DOCUMENT_FOLDERS = [
    "vom_Kunden",
    "Aufmass",
    "Planung",
    "Angebot",
    "Auftrag",
    "Bestellabwicklung",
    "Lieferung_Montage",
    "Reklamation_Kundendienst",
    "Rechnung",
]
CUSTOMER_EXPORT_DOCUMENT_CATEGORY_FOLDERS = {
    "from_customer": "vom_Kunden",
    "measurement": "Aufmass",
    "planning": "Planung",
    "offer": "Angebot",
    "order": "Auftrag",
    "order_processing": "Bestellabwicklung",
    "delivery_installation": "Lieferung_Montage",
    "complaint_service": "Reklamation_Kundendienst",
    "invoice": "Rechnung",
}

DOCUMENT_STATUSES = {
    "draft",
    "received",
    "in_review",
    "approved",
    "sent_to_customer",
    "confirmed_by_customer",
    "replaced",
    "archived",
}

DOCUMENT_CATEGORY_REGISTERS = {
    "from_customer": "anfrage",
    "measurement": "planung",
    "planning": "planung",
    "offer": "angebot_auftrag",
    "order": "angebot_auftrag",
    "order_processing": "abwicklung",
    "complaint_service": "kommunikation",
    "delivery_installation": "abwicklung",
    "invoice": "rechnung_abschluss",
}


@dataclass(frozen=True)
class FileUpload:
    field_name: str
    filename: str
    content_type: str
    content: bytes


class ApiError(Exception):
    def __init__(
        self,
        status: HTTPStatus,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details or {}


def read_token() -> str:
    with open(TOKEN_FILE, encoding="utf-8") as token_file:
        return token_file.read().strip()


def object_storage_configured() -> bool:
    return all(
        [
            OBJECT_STORAGE_BUCKET,
            OBJECT_STORAGE_ENDPOINT,
            OBJECT_STORAGE_REGION,
            OBJECT_STORAGE_ACCESS_KEY_ID,
            OBJECT_STORAGE_SECRET_ACCESS_KEY,
        ]
    )


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def s3_signing_key(secret_key: str, date_stamp: str, region: str) -> bytes:
    key_date = hmac.new(
        f"AWS4{secret_key}".encode(),
        date_stamp.encode(),
        hashlib.sha256,
    ).digest()
    key_region = hmac.new(key_date, region.encode("utf-8"), hashlib.sha256).digest()
    key_service = hmac.new(key_region, b"s3", hashlib.sha256).digest()
    return hmac.new(key_service, b"aws4_request", hashlib.sha256).digest()


def object_storage_url(object_key: str) -> str:
    encoded_key = "/".join(quote(part, safe="") for part in object_key.split("/"))
    return f"{OBJECT_STORAGE_ENDPOINT}/{OBJECT_STORAGE_BUCKET}/{encoded_key}"


def object_storage_request(
    method: str,
    object_key: str,
    body: bytes = b"",
    content_type: str = "application/octet-stream",
) -> bytes:
    if not object_storage_configured():
        raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "object_storage_not_configured")

    parsed = urlparse(OBJECT_STORAGE_ENDPOINT)
    host = parsed.netloc
    now = datetime.utcnow()
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    payload_hash = sha256_hex(body)
    encoded_key = "/".join(quote(part, safe="") for part in object_key.split("/"))
    canonical_uri = f"/{OBJECT_STORAGE_BUCKET}/{encoded_key}"
    canonical_headers = (
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join(
        [
            method,
            canonical_uri,
            "",
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )
    credential_scope = f"{date_stamp}/{OBJECT_STORAGE_REGION}/s3/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            sha256_hex(canonical_request.encode("utf-8")),
        ]
    )
    signature = hmac.new(
        s3_signing_key(OBJECT_STORAGE_SECRET_ACCESS_KEY, date_stamp, OBJECT_STORAGE_REGION),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    authorization = (
        "AWS4-HMAC-SHA256 "
        f"Credential={OBJECT_STORAGE_ACCESS_KEY_ID}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    headers = {
        "Authorization": authorization,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
    }
    if method != "GET":
        headers["Content-Type"] = content_type
        headers["Content-Length"] = str(len(body))
    request = Request(
        object_storage_url(object_key),
        data=body if method != "GET" else None,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=30) as response:
            return response.read()
    except Exception as exc:
        raise ApiError(HTTPStatus.BAD_GATEWAY, "object_storage_request_failed") from exc


def psql_json(sql: str, variables: dict[str, str] | None = None) -> Any:
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
        raise ApiError(HTTPStatus.BAD_REQUEST, result.stderr.strip() or "database_error")
    text = result.stdout.strip()
    if not text:
        return None
    return json.loads(text)


def random_code(length: int) -> str:
    return "".join(secrets.choice(NUMBER_ALPHABET) for _ in range(length))


def value_exists(table: str, column: str, value: str) -> bool:
    result = psql_json(
        f"""
        SELECT jsonb_build_object(
          'exists', EXISTS (
            SELECT 1
            FROM app.{table}
            WHERE {column} = :'value'
          )
        )::text;
        """,
        {"value": value},
    )
    return bool(result and result.get("exists"))


def generate_unique_number(prefix: str, length: int, table: str, column: str) -> str:
    for _ in range(20):
        candidate = f"{prefix}{random_code(length)}"
        if not value_exists(table, column, candidate):
            return candidate
    raise ApiError(HTTPStatus.CONFLICT, "number_generation_collision")


def generate_customer_number(customer_type: str) -> str:
    prefix = "OBJ-" if customer_type == "company" else "PRV-"
    return generate_unique_number(prefix, 6, "customers", "customer_number")


def generate_case_number() -> str:
    return generate_unique_number("V-", 8, "customer_cases", "case_number")


def normalize_carat_order_number(value: Any) -> str:
    normalized = str(value or "").strip().upper()
    if normalized and not CARAT_ORDER_NUMBER_PATTERN.fullmatch(normalized):
        raise ApiError(HTTPStatus.BAD_REQUEST, "carat_order_number_invalid")
    return normalized


def normalize_supplier_name(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    return re.sub(r"\s+", " ", normalized)


def is_carat_bilddaten_position(supplier_name: Any, article_code: Any, title: Any) -> bool:
    normalized_supplier = normalize_supplier_name(supplier_name)
    normalized_title = normalize_supplier_name(title)
    normalized_article = str(article_code or "").strip()
    return normalized_supplier == "bilddaten" or (
        normalized_article == "46000000000"
        and (normalized_title == "decke" or normalized_title.startswith("wand "))
    )


def parse_decimal_or_none(value: Any) -> str | None:
    raw = str(value or "").strip().replace(",", ".")
    if not raw:
        return None
    try:
        return str(Decimal(raw))
    except InvalidOperation as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, "decimal_value_invalid") from exc


def parse_date_or_none(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, "date_value_invalid") from exc


def parse_confirmation_positions(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(str(value or "").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        while len(parts) < 7:
            parts.append("")
        (
            article_code,
            title,
            quantity,
            net_price,
            delivery_week,
            delivery_date,
            description,
        ) = parts[:7]
        rows.append(
            {
                "position_number": str(line_number),
                "article_code": article_code or None,
                "title": title or article_code or f"AB Position {line_number}",
                "quantity": parse_decimal_or_none(quantity),
                "confirmed_net_price": parse_decimal_or_none(net_price),
                "confirmed_delivery_week": delivery_week or None,
                "confirmed_delivery_date": parse_date_or_none(delivery_date),
                "description": description or None,
            }
        )
    if not rows:
        raise ApiError(HTTPStatus.BAD_REQUEST, "confirmation_positions_required")
    return rows


def decimal_from(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def normalize_article_code(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().upper())


def admin_state() -> dict[str, Any]:
    return psql_json(
        """
        SELECT jsonb_build_object(
          'users', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'id', u.id,
                'first_name', u.first_name,
                'last_name', u.last_name,
                'email', u.email,
                'phone', u.phone,
                'job_title', u.job_title,
                'department', u.department,
                'is_active', u.is_active,
                'is_admin', u.is_admin,
                'timezone', u.timezone,
                'security', jsonb_build_object(
                  'mfa_required', COALESCE(uss.mfa_required, TRUE),
                  'password_login_enabled', COALESCE(uss.password_login_enabled, FALSE),
                  'external_identity_provider',
                    COALESCE(uss.external_identity_provider, 'cloudflare_access')
                ),
                'roles', COALESCE((
                  SELECT jsonb_agg(r.code ORDER BY r.code)
                  FROM app.user_roles ur
                  JOIN app.roles r ON r.id = ur.role_id
                  WHERE ur.user_id = u.id
                ), '[]'::jsonb),
                'workdays', COALESCE((
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'weekday', uw.weekday,
                      'is_working_day', uw.is_working_day,
                      'morning_start_time', to_char(uw.morning_start_time, 'HH24:MI'),
                      'morning_end_time', to_char(uw.morning_end_time, 'HH24:MI'),
                      'afternoon_start_time', to_char(uw.afternoon_start_time, 'HH24:MI'),
                      'afternoon_end_time', to_char(uw.afternoon_end_time, 'HH24:MI')
                    )
                    ORDER BY uw.weekday
                  )
                  FROM app.user_workdays uw
                  WHERE uw.user_id = u.id
                ), '[]'::jsonb)
              )
              ORDER BY u.last_name, u.first_name, u.id
            )
            FROM app.users u
            LEFT JOIN app.user_security_settings uss ON uss.user_id = u.id
          ), '[]'::jsonb),
          'roles', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object('code', code, 'name', name)
              ORDER BY code
            )
            FROM app.roles
          ), '[]'::jsonb),
          'company_settings', COALESCE((
            SELECT to_jsonb(c) - 'created_at' - 'updated_at'
            FROM app.company_settings c
            WHERE c.id = 1
          ), '{}'::jsonb),
          'integrations', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'id', i.id,
                'code', i.code,
                'name', i.name,
                'description', i.description,
                'is_enabled', i.is_enabled,
                'connections', COALESCE((
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'id', ic.id,
                      'display_name', ic.display_name,
                      'status', ic.status,
                      'config_json', ic.config_json,
                      'secret_reference', ic.secret_reference
                    )
                    ORDER BY ic.display_name
                  )
                  FROM app.integration_connections ic
                  WHERE ic.integration_id = i.id
                ), '[]'::jsonb)
              )
              ORDER BY i.name
            )
            FROM app.integrations i
          ), '[]'::jsonb)
        )::text;
        """
    )


def current_user_context(access_email: str) -> dict[str, Any]:
    return psql_json(
        """
        WITH matched_users AS (
          SELECT u.id, u.first_name, u.last_name, u.email, u.is_admin
          FROM app.users u
          WHERE u.is_active = TRUE
            AND lower(u.email) = lower(:'access_email')
        ),
        role_admin AS (
          SELECT bool_or(r.code = 'admin') AS is_admin
          FROM matched_users mu
          JOIN app.user_roles ur ON ur.user_id = mu.id
          JOIN app.roles r ON r.id = ur.role_id
        ),
        direct_context AS (
          SELECT
            COALESCE(bool_or(mu.is_admin), FALSE)
              OR COALESCE((SELECT is_admin FROM role_admin), FALSE) AS is_admin,
            COALESCE(jsonb_agg(DISTINCT mu.id), '[]'::jsonb) AS user_ids,
            min(mu.id) AS primary_user_id,
            min(mu.first_name || ' ' || mu.last_name) AS display_name,
            min(mu.email) AS email
          FROM matched_users mu
        ),
        delegated_users AS (
          SELECT DISTINCT ud.delegator_user_id AS id
          FROM app.user_delegations ud
          JOIN matched_users mu ON mu.id = ud.delegate_user_id
          WHERE ud.is_active = TRUE
            AND now() >= ud.starts_at
            AND now() < ud.ends_at
        ),
        scoped_users AS (
          SELECT id FROM matched_users
          UNION
          SELECT id FROM delegated_users
          UNION
          SELECT u.id
          FROM app.users u, direct_context dc
          WHERE dc.is_admin = TRUE
            AND u.is_active = TRUE
        )
        SELECT jsonb_build_object(
          'primary_user_id', (SELECT primary_user_id FROM direct_context),
          'display_name', COALESCE((SELECT display_name FROM direct_context), ''),
          'email', COALESCE((SELECT email FROM direct_context), lower(:'access_email')),
          'is_admin', COALESCE((SELECT is_admin FROM direct_context), FALSE),
          'user_ids', COALESCE((SELECT user_ids FROM direct_context), '[]'::jsonb),
          'delegated_user_ids', COALESCE((
            SELECT jsonb_agg(id ORDER BY id)
            FROM delegated_users
          ), '[]'::jsonb),
          'scope_user_ids', COALESCE((
            SELECT jsonb_agg(id ORDER BY id)
            FROM scoped_users
          ), '[]'::jsonb)
        )::text;
        """,
        {"access_email": access_email},
    )


def overview_state(access_email: str) -> dict[str, Any]:
    return psql_json(
        """
        WITH context AS (
          SELECT :'context'::jsonb AS data
        ),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_tasks AS (
          SELECT DISTINCT t.*
          FROM app.tasks t
          LEFT JOIN app.task_assignments ta ON ta.task_id = t.id
          LEFT JOIN app.task_statuses ts ON ts.id = t.status_id
          WHERE ts.is_terminal = FALSE
            AND t.archived_at IS NULL
            AND t.deleted_at IS NULL
            AND (
              t.created_by_user_id IN (SELECT id FROM scope_users)
              OR ta.user_id IN (SELECT id FROM scope_users)
              OR (SELECT (data->>'is_admin')::boolean FROM context)
            )
        ),
        visible_emails AS (
          SELECT DISTINCT em.*
          FROM app.email_messages em
          LEFT JOIN app.email_case_links ecl ON ecl.email_message_id = em.id
          LEFT JOIN app.customer_cases cc ON cc.id = ecl.customer_case_id
          WHERE
            em.archived_at IS NULL
            AND em.deleted_at IS NULL
            AND (
            (SELECT (data->>'is_admin')::boolean FROM context)
            OR em.assigned_user_id IS NULL
            OR em.assigned_user_id IN (SELECT id FROM scope_users)
            OR cc.owner_user_id IN (SELECT id FROM scope_users)
            )
        )
        SELECT jsonb_build_object(
          'current_user', (SELECT data FROM context),
          'users', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'id', u.id,
                'first_name', u.first_name,
                'last_name', u.last_name,
                'email', u.email,
                'roles', COALESCE((
                  SELECT jsonb_agg(r.code ORDER BY r.code)
                  FROM app.user_roles ur
                  JOIN app.roles r ON r.id = ur.role_id
                  WHERE ur.user_id = u.id
                ), '[]'::jsonb)
              )
              ORDER BY u.last_name, u.first_name, u.id
            )
            FROM app.users u
            WHERE u.is_active = TRUE
          ), '[]'::jsonb),
          'task_statuses', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object('code', code, 'name', name, 'is_terminal', is_terminal)
              ORDER BY sort_order
            )
            FROM app.task_statuses
          ), '[]'::jsonb),
          'customer_cases', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'id', cc.id,
                'case_number', cc.case_number,
                'customer_display_name', cc.customer_display_name,
                'customer_number', c.customer_number,
                'customer_email', c.primary_email,
                'status_phase', COALESCE(cc.status_phase_id, cc.status_phase)
              )
              ORDER BY cc.updated_at DESC, cc.customer_display_name
            )
            FROM app.customer_cases cc
            LEFT JOIN app.customers c ON c.id = cc.customer_id
            WHERE cc.is_active = TRUE
              AND (
                (SELECT (data->>'is_admin')::boolean FROM context)
                OR cc.owner_user_id IN (SELECT id FROM scope_users)
                OR EXISTS (
                  SELECT 1
                  FROM app.tasks t
                  JOIN app.task_assignments ta ON ta.task_id = t.id
                  WHERE t.related_case_id = cc.id
                    AND ta.user_id IN (SELECT id FROM scope_users)
                )
              )
            LIMIT 150
          ), '[]'::jsonb),
          'tasks', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'id', t.id,
                'title', t.title,
                'description', t.description,
                'status', ts.code,
                'status_name', ts.name,
                'priority', t.priority,
                'due_at',
                  to_char(t.due_at AT TIME ZONE 'Europe/Berlin', 'YYYY-MM-DD HH24:MI'),
                'reminder_at',
                  to_char(
                    t.reminder_at AT TIME ZONE 'Europe/Berlin',
                    'YYYY-MM-DD HH24:MI'
                  ),
                'reminder_email_enabled', t.reminder_email_enabled,
                'reminder_overview_enabled', t.reminder_overview_enabled,
                'case', CASE
                  WHEN cc.id IS NULL THEN NULL
                  ELSE jsonb_build_object(
                    'id', cc.id,
                    'case_number', cc.case_number,
                    'customer_display_name', cc.customer_display_name,
                    'status_phase', cc.status_phase
                  )
                END,
                'assigned_users', COALESCE((
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'id', u.id,
                      'name', u.first_name || ' ' || u.last_name
                    )
                    ORDER BY u.last_name, u.first_name, u.id
                  )
                  FROM app.task_assignments ta
                  JOIN app.users u ON u.id = ta.user_id
                  WHERE ta.task_id = t.id
                ), '[]'::jsonb),
                'attachment_count', (
                  SELECT count(*) FROM app.task_attachments tatt WHERE tatt.task_id = t.id
                )
              )
              ORDER BY t.due_at NULLS LAST, t.created_at DESC
            )
            FROM visible_tasks t
            JOIN app.task_statuses ts ON ts.id = t.status_id
            LEFT JOIN app.customer_cases cc ON cc.id = t.related_case_id
          ), '[]'::jsonb),
          'emails', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'id', em.id,
                'subject', em.subject,
                'snippet', em.snippet,
                'direction', em.direction,
                'received_at',
                  to_char(
                    em.received_at AT TIME ZONE 'Europe/Berlin',
                    'YYYY-MM-DD HH24:MI'
                  ),
                'is_unassigned', em.is_unassigned,
                'assigned_user_id', em.assigned_user_id,
                'participants', COALESCE((
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'type', ep.participant_type,
                      'display_name', ep.display_name,
                      'email_address', ep.email_address
                    )
                    ORDER BY ep.id
                  )
                  FROM app.email_participants ep
                  WHERE ep.email_message_id = em.id
                ), '[]'::jsonb),
                'cases', COALESCE((
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'id', cc.id,
                      'case_number', cc.case_number,
                      'customer_display_name', cc.customer_display_name
                    )
                    ORDER BY cc.customer_display_name
                  )
                  FROM app.email_case_links ecl
                  JOIN app.customer_cases cc ON cc.id = ecl.customer_case_id
                  WHERE ecl.email_message_id = em.id
                ), '[]'::jsonb),
                'suggestions', COALESCE((
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'id', eas.id,
                      'confidence', eas.confidence,
                      'reason', eas.reason,
                      'case', CASE
                        WHEN cc.id IS NULL THEN NULL
                        ELSE jsonb_build_object(
                          'id', cc.id,
                          'case_number', cc.case_number,
                          'customer_display_name', cc.customer_display_name
                        )
                      END
                    )
                    ORDER BY eas.confidence DESC, eas.created_at DESC
                  )
                  FROM app.email_assignment_suggestions eas
                  LEFT JOIN app.customer_cases cc ON cc.id = eas.suggested_case_id
                  WHERE eas.email_message_id = em.id
                    AND eas.status = 'pending'
                ), '[]'::jsonb)
              )
              ORDER BY em.is_unassigned DESC, em.received_at DESC NULLS LAST, em.created_at DESC
            )
            FROM visible_emails em
            LIMIT 20
          ), '[]'::jsonb),
          'appointments', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'id', a.id,
                'title', a.title,
                'starts_at',
                  to_char(
                    a.starts_at AT TIME ZONE 'Europe/Berlin',
                    'YYYY-MM-DD HH24:MI'
                  ),
                'location', a.location,
                'case', CASE
                  WHEN cc.id IS NULL THEN NULL
                  ELSE jsonb_build_object(
                    'id', cc.id,
                    'customer_display_name', cc.customer_display_name
                  )
                END
              )
              ORDER BY a.starts_at
            )
            FROM app.appointments a
            LEFT JOIN app.customer_cases cc ON cc.id = a.related_case_id
            WHERE a.starts_at >= now()
              AND (
                (SELECT (data->>'is_admin')::boolean FROM context)
                OR a.owner_user_id IN (SELECT id FROM scope_users)
              )
            LIMIT 10
          ), '[]'::jsonb),
          'news_items', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'id', n.id,
                'title', n.title,
                'body', n.body,
                'category', n.category,
                'starts_on', n.starts_on,
                'ends_on', n.ends_on
              )
              ORDER BY n.starts_on DESC NULLS LAST, n.created_at DESC
            )
            FROM app.news_items n
            WHERE n.visibility = 'team'
              OR (
                (SELECT (data->>'is_admin')::boolean FROM context)
                AND n.visibility = 'admin'
              )
            LIMIT 10
          ), '[]'::jsonb),
          'goal_events', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'id', ge.id,
                'goal', g.title,
                'note', ge.note,
                'achieved_at',
                  to_char(
                    ge.achieved_at AT TIME ZONE 'Europe/Berlin',
                    'YYYY-MM-DD HH24:MI'
                  ),
                'achieved_by', u.first_name || ' ' || u.last_name
              )
              ORDER BY ge.achieved_at DESC
            )
            FROM app.goal_events ge
            JOIN app.goals g ON g.id = ge.goal_id
            LEFT JOIN app.users u ON u.id = ge.achieved_by_user_id
            WHERE
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR ge.achieved_by_user_id IN (SELECT id FROM scope_users)
            LIMIT 10
          ), '[]'::jsonb),
          'communication_events', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'id', ce.id,
                'event_type', ce.event_type,
                'title', ce.title,
                'body', ce.body,
                'occurred_at',
                  to_char(
                    ce.occurred_at AT TIME ZONE 'Europe/Berlin',
                    'YYYY-MM-DD HH24:MI'
                  ),
                'customer_case', CASE
                  WHEN cc.id IS NULL THEN NULL
                  ELSE jsonb_build_object(
                    'id', cc.id,
                    'case_number', cc.case_number,
                    'customer_display_name', cc.customer_display_name
                  )
                END,
                'actor', actor.first_name || ' ' || actor.last_name
              )
              ORDER BY ce.occurred_at DESC
            )
            FROM app.communication_events ce
            LEFT JOIN app.customer_cases cc ON cc.id = ce.customer_case_id
            LEFT JOIN app.users actor ON actor.id = ce.actor_user_id
            WHERE
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR ce.actor_user_id IN (SELECT id FROM scope_users)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
            LIMIT 12
          ), '[]'::jsonb),
          'delegations', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'id', ud.id,
                'represented_user', delegator.first_name || ' ' || delegator.last_name,
                'starts_at',
                  to_char(
                    ud.starts_at AT TIME ZONE 'Europe/Berlin',
                    'YYYY-MM-DD HH24:MI'
                  ),
                'ends_at',
                  to_char(
                    ud.ends_at AT TIME ZONE 'Europe/Berlin',
                    'YYYY-MM-DD HH24:MI'
                  ),
                'scope', ud.scope
              )
              ORDER BY ud.ends_at
            )
            FROM app.user_delegations ud
            JOIN app.users delegate ON delegate.id = ud.delegate_user_id
            JOIN app.users delegator ON delegator.id = ud.delegator_user_id
            WHERE ud.is_active = TRUE
              AND now() >= ud.starts_at
              AND now() < ud.ends_at
              AND delegate.id IN (
                SELECT jsonb_array_elements_text(data->'user_ids')::bigint FROM context
              )
          ), '[]'::jsonb)
        )::text;
        """,
        {"context": json.dumps(current_user_context(access_email))},
    )


def normalize_bool(value: Any) -> str:
    return "true" if str(value).lower() in {"1", "true", "on", "yes"} else "false"


def normalize_phone_number(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    cleaned = re.sub(r"[^\d+]", "", raw)
    if cleaned.startswith("00"):
        cleaned = f"+{cleaned[2:]}"
    if cleaned.startswith("+"):
        digits = re.sub(r"\D", "", cleaned[1:])
        return f"+{digits}" if digits else ""
    digits = re.sub(r"\D", "", cleaned)
    if not digits:
        return ""
    if digits.startswith("0"):
        return f"+49{digits[1:]}"
    return f"+{digits}"


def request_payload(handler: BaseHTTPRequestHandler) -> tuple[dict[str, Any], list[FileUpload]]:
    length = int(handler.headers.get("content-length", "0"))
    raw_body = handler.rfile.read(length) if length else b""
    content_type = handler.headers.get("content-type", "")
    if "application/json" in content_type:
        return json.loads(raw_body.decode("utf-8") or "{}"), []
    if "multipart/form-data" in content_type:
        message = BytesParser(policy=email_policy).parsebytes(
            b"Content-Type: "
            + content_type.encode("utf-8")
            + b"\r\nMIME-Version: 1.0\r\n\r\n"
            + raw_body
        )
        fields: dict[str, Any] = {}
        files: list[FileUpload] = []
        for part in message.iter_parts():
            if part.get_content_disposition() != "form-data":
                continue
            field_name = part.get_param("name", header="content-disposition")
            if not field_name:
                continue
            filename = part.get_filename()
            content = part.get_payload(decode=True) or b""
            if filename:
                if content:
                    files.append(
                        FileUpload(
                            field_name=field_name,
                            filename=filename,
                            content_type=part.get_content_type(),
                            content=content,
                        )
                    )
                continue
            charset = part.get_content_charset() or "utf-8"
            fields[field_name] = content.decode(charset, errors="replace")
        return fields, files
    parsed = parse_qs(raw_body.decode("utf-8") if raw_body else "", keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}, []


def form_payload(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    fields, _files = request_payload(handler)
    return fields


def safe_upload_filename(filename: str) -> str:
    name = Path(filename).name
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return safe or f"upload-{uuid4().hex}"


def safe_response_content_type(content_type: str) -> str:
    value = content_type.strip()
    allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!#$&^_.+-")
    parts = value.split("/")
    if len(parts) == 2 and all(parts) and all(set(part) <= allowed_chars for part in parts):
        return value
    return "application/octet-stream"


def safe_response_filename(filename: str) -> str:
    safe_name = safe_upload_filename(filename)
    return quote(safe_name.replace("\r", "").replace("\n", ""), safe="")


def normalize_attachment_type(upload: FileUpload) -> str:
    extension = Path(upload.filename).suffix.lower()
    expected_type = ALLOWED_TASK_ATTACHMENT_EXTENSIONS.get(extension)
    if upload.content_type in ALLOWED_TASK_ATTACHMENT_TYPES:
        return upload.content_type
    if expected_type:
        return expected_type
    raise ApiError(HTTPStatus.BAD_REQUEST, "unsupported_task_attachment_type")


def normalize_document_file_type(upload: FileUpload) -> str:
    extension = Path(upload.filename).suffix.lower()
    expected_type = ALLOWED_DOCUMENT_FILE_EXTENSIONS.get(extension)
    if expected_type:
        return expected_type
    if (
        upload.content_type in ALLOWED_DOCUMENT_FILE_TYPES
        and upload.content_type != "application/octet-stream"
    ):
        return upload.content_type
    raise ApiError(HTTPStatus.BAD_REQUEST, "unsupported_document_file_type")


def first_document_upload(files: list[FileUpload]) -> FileUpload | None:
    for upload in files:
        if upload.field_name == "file":
            return upload
    return files[0] if files else None


def customer_case_document_object_key(
    customer_id: int,
    case_id: str,
    document_category: str,
    filename: str,
) -> str:
    safe_name = safe_upload_filename(filename)
    safe_category = re.sub(r"[^a-z0-9_-]+", "_", document_category.lower()).strip("_") or "document"
    return (
        f"customers/{customer_id}/cases/{case_id}/documents/"
        f"{safe_category}/{uuid4().hex}-{safe_name}"
    )


def is_carat_prjz_upload(upload: FileUpload) -> bool:
    return Path(upload.filename).suffix.lower() == ".prjz" and upload.content.startswith(b"PK")


def split_prj_line(line: str) -> list[str]:
    if line.endswith("|*"):
        line = line[:-2]
    elif line.endswith("*"):
        line = line[:-1]
    return [part.strip() for part in line.split("|")]


def prj_value_after_code(parts: list[str], code_prefix: str) -> str:
    if len(parts) < 2 or not parts[1].startswith(code_prefix):
        return ""
    value = parts[1][len(code_prefix):].strip()
    trailing = " ".join(part for part in parts[2:] if part).strip()
    return " ".join(part for part in (value, trailing) if part).strip()


def parse_decimal(value: str) -> float | None:
    normalized = value.strip().replace(",", ".")
    if not normalized:
        return None
    try:
        return float(normalized)
    except ValueError:
        return None


def parse_prjz_content(content: bytes, filename: str) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            prj_names = [
                name
                for name in archive.namelist()
                if name.lower().endswith(".prj") and not name.endswith("/")
            ]
            if not prj_names:
                raise ValueError("prj_file_missing")
            prj_name = prj_names[0]
            prj_content = archive.read(prj_name)
    except zipfile.BadZipFile as exc:
        raise ValueError("invalid_prjz_zip") from exc

    text = prj_content.decode("cp1252", errors="replace")
    lines = [line for line in text.splitlines() if line.strip()]
    parsed_lines = [split_prj_line(line) for line in lines]
    summary: dict[str, Any] = {
        "source_filename": safe_upload_filename(filename),
        "inner_filename": prj_name,
        "line_count": len(lines),
        "parser_version": CARAT_PRJZ_PARSER_VERSION,
        "carat_version": None,
        "project_number": None,
        "project_name": None,
        "customer_name": None,
        "currency": None,
        "suppliers": [],
        "positions": [],
    }

    if parsed_lines:
        first = parsed_lines[0]
        if len(first) > 2:
            summary["carat_version"] = first[2] or None
        if len(first) > 3:
            summary["project_number"] = first[3] or None

    supplier_by_suffix: dict[str, dict[str, Any]] = {}
    ignored_supplier_suffixes: set[str] = set()
    for parts in parsed_lines:
        if len(parts) < 2:
            continue
        section = parts[0]
        code = parts[1]
        if section == "001" and code == "0020" and len(parts) > 2 and parts[2]:
            summary["customer_name"] = parts[2]
            summary["project_name"] = parts[2]
        if section == "001" and code == "2150" and len(parts) > 2 and parts[2]:
            summary["currency"] = parts[2]
        if section == "002" and code.startswith("2000") and len(parts) > 2:
            name = parts[2].strip()
            if not name:
                continue
            suffix = code[4:].lstrip("0") or code[4:] or code
            if normalize_supplier_name(name) == "bilddaten":
                ignored_supplier_suffixes.add(suffix)
                continue
            supplier = {
                "code": code,
                "name": name,
                "catalog": parts[4] if len(parts) > 4 else "",
                "catalog_date": parts[5] if len(parts) > 5 else "",
                "kind": parts[6] if len(parts) > 6 else "",
            }
            summary["suppliers"].append(supplier)
            supplier_by_suffix[suffix] = supplier

    article_markers = [
        index
        for index, parts in enumerate(parsed_lines)
        if len(parts) >= 2 and parts[1] == "9999.Artikel"
    ]
    for marker_index, start in enumerate(article_markers):
        end = (
            article_markers[marker_index + 1]
            if marker_index + 1 < len(article_markers)
            else len(parsed_lines)
        )
        block = parsed_lines[start:end]
        source_line = start + 1
        position_number = ""
        article_code = ""
        title = ""
        description_parts: list[str] = []
        supplier_code = ""
        supplier_name = ""
        quantity: float | None = None
        dimensions: dict[str, Any] = {}
        ignored_position = False

        for parts in block[:80]:
            if len(parts) < 2:
                continue
            code = parts[1]
            if code.startswith("4500") and len(parts) > 2:
                position_number = parts[2].lstrip("0") or parts[2]
            if code.startswith("4510"):
                text_value = prj_value_after_code(parts, "4510")
                if text_value:
                    description_parts.append(text_value)
            if code.startswith("4512"):
                values = [parse_decimal(part) for part in parts[2:5]]
                dimension_keys = ("width", "depth", "height")
                dimensions = {
                    key: value
                    for key, value in zip(dimension_keys, values, strict=False)
                    if value not in (None, 0)
                }
            if code.startswith("4600"):
                article_code = code
                if len(parts) > 3 and parts[3]:
                    title = parts[3]
                suffix = code[4:].lstrip("0") or code[4:] or code
                if any(
                    suffix.endswith(ignored_suffix) or ignored_suffix.endswith(suffix)
                    for ignored_suffix in ignored_supplier_suffixes
                ):
                    ignored_position = True
                for known_suffix, supplier in supplier_by_suffix.items():
                    if suffix.endswith(known_suffix) or known_suffix.endswith(suffix):
                        supplier_code = supplier["code"]
                        supplier_name = supplier["name"]
                        break
            if code.startswith("4627") and len(parts) > 4:
                quantity = parse_decimal(parts[4])

        if not title and description_parts:
            title = description_parts[0][:120]
        if not title:
            continue
        if ignored_position or is_carat_bilddaten_position(supplier_name, article_code, title):
            continue
        summary["positions"].append(
            {
                "source_line": source_line,
                "position_number": position_number,
                "supplier_code": supplier_code,
                "supplier_name": supplier_name,
                "article_code": article_code,
                "title": title,
                "description": "\n".join(description_parts[:6]),
                "quantity": quantity,
                "dimensions": dimensions,
                "raw": {
                    "marker_line": lines[start],
                    "block_size": len(block),
                },
            }
        )

    return summary


def selected_roles(data: dict[str, Any]) -> list[str]:
    roles = []
    for code in ("admin", "employee", "sales"):
        if normalize_bool(data.get(f"role_{code}")) == "true":
            roles.append(code)
    return roles


def upsert_user(data: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
    payload = {
        "first_name": str(data.get("first_name", "")).strip(),
        "last_name": str(data.get("last_name", "")).strip(),
        "email": str(data.get("email", "")).strip().lower(),
        "phone": str(data.get("phone", "")).strip() or None,
        "job_title": str(data.get("job_title", "")).strip() or None,
        "department": str(data.get("department", "")).strip() or None,
        "is_active": normalize_bool(data.get("is_active")),
        "timezone": str(data.get("timezone", "Europe/Berlin")).strip() or "Europe/Berlin",
        "mfa_required": normalize_bool(data.get("mfa_required", "true")),
        "roles": selected_roles(data),
    }
    if not payload["first_name"] or not payload["last_name"] or not payload["email"]:
        raise ApiError(HTTPStatus.BAD_REQUEST, "first_name_last_name_email_required")
    if user_id is not None:
        payload["id"] = int(user_id)

    sql = """
    WITH payload AS (SELECT :'payload'::jsonb AS data),
    changed_user AS (
      INSERT INTO app.users (
        first_name, last_name, email, phone, job_title, department,
        is_active, is_admin, timezone
      )
      SELECT
        data->>'first_name',
        data->>'last_name',
        data->>'email',
        NULLIF(data->>'phone', ''),
        NULLIF(data->>'job_title', ''),
        NULLIF(data->>'department', ''),
        (data->>'is_active')::boolean,
        COALESCE((data->'roles') ? 'admin', FALSE),
        data->>'timezone'
      FROM payload
      WHERE NOT (data ? 'id')
      UNION ALL
      SELECT
        data->>'first_name',
        data->>'last_name',
        data->>'email',
        NULLIF(data->>'phone', ''),
        NULLIF(data->>'job_title', ''),
        NULLIF(data->>'department', ''),
        (data->>'is_active')::boolean,
        COALESCE((data->'roles') ? 'admin', FALSE),
        data->>'timezone'
      FROM payload
      WHERE FALSE
      RETURNING id
    ),
    updated_user AS (
      UPDATE app.users u
      SET
        first_name = data->>'first_name',
        last_name = data->>'last_name',
        email = data->>'email',
        phone = NULLIF(data->>'phone', ''),
        job_title = NULLIF(data->>'job_title', ''),
        department = NULLIF(data->>'department', ''),
        is_active = (data->>'is_active')::boolean,
        is_admin = COALESCE((data->'roles') ? 'admin', FALSE),
        timezone = data->>'timezone'
      FROM payload
      WHERE data ? 'id'
        AND u.id = (data->>'id')::bigint
      RETURNING u.id
    ),
    target_user AS (
      SELECT id FROM changed_user
      UNION ALL
      SELECT id FROM updated_user
    ),
    security AS (
      INSERT INTO app.user_security_settings (
        user_id, external_identity_provider, password_login_enabled, mfa_required
      )
      SELECT id, 'cloudflare_access', FALSE, (data->>'mfa_required')::boolean
      FROM target_user, payload
      ON CONFLICT (user_id) DO UPDATE
      SET
        external_identity_provider = EXCLUDED.external_identity_provider,
        password_login_enabled = FALSE,
        mfa_required = EXCLUDED.mfa_required
      RETURNING user_id
    ),
    preferences AS (
      INSERT INTO app.user_preferences (user_id, timezone)
      SELECT id, data->>'timezone'
      FROM target_user, payload
      ON CONFLICT (user_id) DO UPDATE
      SET timezone = EXCLUDED.timezone
      RETURNING user_id
    ),
    removed_roles AS (
      DELETE FROM app.user_roles
      WHERE user_id IN (SELECT id FROM target_user)
      RETURNING user_id
    ),
    inserted_roles AS (
      INSERT INTO app.user_roles (user_id, role_id)
      SELECT target_user.id, roles.id
      FROM target_user
      CROSS JOIN payload
      JOIN app.roles roles ON roles.code IN (
        SELECT jsonb_array_elements_text(data->'roles')
      )
      ON CONFLICT DO NOTHING
      RETURNING user_id
    )
    SELECT jsonb_build_object('ok', TRUE, 'user_id', (SELECT id FROM target_user))::text;
    """
    return psql_json(sql, {"payload": json.dumps(payload)})


def save_roles(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    payload = {"id": int(user_id), "roles": selected_roles(data)}
    return psql_json(
        """
        BEGIN;
        WITH payload AS (SELECT :'payload'::jsonb AS data)
        DELETE FROM app.user_roles
        USING payload
        WHERE user_id = (data->>'id')::bigint;
        WITH payload AS (SELECT :'payload'::jsonb AS data)
        INSERT INTO app.user_roles (user_id, role_id)
        SELECT (data->>'id')::bigint, r.id
        FROM payload
        JOIN app.roles r ON r.code IN (
          SELECT jsonb_array_elements_text(data->'roles')
        )
        ON CONFLICT DO NOTHING;
        WITH payload AS (SELECT :'payload'::jsonb AS data)
        UPDATE app.users u
        SET is_admin = COALESCE((data->'roles') ? 'admin', FALSE)
        FROM payload
        WHERE u.id = (data->>'id')::bigint;
        COMMIT;
        SELECT jsonb_build_object('ok', TRUE)::text;
        """,
        {"payload": json.dumps(payload)},
    )


def save_workdays(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    days = []
    for weekday in range(1, 7):
        active = normalize_bool(data.get(f"is_working_day_{weekday}")) == "true"
        days.append(
            {
                "weekday": weekday,
                "is_working_day": active,
                "morning_start_time": data.get(f"morning_start_time_{weekday}") if active else "",
                "morning_end_time": data.get(f"morning_end_time_{weekday}") if active else "",
                "afternoon_start_time": (
                    data.get(f"afternoon_start_time_{weekday}") if active else ""
                ),
                "afternoon_end_time": data.get(f"afternoon_end_time_{weekday}") if active else "",
            }
        )
    payload = {
        "id": int(user_id),
        "timezone": data.get("preference_timezone", "Europe/Berlin"),
        "days": days,
    }
    return psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        days AS (
          SELECT *
          FROM jsonb_to_recordset((SELECT data->'days' FROM payload)) AS d(
            weekday smallint,
            is_working_day boolean,
            morning_start_time text,
            morning_end_time text,
            afternoon_start_time text,
            afternoon_end_time text
          )
        ),
        upserted AS (
          INSERT INTO app.user_workdays (
            user_id, weekday, is_working_day, morning_start_time, morning_end_time,
            afternoon_start_time, afternoon_end_time
          )
          SELECT
            (SELECT (data->>'id')::bigint FROM payload),
            weekday,
            is_working_day,
            NULLIF(morning_start_time, '')::time,
            NULLIF(morning_end_time, '')::time,
            NULLIF(afternoon_start_time, '')::time,
            NULLIF(afternoon_end_time, '')::time
          FROM days
          ON CONFLICT (user_id, weekday) DO UPDATE
          SET
            is_working_day = EXCLUDED.is_working_day,
            morning_start_time = EXCLUDED.morning_start_time,
            morning_end_time = EXCLUDED.morning_end_time,
            afternoon_start_time = EXCLUDED.afternoon_start_time,
            afternoon_end_time = EXCLUDED.afternoon_end_time
          RETURNING user_id
        )
        INSERT INTO app.user_preferences (user_id, timezone)
        SELECT (data->>'id')::bigint, data->>'timezone'
        FROM payload
        ON CONFLICT (user_id) DO UPDATE
        SET timezone = EXCLUDED.timezone;
        SELECT jsonb_build_object('ok', TRUE)::text;
        """,
        {"payload": json.dumps(payload)},
    )


def save_company(data: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "company_name": data.get("company_name", ""),
        "legal_name": data.get("legal_name", ""),
        "street": data.get("street", ""),
        "postal_code": data.get("postal_code", ""),
        "city": data.get("city", ""),
        "country": data.get("country", "DE"),
        "phone": data.get("phone", ""),
        "fax": data.get("fax", ""),
        "email": data.get("email", ""),
        "website": data.get("website", ""),
        "vat_id": data.get("vat_id", ""),
        "commercial_register": data.get("commercial_register", ""),
        "managing_director": data.get("managing_director", ""),
    }
    return psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data)
        INSERT INTO app.company_settings (
          id, company_name, legal_name, street, postal_code, city, country, phone,
          fax, email, website, vat_id, commercial_register, managing_director
        )
        SELECT
          1,
          data->>'company_name',
          data->>'legal_name',
          NULLIF(data->>'street', ''),
          NULLIF(data->>'postal_code', ''),
          NULLIF(data->>'city', ''),
          COALESCE(NULLIF(data->>'country', ''), 'DE'),
          NULLIF(data->>'phone', ''),
          NULLIF(data->>'fax', ''),
          NULLIF(data->>'email', ''),
          NULLIF(data->>'website', ''),
          NULLIF(data->>'vat_id', ''),
          NULLIF(data->>'commercial_register', ''),
          NULLIF(data->>'managing_director', '')
        FROM payload
        ON CONFLICT (id) DO UPDATE
        SET
          company_name = EXCLUDED.company_name,
          legal_name = EXCLUDED.legal_name,
          street = EXCLUDED.street,
          postal_code = EXCLUDED.postal_code,
          city = EXCLUDED.city,
          country = EXCLUDED.country,
          phone = EXCLUDED.phone,
          fax = EXCLUDED.fax,
          email = EXCLUDED.email,
          website = EXCLUDED.website,
          vat_id = EXCLUDED.vat_id,
          commercial_register = EXCLUDED.commercial_register,
          managing_director = EXCLUDED.managing_director;
        SELECT jsonb_build_object('ok', TRUE)::text;
        """,
        {"payload": json.dumps(payload)},
    )


def save_integration(data: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "code": str(data.get("integration_code", "")).strip().lower().replace("-", "_"),
        "name": str(data.get("integration_name", "")).strip(),
        "display_name": str(data.get("display_name", "")).strip(),
        "status": data.get("status", "pending"),
        "secret_reference": data.get("secret_reference", ""),
        "config_json": data.get("config_json", "{}") or "{}",
        "is_enabled": normalize_bool(data.get("is_enabled")),
    }
    return psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        integration AS (
          INSERT INTO app.integrations (code, name, is_enabled)
          SELECT data->>'code', data->>'name', (data->>'is_enabled')::boolean
          FROM payload
          ON CONFLICT (code) DO UPDATE
          SET name = EXCLUDED.name, is_enabled = EXCLUDED.is_enabled
          RETURNING id
        )
        INSERT INTO app.integration_connections (
          integration_id, display_name, status, config_json, secret_reference
        )
        SELECT
          id,
          data->>'display_name',
          data->>'status',
          (data->>'config_json')::jsonb,
          NULLIF(data->>'secret_reference', '')
        FROM integration, payload
        ON CONFLICT DO NOTHING;
        SELECT jsonb_build_object('ok', TRUE)::text;
        """,
        {"payload": json.dumps(payload)},
    )


def require_primary_user(access_email: str) -> dict[str, Any]:
    context = current_user_context(access_email)
    if not context.get("primary_user_id"):
        raise ApiError(HTTPStatus.FORBIDDEN, "user_not_registered")
    return context


def customer_display_name(data: dict[str, Any]) -> str:
    customer_type = str(data.get("customer_type", "private")).strip() or "private"
    if customer_type == "company":
        display_name = str(data.get("company_name", "")).strip()
    else:
        display_name = " ".join(
            part
            for part in [
                str(data.get("first_name", "")).strip(),
                str(data.get("last_name", "")).strip(),
            ]
            if part
        )
    return (
        display_name
        or str(data.get("company_name", "")).strip()
        or str(data.get("primary_email", "")).strip().lower()
    )


def customers_state(access_email: str) -> dict[str, Any]:
    context = require_primary_user(access_email)
    state = psql_json(
        """
        WITH context AS (
          SELECT :'context'::jsonb AS data
        ),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_customers AS (
          SELECT DISTINCT c.*
          FROM app.customers c
          LEFT JOIN app.customer_cases cc ON cc.customer_id = c.id
          WHERE c.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
            )
        ),
        assignable_users AS (
          SELECT u.*
          FROM app.users u
          WHERE u.is_active = TRUE
        )
        SELECT jsonb_build_object(
          'current_user', (SELECT data FROM context),
          'users', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'id', u.id,
                'first_name', u.first_name,
                'last_name', u.last_name,
                'email', u.email,
                'roles', COALESCE((
                  SELECT jsonb_agg(r.code ORDER BY r.code)
                  FROM app.user_roles ur
                  JOIN app.roles r ON r.id = ur.role_id
                  WHERE ur.user_id = u.id
                ), '[]'::jsonb)
              )
              ORDER BY u.last_name, u.first_name, u.id
            )
            FROM assignable_users u
          ), '[]'::jsonb),
          'status_phases', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'phase', phase,
                'name', name,
                'is_terminal', is_terminal
              )
              ORDER BY sort_order
            )
            FROM app.customer_case_status_phases
          ), '[]'::jsonb),
          'customers', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'id', c.id,
                'customer_number', c.customer_number,
                'customer_type', c.customer_type,
                'display_name', c.display_name,
                'salutation', c.salutation,
                'title', c.title,
                'first_name', c.first_name,
                'last_name', c.last_name,
                'company_name', c.company_name,
                'primary_email', c.primary_email,
                'primary_phone', c.primary_phone,
                'primary_mobile', c.primary_mobile,
                'preferred_contact_channel', c.preferred_contact_channel,
                'legal_form', c.legal_form,
                'vat_id', c.vat_id,
                'tax_number', c.tax_number,
                'registry_court', c.registry_court,
                'registry_number', c.registry_number,
                'object_customer_label', c.object_customer_label,
                'tax_treatment', c.tax_treatment,
                'tax_treatment_note', c.tax_treatment_note,
                'has_custom_vat', c.has_custom_vat,
                'custom_vat_rate', c.custom_vat_rate,
                'custom_vat_rate_label', c.custom_vat_rate_label,
                'country', c.country,
                'notes', c.notes,
                'owner_user_id', c.owner_user_id,
                'file_sections', COALESCE((
                  SELECT jsonb_object_agg(cfs.section_code, cfs.payload_json)
                  FROM app.customer_file_sections cfs
                  WHERE cfs.customer_id = c.id
                ), '{}'::jsonb),
                'updated_at',
                  to_char(
                    c.updated_at AT TIME ZONE 'Europe/Berlin',
                    'YYYY-MM-DD HH24:MI'
                  ),
                'case_count', (
                  SELECT count(*)
                  FROM app.customer_cases cc
                  WHERE cc.customer_id = c.id
                    AND cc.is_active = TRUE
                ),
                'address', (
                  SELECT jsonb_build_object(
                    'street', ca.street,
                    'house_number', ca.house_number,
                    'address_extra', ca.address_extra,
                    'postal_code', ca.postal_code,
                    'city', ca.city,
                    'country', ca.country
                  )
                  FROM app.customer_addresses ca
                  WHERE ca.customer_id = c.id
                  ORDER BY ca.is_primary DESC, ca.id
                  LIMIT 1
                )
              )
              ORDER BY c.updated_at DESC, c.id DESC
            )
            FROM visible_customers c
          ), '[]'::jsonb),
          'customer_cases', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'id', cc.id,
                'customer_id', cc.customer_id,
                'case_number', cc.case_number,
                'carat_order_number', cc.carat_order_number,
                'case_title', cc.case_title,
                'case_status', cc.case_status,
                'customer_display_name', cc.customer_display_name,
                'customer_number', c.customer_number,
                'customer_email', c.primary_email,
                'status_phase', COALESCE(cc.status_phase_id, cc.status_phase),
                'status_phase_name', csp.name,
                'notes', COALESCE((
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'id', n.id,
                      'customer_case_id', n.customer_case_id,
                      'note_type', n.note_type,
                      'body', n.body,
                      'created_by', COALESCE(u.first_name || ' ' || u.last_name, u.email),
                      'created_at',
                        to_char(
                          n.created_at AT TIME ZONE 'Europe/Berlin',
                          'YYYY-MM-DD HH24:MI'
                        )
                    )
                    ORDER BY n.created_at DESC, n.id DESC
                  )
                  FROM app.customer_case_notes n
                  LEFT JOIN app.users u ON u.id = n.created_by_user_id
                  WHERE n.customer_case_id = cc.id
                ), '[]'::jsonb),
                'sections', COALESCE((
                  SELECT jsonb_object_agg(ccs.section_code, ccs.payload_json)
                  FROM app.customer_case_sections ccs
                  WHERE ccs.customer_case_id = cc.id
                ), '{}'::jsonb),
                'documents', COALESCE((
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'id', d.id,
                      'customer_case_id', d.customer_case_id,
                      'register_code', d.register_code,
                      'document_category', d.document_category,
                      'document_type', d.document_type,
                      'document_status', d.document_status,
                      'title', COALESCE(d.title, d.original_filename),
                      'note', d.note,
                      'version_label', d.version_label,
                      'is_current_version', d.is_current_version,
                      'replaces_document_id', d.replaces_document_id,
                      'has_file', d.storage_path IS NOT NULL OR d.object_storage_key IS NOT NULL,
                      'storage_backend', d.storage_backend,
                      'content_sha256', d.content_sha256,
                      'original_filename', d.original_filename,
                      'content_type', d.content_type,
                      'file_size_bytes', d.file_size_bytes,
                      'created_by', COALESCE(u.first_name || ' ' || u.last_name, u.email),
                      'created_at',
                        to_char(
                          d.created_at AT TIME ZONE 'Europe/Berlin',
                          'YYYY-MM-DD HH24:MI'
                        ),
                      'updated_at',
                        to_char(
                          d.updated_at AT TIME ZONE 'Europe/Berlin',
                          'YYYY-MM-DD HH24:MI'
                        )
                    )
                    ORDER BY d.is_current_version DESC, d.created_at DESC, d.id DESC
                  )
                  FROM app.customer_case_documents d
                  LEFT JOIN app.users u ON u.id = d.uploaded_by_user_id
                  WHERE d.customer_case_id = cc.id
                    AND d.document_status <> 'archived'
                ), '[]'::jsonb),
                'carat_imports', COALESCE((
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'id', ci.id,
                      'customer_case_id', ci.customer_case_id,
                      'document_id', ci.document_id,
                      'parser_version', ci.parser_version,
                      'source_filename', ci.source_filename,
                      'carat_version', ci.carat_version,
                      'project_number', ci.project_number,
                      'project_name', ci.project_name,
                      'customer_name', ci.customer_name,
                      'currency', ci.currency,
                      'supplier_count', ci.supplier_count,
                      'position_count', ci.position_count,
                      'status', ci.status,
                      'summary', ci.summary_json,
                      'created_at',
                        to_char(
                          ci.created_at AT TIME ZONE 'Europe/Berlin',
                          'YYYY-MM-DD HH24:MI'
                        ),
                      'positions', COALESCE((
                        SELECT jsonb_agg(
                          jsonb_build_object(
                            'id', cip.id,
                            'source_line', cip.source_line,
                            'position_number', cip.position_number,
                            'supplier_code', cip.supplier_code,
                            'supplier_name', cip.supplier_name,
                            'article_code', cip.article_code,
                            'title', cip.title,
                            'description', cip.description,
                            'quantity', cip.quantity,
                            'dimensions', cip.dimensions_json,
                            'selection_status', cip.selection_status,
                            'selected_at',
                              CASE
                                WHEN cip.selected_at IS NULL THEN NULL
                                ELSE to_char(
                                  cip.selected_at AT TIME ZONE 'Europe/Berlin',
                                  'YYYY-MM-DD HH24:MI'
                                )
                              END
                          )
                          ORDER BY
                            COALESCE(cip.supplier_name, ''),
                            CASE
                              WHEN cip.position_number ~ '^[0-9]+$'
                                THEN cip.position_number::integer
                              ELSE NULL
                            END NULLS LAST,
                            cip.id
                        )
                        FROM app.customer_case_carat_import_positions cip
                        WHERE cip.import_id = ci.id
                      ), '[]'::jsonb)
                    )
                    ORDER BY ci.created_at DESC, ci.id DESC
                  )
                  FROM app.customer_case_carat_imports ci
                  JOIN app.customer_case_documents cd ON cd.id = ci.document_id
                  WHERE ci.customer_case_id = cc.id
                    AND cd.document_status <> 'archived'
                    AND cd.is_current_version = TRUE
                ), '[]'::jsonb),
                'supplier_orders', COALESCE((
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'id', so.id,
                      'customer_case_id', so.customer_case_id,
                      'supplier_id', so.supplier_id,
                      'supplier_name', s.name,
                      'source_carat_import_id', so.source_carat_import_id,
                      'order_number', so.order_number,
                      'title', so.title,
                      'status', so.status,
                      'ordered_position_count', so.ordered_position_count,
                      'created_at',
                        to_char(
                          so.created_at AT TIME ZONE 'Europe/Berlin',
                          'YYYY-MM-DD HH24:MI'
                        ),
                      'positions', COALESCE((
                        SELECT jsonb_agg(
                          jsonb_build_object(
                            'id', sop.id,
                            'position_number', sop.position_number,
                            'article_code', sop.article_code,
                            'title', sop.title,
                            'description', sop.description,
                            'quantity', sop.quantity,
                            'unit', sop.unit,
                            'ordered_net_price', sop.ordered_net_price,
                            'ordered_delivery_week', sop.ordered_delivery_week,
                            'ordered_delivery_date', sop.ordered_delivery_date
                          )
                          ORDER BY sop.id
                        )
                        FROM app.supplier_order_positions sop
                        WHERE sop.supplier_order_id = so.id
                      ), '[]'::jsonb)
                    )
                    ORDER BY so.updated_at DESC, so.id DESC
                  )
                  FROM app.supplier_orders so
                  JOIN app.suppliers s ON s.id = so.supplier_id
                  WHERE so.customer_case_id = cc.id
                    AND so.status <> 'canceled'
                ), '[]'::jsonb),
                'supplier_order_confirmations', COALESCE((
                  SELECT jsonb_agg(
                    jsonb_build_object(
                      'id', soc.id,
                      'inbox_item_id', soc.inbox_item_id,
                      'customer_case_id', soc.customer_case_id,
                      'supplier_order_id', soc.supplier_order_id,
                      'supplier_id', soc.supplier_id,
                      'supplier_name', s.name,
                      'document_id', soc.document_id,
                      'confirmation_number', soc.confirmation_number,
                      'status', soc.status,
                      'ordered_position_count', soc.ordered_position_count,
                      'confirmation_position_count', soc.confirmation_position_count,
                      'matched_position_count', soc.matched_position_count,
                      'unmatched_order_position_count', soc.unmatched_order_position_count,
                      'unmatched_confirmation_position_count',
                        soc.unmatched_confirmation_position_count,
                      'match_rate', soc.match_rate,
                      'approved_at',
                        CASE
                          WHEN soc.approved_at IS NULL THEN NULL
                          ELSE to_char(
                            soc.approved_at AT TIME ZONE 'Europe/Berlin',
                            'YYYY-MM-DD HH24:MI'
                          )
                        END,
                      'created_at',
                        to_char(
                          soc.created_at AT TIME ZONE 'Europe/Berlin',
                          'YYYY-MM-DD HH24:MI'
                        ),
                      'positions', COALESCE((
                        SELECT jsonb_agg(
                          jsonb_build_object(
                            'id', cp.id,
                            'matched_order_position_id', cp.matched_order_position_id,
                            'position_number', cp.position_number,
                            'article_code', cp.article_code,
                            'title', cp.title,
                            'description', cp.description,
                            'quantity', cp.quantity,
                            'unit', cp.unit,
                            'confirmed_net_price', cp.confirmed_net_price,
                            'confirmed_delivery_week', cp.confirmed_delivery_week,
                            'confirmed_delivery_date', cp.confirmed_delivery_date,
                            'match_status', cp.match_status,
                            'severity', cp.severity
                          )
                          ORDER BY cp.id
                        )
                        FROM app.supplier_order_confirmation_positions cp
                        WHERE cp.confirmation_id = soc.id
                      ), '[]'::jsonb),
                      'exceptions', COALESCE((
                        SELECT jsonb_agg(
                          jsonb_build_object(
                            'id', ex.id,
                            'confirmation_position_id', ex.confirmation_position_id,
                            'order_position_id', ex.order_position_id,
                            'difference_type', ex.difference_type,
                            'severity', ex.severity,
                            'status', ex.status,
                            'ordered_value', ex.ordered_value,
                            'confirmed_value', ex.confirmed_value,
                            'difference_value', ex.difference_value,
                            'message', ex.message,
                            'resolution_action', ex.resolution_action,
                            'resolution_note', ex.resolution_note,
                            'resolved_at',
                              CASE
                                WHEN ex.resolved_at IS NULL THEN NULL
                                ELSE to_char(
                                  ex.resolved_at AT TIME ZONE 'Europe/Berlin',
                                  'YYYY-MM-DD HH24:MI'
                                )
                              END
                          )
                          ORDER BY
                            CASE ex.severity WHEN 'red' THEN 0 ELSE 1 END,
                            ex.id
                        )
                        FROM app.supplier_order_confirmation_exceptions ex
                        WHERE ex.confirmation_id = soc.id
                      ), '[]'::jsonb),
                      'communications', COALESCE((
                        SELECT jsonb_agg(
                          jsonb_build_object(
                            'id', sc.id,
                            'exception_id', sc.exception_id,
                            'communication_type', sc.communication_type,
                            'status', sc.status,
                            'recipient_email', sc.recipient_email,
                            'subject', sc.subject,
                            'body', sc.body,
                            'created_at',
                              to_char(
                                sc.created_at AT TIME ZONE 'Europe/Berlin',
                                'YYYY-MM-DD HH24:MI'
                              )
                          )
                          ORDER BY sc.created_at DESC, sc.id DESC
                        )
                        FROM app.supplier_communications sc
                        WHERE sc.confirmation_id = soc.id
                      ), '[]'::jsonb),
                      'follow_ups', COALESCE((
                        SELECT jsonb_agg(
                          jsonb_build_object(
                            'id', sf.id,
                            'communication_id', sf.communication_id,
                            'title', sf.title,
                            'status', sf.status,
                            'due_at',
                              CASE
                                WHEN sf.due_at IS NULL THEN NULL
                                ELSE to_char(
                                  sf.due_at AT TIME ZONE 'Europe/Berlin',
                                  'YYYY-MM-DD HH24:MI'
                                )
                              END
                          )
                          ORDER BY sf.due_at NULLS LAST, sf.id
                        )
                        FROM app.supplier_follow_ups sf
                        WHERE sf.confirmation_id = soc.id
                      ), '[]'::jsonb)
                    )
                    ORDER BY soc.updated_at DESC, soc.id DESC
                  )
                  FROM app.supplier_order_confirmations soc
                  JOIN app.suppliers s ON s.id = soc.supplier_id
                  WHERE soc.customer_case_id = cc.id
                ), '[]'::jsonb),
                'updated_at',
                  to_char(
                    cc.updated_at AT TIME ZONE 'Europe/Berlin',
                    'YYYY-MM-DD HH24:MI'
                  )
              )
              ORDER BY cc.updated_at DESC, cc.id DESC
            )
            FROM app.customer_cases cc
            JOIN visible_customers c ON c.id = cc.customer_id
            LEFT JOIN app.customer_case_status_phases csp
              ON csp.phase = COALESCE(cc.status_phase_id, cc.status_phase)
            WHERE cc.is_active = TRUE
          ), '[]'::jsonb)
        )::text;
        """,
        {"context": json.dumps(context)},
    )
    if state is None:
        return {
            "current_user": context,
            "users": [],
            "status_phases": [],
            "customers": [],
            "customer_cases": [],
        }
    return state


def search_customers(
    query: str,
    access_email: str,
    customer_filter: str = "all",
) -> dict[str, Any]:
    context = require_primary_user(access_email)
    search_value = query.strip()
    search_filter = customer_filter if customer_filter in {"active", "closed", "all"} else "all"
    phone_value = normalize_phone_number(search_value)
    if len(search_value) < 3:
        return {"ok": True, "customers": []}
    return psql_json(
        """
        WITH context AS (
          SELECT :'context'::jsonb AS data
        ),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_customers AS (
          SELECT DISTINCT c.*
          FROM app.customers c
          LEFT JOIN app.customer_cases cc ON cc.customer_id = c.id
          WHERE c.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
            )
        ),
        matches AS (
          SELECT
            c.id,
            c.display_name,
            c.customer_type,
            c.customer_number,
            c.primary_email,
            ca.postal_code,
            ca.city,
            CASE
              WHEN lower(COALESCE(c.primary_email, '')) = lower(:'search_value') THEN 0
              WHEN :'phone_value' <> ''
                AND COALESCE(c.primary_phone_normalized, '') = :'phone_value' THEN 1
              WHEN :'phone_value' <> ''
                AND COALESCE(c.primary_mobile_normalized, '') = :'phone_value' THEN 1
              WHEN lower(COALESCE(c.customer_number, '')) = lower(:'search_value') THEN 2
              WHEN lower(c.display_name) = lower(:'search_value') THEN 3
              ELSE 9
            END AS rank
          FROM visible_customers c
          LEFT JOIN LATERAL (
            SELECT postal_code, city
            FROM app.customer_addresses ca
            WHERE ca.customer_id = c.id
            ORDER BY ca.is_primary DESC, ca.id
            LIMIT 1
          ) ca ON TRUE
          WHERE
            (
              c.display_name ILIKE '%' || :'search_value' || '%'
              OR COALESCE(c.company_name, '') ILIKE '%' || :'search_value' || '%'
              OR COALESCE(c.customer_number, '') ILIKE '%' || :'search_value' || '%'
              OR COALESCE(c.primary_email, '') ILIKE '%' || :'search_value' || '%'
              OR (
                :'phone_value' <> ''
                AND COALESCE(c.primary_phone_normalized, '') = :'phone_value'
              )
              OR (
                :'phone_value' <> ''
                AND COALESCE(c.primary_mobile_normalized, '') = :'phone_value'
              )
              OR COALESCE(c.primary_phone, '') ILIKE '%' || :'search_value' || '%'
              OR COALESCE(c.primary_mobile, '') ILIKE '%' || :'search_value' || '%'
            )
            AND (
              :'customer_filter' = 'all'
              OR (
                :'customer_filter' = 'closed'
                AND EXISTS (
                  SELECT 1
                  FROM app.customer_cases cc
                  LEFT JOIN app.customer_case_status_phases csp
                    ON csp.phase = COALESCE(cc.status_phase_id, cc.status_phase)
                  WHERE cc.customer_id = c.id
                    AND cc.is_active = TRUE
                    AND COALESCE(csp.is_terminal, FALSE) = TRUE
                )
              )
              OR (
                :'customer_filter' = 'active'
                AND (
                  EXISTS (
                    SELECT 1
                    FROM app.customer_cases cc
                    LEFT JOIN app.customer_case_status_phases csp
                      ON csp.phase = COALESCE(cc.status_phase_id, cc.status_phase)
                    WHERE cc.customer_id = c.id
                      AND cc.is_active = TRUE
                      AND COALESCE(csp.is_terminal, FALSE) = FALSE
                  )
                  OR NOT EXISTS (
                    SELECT 1
                    FROM app.customer_cases cc
                    WHERE cc.customer_id = c.id
                      AND cc.is_active = TRUE
                  )
                )
              )
            )
        )
        SELECT jsonb_build_object(
          'ok', TRUE,
          'customers', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'customer_id', id,
                'display_name', display_name,
                'customer_type', customer_type,
                'customer_number', customer_number,
                'city', city,
                'postal_code', postal_code,
                'primary_email', primary_email
              )
              ORDER BY rank, display_name, id
            )
            FROM (
              SELECT *
              FROM matches
              ORDER BY rank, display_name, id
              LIMIT 20
            ) limited_matches
          ), '[]'::jsonb)
        )::text;
        """,
        {
            "context": json.dumps(context),
            "search_value": search_value,
            "customer_filter": search_filter,
            "phone_value": phone_value,
        },
    )


def customer_duplicate_matches(
    payload: dict[str, Any],
    match_scope: str = "all",
) -> list[dict[str, Any]]:
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        candidates AS (
          SELECT DISTINCT
            c.id,
            c.display_name,
            c.customer_number,
            c.customer_type,
            c.primary_email,
            c.primary_phone,
            ca.postal_code,
            ca.city,
            ca.street,
            ca.house_number,
            (
              SELECT count(*)
              FROM app.customer_cases cc
              WHERE cc.customer_id = c.id
                AND cc.is_active = TRUE
            ) AS active_case_count,
            CASE
              WHEN NULLIF(data->>'primary_email', '') IS NOT NULL
                AND lower(COALESCE(c.primary_email, '')) = lower(data->>'primary_email')
                THEN 'email'
              WHEN NULLIF(data->>'primary_phone_normalized', '') IS NOT NULL
                AND COALESCE(c.primary_phone_normalized, '') = data->>'primary_phone_normalized'
                THEN 'phone'
              WHEN NULLIF(data->>'primary_mobile_normalized', '') IS NOT NULL
                AND COALESCE(c.primary_mobile_normalized, '') = data->>'primary_mobile_normalized'
                THEN 'mobile'
              WHEN NULLIF(data->>'postal_code', '') IS NOT NULL
                AND lower(c.display_name) = lower(data->>'display_name')
                AND EXISTS (
                  SELECT 1
                  FROM app.customer_addresses ca
                  WHERE ca.customer_id = c.id
                    AND ca.postal_code = data->>'postal_code'
                )
                THEN 'name_postal_code'
              ELSE 'unknown'
            END AS match_type
          FROM app.customers c
          LEFT JOIN LATERAL (
            SELECT postal_code, city, street, house_number
            FROM app.customer_addresses ca
            WHERE ca.customer_id = c.id
            ORDER BY ca.is_primary DESC, ca.id
            LIMIT 1
          ) ca ON TRUE,
          payload
          WHERE c.is_active = TRUE
            AND c.id <> COALESCE(NULLIF(data->>'customer_id', '')::bigint, 0)
            AND (
              (
                NULLIF(data->>'primary_email', '') IS NOT NULL
                AND lower(COALESCE(c.primary_email, '')) = lower(data->>'primary_email')
              )
              OR (
                NULLIF(data->>'primary_phone_normalized', '') IS NOT NULL
                AND COALESCE(c.primary_phone_normalized, '') = data->>'primary_phone_normalized'
              )
              OR (
                NULLIF(data->>'primary_mobile_normalized', '') IS NOT NULL
                AND COALESCE(c.primary_mobile_normalized, '') = data->>'primary_mobile_normalized'
              )
              OR (
                NULLIF(data->>'postal_code', '') IS NOT NULL
                AND lower(c.display_name) = lower(data->>'display_name')
                AND EXISTS (
                  SELECT 1
                  FROM app.customer_addresses ca
                  WHERE ca.customer_id = c.id
                    AND ca.postal_code = data->>'postal_code'
                )
              )
            )
            AND (
              :'match_scope' = 'all'
              OR (
                :'match_scope' = 'email'
                AND NULLIF(data->>'primary_email', '') IS NOT NULL
                AND lower(COALESCE(c.primary_email, '')) = lower(data->>'primary_email')
              )
            )
          ORDER BY c.display_name, c.id
          LIMIT 5
        )
        SELECT jsonb_build_object(
          'matches', COALESCE((
            SELECT jsonb_agg(
              jsonb_build_object(
                'customer_id', id,
                'display_name', display_name,
                'customer_number', customer_number,
                'customer_type', customer_type,
                'primary_email', primary_email,
                'primary_phone', primary_phone,
                'postal_code', postal_code,
                'city', city,
                'street', street,
                'house_number', house_number,
                'active_case_count', active_case_count,
                'match_type', match_type
              )
              ORDER BY display_name, id
            )
            FROM candidates
          ), '[]'::jsonb)
        )::text;
        """,
        {"payload": json.dumps(payload), "match_scope": match_scope},
    )
    matches = result.get("matches") if result else []
    return matches if isinstance(matches, list) else []


def save_customer(
    data: dict[str, Any],
    access_email: str,
    customer_id: str | None = None,
) -> dict[str, Any]:
    context = require_primary_user(access_email)
    actor_user_id = int(context["primary_user_id"])
    display_name = customer_display_name(data)
    if not display_name:
        raise ApiError(HTTPStatus.BAD_REQUEST, "customer_name_required")
    customer_type = str(data.get("customer_type", "private")).strip() or "private"
    create_case = normalize_bool(data.get("create_case"))
    allow_duplicate_email = normalize_bool(data.get("allow_duplicate_email"))
    is_company = customer_type == "company"
    contact_first_name = str(data.get("contact_first_name", "")).strip()
    contact_last_name = str(data.get("contact_last_name", "")).strip()
    contact_email = str(data.get("contact_email", "")).strip().lower()
    contact_phone = str(data.get("contact_phone", "")).strip()
    contact_display_name = " ".join(
        part for part in [contact_first_name, contact_last_name] if part
    )
    country = str(data.get("country", "DE")).strip().upper() or "DE"
    has_custom_vat = normalize_bool(data.get("has_custom_vat"))
    custom_vat_rate = str(data.get("custom_vat_rate", "")).strip().replace(",", ".")
    if not has_custom_vat:
        custom_vat_rate = ""
    payload = {
        "customer_id": str(customer_id or "").strip(),
        "customer_number": ""
        if customer_id
        else generate_customer_number(customer_type),
        "customer_type": customer_type,
        "salutation": str(data.get("salutation", "")).strip(),
        "title": str(data.get("title", "")).strip(),
        "first_name": "" if is_company else str(data.get("first_name", "")).strip(),
        "last_name": "" if is_company else str(data.get("last_name", "")).strip(),
        "company_name": str(data.get("company_name", "")).strip(),
        "legal_form": str(data.get("legal_form", "")).strip() if is_company else "",
        "vat_id": str(data.get("vat_id", "")).strip() if is_company else "",
        "tax_number": str(data.get("tax_number", "")).strip() if is_company else "",
        "registry_court": str(data.get("registry_court", "")).strip() if is_company else "",
        "registry_number": str(data.get("registry_number", "")).strip() if is_company else "",
        "object_customer_label": str(data.get("object_customer_label", "")).strip()
        if is_company
        else "",
        "country": country,
        "tax_treatment": str(data.get("tax_treatment", "standard_de")).strip() or "standard_de",
        "tax_treatment_note": str(data.get("tax_treatment_note", "")).strip(),
        "has_custom_vat": has_custom_vat,
        "custom_vat_rate": custom_vat_rate,
        "custom_vat_rate_label": str(data.get("custom_vat_rate_label", "")).strip()
        if has_custom_vat
        else "",
        "contact_first_name": contact_first_name,
        "contact_last_name": contact_last_name,
        "contact_display_name": contact_display_name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "contact_phone_normalized": normalize_phone_number(contact_phone),
        "display_name": display_name,
        "primary_email": str(data.get("primary_email", "")).strip().lower(),
        "primary_phone": str(data.get("primary_phone", "")).strip(),
        "primary_phone_normalized": normalize_phone_number(data.get("primary_phone", "")),
        "primary_mobile": str(data.get("primary_mobile", "")).strip(),
        "primary_mobile_normalized": normalize_phone_number(data.get("primary_mobile", "")),
        "preferred_contact_channel": str(data.get("preferred_contact_channel", "email")).strip()
        or "email",
        "notes": str(data.get("notes", "")).strip(),
        "owner_user_id": str(data.get("owner_user_id") or actor_user_id),
        "street": str(data.get("street", "")).strip(),
        "house_number": str(data.get("house_number", "")).strip(),
        "postal_code": str(data.get("postal_code", "")).strip(),
        "city": str(data.get("city", "")).strip(),
        "create_case": create_case,
        "case_number": generate_case_number() if create_case else "",
        "carat_order_number": normalize_carat_order_number(data.get("carat_order_number", "")),
        "case_title": str(data.get("case_title", "")).strip(),
        "case_type": str(
            data.get(
                "case_type",
                "kitchen_project_b2b"
                if str(data.get("customer_type", "private")).strip() == "company"
                else "kitchen_project",
            )
        ).strip(),
        "status_phase_id": str(data.get("status_phase_id") or "1"),
        "responsible_user_id": str(
            data.get("responsible_user_id") or data.get("owner_user_id") or actor_user_id
        ),
        "actor_user_id": actor_user_id,
        "context": context,
    }
    email_duplicate_matches = customer_duplicate_matches(payload, "email")
    if (
        email_duplicate_matches
        and not allow_duplicate_email
        and not customer_id
    ):
        raise ApiError(
            HTTPStatus.CONFLICT,
            "customer_email_duplicate_found",
            {"matches": email_duplicate_matches},
        )
    duplicate_matches = [
        match
        for match in customer_duplicate_matches(payload)
        if match.get("match_type") != "email"
    ]
    if duplicate_matches:
        raise ApiError(
            HTTPStatus.CONFLICT,
            "customer_duplicate_found",
            {"matches": duplicate_matches},
        )
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_customer AS (
          SELECT c.id
          FROM app.customers c
          WHERE c.id = NULLIF((SELECT data->>'customer_id' FROM payload), '')::bigint
            AND c.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        updated_customer AS (
          UPDATE app.customers c
          SET
            customer_type = data->>'customer_type',
            salutation = NULLIF(data->>'salutation', ''),
            title = NULLIF(data->>'title', ''),
            first_name = NULLIF(data->>'first_name', ''),
            last_name = NULLIF(data->>'last_name', ''),
            company_name = NULLIF(data->>'company_name', ''),
            vat_id = NULLIF(data->>'vat_id', ''),
            tax_number = NULLIF(data->>'tax_number', ''),
            legal_form = NULLIF(data->>'legal_form', ''),
            registry_court = NULLIF(data->>'registry_court', ''),
            registry_number = NULLIF(data->>'registry_number', ''),
            object_customer_label = NULLIF(data->>'object_customer_label', ''),
            display_name = data->>'display_name',
            primary_email = NULLIF(data->>'primary_email', ''),
            primary_phone = NULLIF(data->>'primary_phone', ''),
            primary_phone_normalized = NULLIF(data->>'primary_phone_normalized', ''),
            primary_mobile = NULLIF(data->>'primary_mobile', ''),
            primary_mobile_normalized = NULLIF(data->>'primary_mobile_normalized', ''),
            preferred_contact_channel = data->>'preferred_contact_channel',
            country = NULLIF(data->>'country', ''),
            iso_country_code = NULLIF(data->>'country', ''),
            tax_treatment = NULLIF(data->>'tax_treatment', ''),
            tax_treatment_note = NULLIF(data->>'tax_treatment_note', ''),
            has_custom_vat = (data->>'has_custom_vat')::boolean,
            custom_vat_rate = NULLIF(data->>'custom_vat_rate', '')::numeric,
            custom_vat_rate_label = NULLIF(data->>'custom_vat_rate_label', ''),
            notes = NULLIF(data->>'notes', ''),
            owner_user_id = NULLIF(data->>'owner_user_id', '')::bigint,
            updated_at = now()
          FROM payload
          WHERE c.id = (SELECT id FROM visible_customer)
          RETURNING c.id
        ),
        inserted_customer AS (
          INSERT INTO app.customers (
            customer_number,
            customer_type,
            salutation,
            title,
            first_name,
            last_name,
            company_name,
            vat_id,
            tax_number,
            legal_form,
            registry_court,
            registry_number,
            object_customer_label,
            display_name,
            primary_email,
            primary_phone,
            primary_phone_normalized,
            primary_mobile,
            primary_mobile_normalized,
            preferred_contact_channel,
            country,
            iso_country_code,
            tax_treatment,
            tax_treatment_note,
            has_custom_vat,
            custom_vat_rate,
            custom_vat_rate_label,
            notes,
            owner_user_id,
            created_by_user_id
          )
          SELECT
            NULLIF(data->>'customer_number', ''),
            data->>'customer_type',
            NULLIF(data->>'salutation', ''),
            NULLIF(data->>'title', ''),
            NULLIF(data->>'first_name', ''),
            NULLIF(data->>'last_name', ''),
            NULLIF(data->>'company_name', ''),
            NULLIF(data->>'vat_id', ''),
            NULLIF(data->>'tax_number', ''),
            NULLIF(data->>'legal_form', ''),
            NULLIF(data->>'registry_court', ''),
            NULLIF(data->>'registry_number', ''),
            NULLIF(data->>'object_customer_label', ''),
            data->>'display_name',
            NULLIF(data->>'primary_email', ''),
            NULLIF(data->>'primary_phone', ''),
            NULLIF(data->>'primary_phone_normalized', ''),
            NULLIF(data->>'primary_mobile', ''),
            NULLIF(data->>'primary_mobile_normalized', ''),
            data->>'preferred_contact_channel',
            NULLIF(data->>'country', ''),
            NULLIF(data->>'country', ''),
            NULLIF(data->>'tax_treatment', ''),
            NULLIF(data->>'tax_treatment_note', ''),
            (data->>'has_custom_vat')::boolean,
            NULLIF(data->>'custom_vat_rate', '')::numeric,
            NULLIF(data->>'custom_vat_rate_label', ''),
            NULLIF(data->>'notes', ''),
            NULLIF(data->>'owner_user_id', '')::bigint,
            (data->>'actor_user_id')::bigint
          FROM payload
          WHERE (data->>'customer_id') = ''
          RETURNING id
        ),
        target_customer AS (
          SELECT id FROM updated_customer
          UNION ALL
          SELECT id FROM inserted_customer
        ),
        address_input AS (
          SELECT data
          FROM payload
          WHERE NULLIF(data->>'street', '') IS NOT NULL
            AND NULLIF(data->>'postal_code', '') IS NOT NULL
            AND NULLIF(data->>'city', '') IS NOT NULL
        ),
        existing_address AS (
          SELECT ca.id
          FROM app.customer_addresses ca
          WHERE ca.customer_id = (SELECT id FROM target_customer)
            AND ca.address_type = 'billing'
          ORDER BY ca.is_primary DESC, ca.id
          LIMIT 1
        ),
        updated_address AS (
          UPDATE app.customer_addresses ca
          SET
            recipient_name = (SELECT data->>'display_name' FROM payload),
            street = data->>'street',
            house_number = NULLIF(data->>'house_number', ''),
            postal_code = data->>'postal_code',
            city = data->>'city',
            country = NULLIF(data->>'country', ''),
            iso_country_code = NULLIF(data->>'country', ''),
            updated_at = now(),
            is_primary = TRUE
          FROM address_input
          WHERE ca.id = (SELECT id FROM existing_address)
        ),
        inserted_address AS (
          INSERT INTO app.customer_addresses (
            customer_id,
            address_type,
            recipient_name,
            street,
            house_number,
            postal_code,
            city,
            country,
            iso_country_code,
            is_primary
          )
          SELECT
            (SELECT id FROM target_customer),
            'billing',
            data->>'display_name',
            data->>'street',
            NULLIF(data->>'house_number', ''),
            data->>'postal_code',
            data->>'city',
            data->>'country',
            data->>'country',
            TRUE
          FROM address_input
          WHERE NOT EXISTS (SELECT 1 FROM existing_address)
        ),
        contact_input AS (
          SELECT data
          FROM payload
          WHERE data->>'customer_type' = 'company'
            AND (
              NULLIF(data->>'contact_display_name', '') IS NOT NULL
              OR NULLIF(data->>'contact_email', '') IS NOT NULL
              OR NULLIF(data->>'contact_phone', '') IS NOT NULL
            )
        ),
        existing_contact AS (
          SELECT cc.id
          FROM app.customer_contacts cc
          WHERE cc.customer_id = (SELECT id FROM target_customer)
            AND cc.contact_type = 'primary'
          ORDER BY cc.is_primary DESC, cc.id
          LIMIT 1
        ),
        updated_contact AS (
          UPDATE app.customer_contacts cc
          SET
            first_name = NULLIF(data->>'contact_first_name', ''),
            last_name = NULLIF(data->>'contact_last_name', ''),
            display_name = COALESCE(
              NULLIF(data->>'contact_display_name', ''),
              NULLIF(data->>'contact_email', ''),
              NULLIF(data->>'contact_phone', '')
            ),
            email = NULLIF(data->>'contact_email', ''),
            phone = NULLIF(data->>'contact_phone', ''),
            phone_normalized = NULLIF(data->>'contact_phone_normalized', ''),
            updated_at = now(),
            is_primary = TRUE
          FROM contact_input
          WHERE cc.id = (SELECT id FROM existing_contact)
        ),
        inserted_contact AS (
          INSERT INTO app.customer_contacts (
            customer_id,
            contact_type,
            first_name,
            last_name,
            display_name,
            email,
            phone,
            phone_normalized,
            is_primary
          )
          SELECT
            (SELECT id FROM target_customer),
            'primary',
            NULLIF(data->>'contact_first_name', ''),
            NULLIF(data->>'contact_last_name', ''),
            COALESCE(
              NULLIF(data->>'contact_display_name', ''),
              NULLIF(data->>'contact_email', ''),
              NULLIF(data->>'contact_phone', '')
            ),
            NULLIF(data->>'contact_email', ''),
            NULLIF(data->>'contact_phone', ''),
            NULLIF(data->>'contact_phone_normalized', ''),
            TRUE
          FROM contact_input
          WHERE NOT EXISTS (SELECT 1 FROM existing_contact)
        ),
        created_case AS (
          INSERT INTO app.customer_cases (
            case_number,
            customer_display_name,
            status_phase,
            owner_user_id,
            customer_id,
            case_title,
            case_type,
            carat_order_number,
            status_phase_id,
            created_by_user_id,
            responsible_user_id
          )
          SELECT
            NULLIF(data->>'case_number', ''),
            data->>'display_name',
            NULLIF(data->>'status_phase_id', '')::smallint,
            NULLIF(data->>'responsible_user_id', '')::bigint,
            (SELECT id FROM target_customer),
            NULLIF(data->>'case_title', ''),
            data->>'case_type',
            NULLIF(data->>'carat_order_number', ''),
            NULLIF(data->>'status_phase_id', '')::smallint,
            (data->>'actor_user_id')::bigint,
            NULLIF(data->>'responsible_user_id', '')::bigint
          FROM payload
          WHERE (data->>'create_case')::boolean
          RETURNING id
        ),
        customer_event AS (
          INSERT INTO app.communication_events (
            event_type,
            customer_case_id,
            actor_user_id,
            title,
            body
          )
          SELECT
            CASE WHEN (SELECT data->>'customer_id' FROM payload) = '' THEN 'customer_created'
                 ELSE 'customer_updated'
            END,
            (SELECT id FROM created_case),
            (SELECT (data->>'actor_user_id')::bigint FROM payload),
            (SELECT data->>'display_name' FROM payload),
            NULLIF((SELECT data->>'notes' FROM payload), '')
        )
        SELECT jsonb_build_object(
          'ok', TRUE,
          'customer_id', (SELECT id FROM target_customer),
          'customer_case_id', (SELECT id FROM created_case)
        )::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("customer_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_not_found")
    return result


def save_customer_section(
    customer_id: str,
    section_code: str,
    data: dict[str, Any],
    access_email: str,
) -> dict[str, Any]:
    context = require_primary_user(access_email)
    payload = {
        "customer_id": customer_id,
        "section_code": section_code,
        "payload_json": {
            key: value
            for key, value in data.items()
            if not key.startswith("_")
        },
        "actor_user_id": context["primary_user_id"],
        "context": context,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_customer AS (
          SELECT c.id
          FROM app.customers c
          LEFT JOIN app.customer_cases cc ON cc.customer_id = c.id
          WHERE c.id = NULLIF((SELECT data->>'customer_id' FROM payload), '')::bigint
            AND c.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        upserted AS (
          INSERT INTO app.customer_file_sections (
            customer_id,
            section_code,
            payload_json,
            updated_by_user_id
          )
          SELECT
            (SELECT id FROM visible_customer),
            data->>'section_code',
            data->'payload_json',
            NULLIF(data->>'actor_user_id', '')::bigint
          FROM payload
          WHERE EXISTS (SELECT 1 FROM visible_customer)
          ON CONFLICT (customer_id, section_code) DO UPDATE
          SET
            payload_json = EXCLUDED.payload_json,
            updated_by_user_id = EXCLUDED.updated_by_user_id,
            updated_at = now()
          RETURNING id
        )
        SELECT jsonb_build_object('ok', TRUE, 'section_id', (SELECT id FROM upserted))::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("section_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_not_found")
    return result


def berlin_now() -> datetime:
    return datetime.now(ZoneInfo("Europe/Berlin"))


def export_slug(value: Any, fallback: str = "Kundenakte") -> str:
    normalized = unicodedata.normalize("NFKD", str(value or fallback))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", ascii_value).strip("_")
    return slug or fallback


def pdf_escape(value: Any) -> str:
    text = str(value or "")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def simple_pdf(title: str, lines: list[str]) -> bytes:
    text_lines = [title, "", *lines]
    content = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
    for index, line in enumerate(text_lines[:52]):
        if index:
            content.append("T*")
        content.append(f"({pdf_escape(line[:105])}) Tj")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        ),
    ]
    output = BytesIO()
    output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{number} 0 obj\n".encode("ascii"))
        output.write(obj)
        output.write(b"\nendobj\n")
    xref_offset = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return output.getvalue()


def export_folder(customer: dict[str, Any]) -> str:
    number = export_slug(customer.get("customer_number"), f"Kunde_{customer.get('id')}")
    name = export_slug(customer.get("display_name"), "Kundenakte")
    return f"{number}_{name}"


def export_timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def customer_export_pdf_lines(
    customer: dict[str, Any],
    cases: list[dict[str, Any]],
    exported_at: str,
) -> list[str]:
    address = customer.get("address") or {}
    address_line = " ".join(
        str(part)
        for part in [
            address.get("street"),
            address.get("house_number"),
            address.get("postal_code"),
            address.get("city"),
            address.get("country") or customer.get("country"),
        ]
        if part
    )
    phone_value = (
        customer.get("primary_phone")
        or customer.get("primary_mobile")
        or "Nicht hinterlegt"
    )
    lines = [
        f"Exportiert am: {exported_at}",
        f"Kundennummer: {customer.get('customer_number') or 'ohne Nummer'}",
        f"Name: {customer.get('display_name') or ''}",
        f"Kundentyp: {customer.get('customer_type') or ''}",
        f"E-Mail: {customer.get('primary_email') or 'Nicht hinterlegt'}",
        f"Telefon: {phone_value}",
        f"Adresse: {address_line or 'Nicht hinterlegt'}",
        f"Notizen: {customer.get('notes') or ''}",
        "",
        f"Vorgaenge: {len(cases)}",
    ]
    for case in cases[:20]:
        lines.append(
            " - "
            + " | ".join(
                part
                for part in [
                    case.get("case_number") or f"Vorgang #{case.get('id')}",
                    case.get("case_title") or "Kuechenprojekt",
                    case.get("status_phase_name") or case.get("case_status") or "",
                ]
                if part
            )
        )
    return lines


def customer_export_document_rows(
    customer_id: str, context: dict[str, Any]
) -> list[dict[str, Any]]:
    result = psql_json(
        """
        WITH context AS (SELECT :'context'::jsonb AS data),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_customer AS (
          SELECT c.id
          FROM app.customers c
          LEFT JOIN app.customer_cases cc ON cc.customer_id = c.id
          WHERE c.id = NULLIF(:'customer_id', '')::bigint
            AND c.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        )
        SELECT COALESCE(jsonb_agg(
          jsonb_build_object(
            'case_id', cc.id,
            'case_number', cc.case_number,
            'document_id', d.id,
            'register_code', d.register_code,
            'document_category', d.document_category,
            'title', COALESCE(d.title, d.original_filename, 'Dokument'),
            'original_filename', d.original_filename,
            'storage_path', d.storage_path,
            'storage_backend', d.storage_backend,
            'object_storage_key', d.object_storage_key,
            'content_type', d.content_type
          )
          ORDER BY cc.id, d.id
        ), '[]'::jsonb)::text
        FROM app.customer_case_documents d
        JOIN app.customer_cases cc ON cc.id = d.customer_case_id
        WHERE cc.customer_id = (SELECT id FROM visible_customer)
          AND d.archived_at IS NULL;
        """,
        {"customer_id": customer_id, "context": json.dumps(context)},
    )
    return result if isinstance(result, list) else []


def customer_export_task_rows(customer_id: str, context: dict[str, Any]) -> list[dict[str, Any]]:
    result = psql_json(
        """
        WITH context AS (SELECT :'context'::jsonb AS data),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_customer AS (
          SELECT c.id
          FROM app.customers c
          LEFT JOIN app.customer_cases cc ON cc.customer_id = c.id
          WHERE c.id = NULLIF(:'customer_id', '')::bigint
            AND c.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        )
        SELECT COALESCE(jsonb_agg(
          jsonb_build_object(
            'id', t.id,
            'customer_case_id', t.related_case_id,
            'case_number', cc.case_number,
            'title', t.title,
            'description', t.description,
            'status', ts.code,
            'status_name', ts.name,
            'priority', t.priority,
            'due_at',
              CASE
                WHEN t.due_at IS NULL THEN NULL
                ELSE to_char(t.due_at AT TIME ZONE 'Europe/Berlin', 'YYYY-MM-DD HH24:MI')
              END,
            'reminder_at',
              CASE
                WHEN t.reminder_at IS NULL THEN NULL
                ELSE to_char(t.reminder_at AT TIME ZONE 'Europe/Berlin', 'YYYY-MM-DD HH24:MI')
              END,
            'created_at',
              to_char(t.created_at AT TIME ZONE 'Europe/Berlin', 'YYYY-MM-DD HH24:MI'),
            'attachments', COALESCE((
              SELECT jsonb_agg(
                jsonb_build_object(
                  'id', tatt.id,
                  'task_id', tatt.task_id,
                  'original_filename', tatt.original_filename,
                  'storage_path', tatt.storage_path,
                  'content_type', tatt.content_type,
                  'file_size_bytes', tatt.file_size_bytes,
                  'created_at',
                    to_char(tatt.created_at AT TIME ZONE 'Europe/Berlin', 'YYYY-MM-DD HH24:MI')
                )
                ORDER BY tatt.created_at DESC, tatt.id DESC
              )
              FROM app.task_attachments tatt
              WHERE tatt.task_id = t.id
            ), '[]'::jsonb)
          )
          ORDER BY t.due_at NULLS LAST, t.created_at DESC, t.id DESC
        ), '[]'::jsonb)::text
        FROM app.tasks t
        JOIN app.customer_cases cc ON cc.id = t.related_case_id
        JOIN app.task_statuses ts ON ts.id = t.status_id
        WHERE cc.customer_id = (SELECT id FROM visible_customer)
          AND t.archived_at IS NULL
          AND t.deleted_at IS NULL;
        """,
        {"customer_id": customer_id, "context": json.dumps(context)},
    )
    return result if isinstance(result, list) else []


def customer_export_email_rows(customer_id: str, context: dict[str, Any]) -> list[dict[str, Any]]:
    result = psql_json(
        """
        WITH context AS (SELECT :'context'::jsonb AS data),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_customer AS (
          SELECT c.id
          FROM app.customers c
          LEFT JOIN app.customer_cases cc ON cc.customer_id = c.id
          WHERE c.id = NULLIF(:'customer_id', '')::bigint
            AND c.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        )
        SELECT COALESCE(jsonb_agg(
          jsonb_build_object(
            'id', em.id,
            'customer_case_id', ecl.customer_case_id,
            'case_number', cc.case_number,
            'subject', em.subject,
            'snippet', em.snippet,
            'direction', em.direction,
            'received_at',
              CASE
                WHEN em.received_at IS NULL THEN NULL
                ELSE to_char(em.received_at AT TIME ZONE 'Europe/Berlin', 'YYYY-MM-DD HH24:MI')
              END,
            'sent_at',
              CASE
                WHEN em.sent_at IS NULL THEN NULL
                ELSE to_char(em.sent_at AT TIME ZONE 'Europe/Berlin', 'YYYY-MM-DD HH24:MI')
              END,
            'assigned_at',
              to_char(ecl.assigned_at AT TIME ZONE 'Europe/Berlin', 'YYYY-MM-DD HH24:MI'),
            'participants', COALESCE((
              SELECT jsonb_agg(
                jsonb_build_object(
                  'type', ep.participant_type,
                  'display_name', ep.display_name,
                  'email_address', ep.email_address
                )
                ORDER BY ep.id
              )
              FROM app.email_participants ep
              WHERE ep.email_message_id = em.id
            ), '[]'::jsonb),
            'attachments', COALESCE((
              SELECT jsonb_agg(
                jsonb_build_object(
                  'id', ea.id,
                  'email_message_id', ea.email_message_id,
                  'original_filename', ea.original_filename,
                  'storage_path', ea.storage_path,
                  'content_type', ea.content_type,
                  'file_size_bytes', ea.file_size_bytes,
                  'created_at',
                    to_char(ea.created_at AT TIME ZONE 'Europe/Berlin', 'YYYY-MM-DD HH24:MI')
                )
                ORDER BY ea.created_at DESC, ea.id DESC
              )
              FROM app.email_attachments ea
              WHERE ea.email_message_id = em.id
            ), '[]'::jsonb)
          )
          ORDER BY
            ecl.customer_case_id,
            em.received_at DESC NULLS LAST,
            em.created_at DESC,
            em.id DESC
        ), '[]'::jsonb)::text
        FROM app.email_case_links ecl
        JOIN app.customer_cases cc ON cc.id = ecl.customer_case_id
        JOIN app.email_messages em ON em.id = ecl.email_message_id
        WHERE cc.customer_id = (SELECT id FROM visible_customer)
          AND em.archived_at IS NULL
          AND em.deleted_at IS NULL;
        """,
        {"customer_id": customer_id, "context": json.dumps(context)},
    )
    return result if isinstance(result, list) else []


def rows_by_case(
    rows: list[dict[str, Any]], case_id_key: str = "customer_case_id"
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get(case_id_key)), []).append(row)
    return grouped


def archive_write_local_file(
    archive: zipfile.ZipFile,
    archive_name: str,
    storage_path: Any,
) -> bool:
    path_value = str(storage_path or "")
    if not path_value:
        return False
    path = Path(path_value)
    try:
        resolved_path = path.resolve(strict=True)
        upload_root = UPLOAD_ROOT.resolve(strict=False)
    except OSError:
        return False
    if not resolved_path.is_relative_to(upload_root) or not resolved_path.is_file():
        return False
    archive.write(resolved_path, archive_name)
    return True


def document_export_filename(row: dict[str, Any]) -> str:
    original_name = export_slug(row.get("original_filename") or row.get("title"), "Dokument")
    suffix = Path(str(row.get("original_filename") or "")).suffix
    if suffix and not original_name.endswith(suffix):
        return f"{original_name}{suffix}"
    return original_name


def add_existing_document_files(
    archive: zipfile.ZipFile,
    root: str,
    rows: list[dict[str, Any]],
) -> int:
    used_names: set[str] = set()
    included_count = 0
    for row in rows:
        case_folder = export_slug(row.get("case_number") or f"Vorgang_{row.get('case_id')}")
        category_folder = CUSTOMER_EXPORT_DOCUMENT_CATEGORY_FOLDERS.get(
            str(row.get("document_category") or ""),
            export_slug(row.get("document_category"), "Dokumente"),
        )
        filename = document_export_filename(row)
        archive_names = [
            f"{root}/01_Vorgaenge/{case_folder}/Dokumente/{category_folder}/{filename}",
        ]
        register_folder = CUSTOMER_EXPORT_REGISTER_FOLDERS.get(str(row.get("register_code") or ""))
        if register_folder:
            archive_names.append(
                f"{root}/01_Vorgaenge/{case_folder}/{register_folder}/Dateien/{filename}"
            )
        unique_archive_names = []
        for archive_name in archive_names:
            if archive_name in used_names:
                archive_name = str(
                    Path(archive_name).with_name(f"{row.get('document_id')}_{filename}")
                )
            used_names.add(archive_name)
            unique_archive_names.append(archive_name)
        if row.get("storage_backend") == "object_storage" and row.get("object_storage_key"):
            file_body = object_storage_request("GET", str(row["object_storage_key"]))
            for archive_name in unique_archive_names:
                archive.writestr(archive_name, file_body)
            included_count += 1
            continue
        written = False
        for archive_name in unique_archive_names:
            written = (
                archive_write_local_file(archive, archive_name, row.get("storage_path"))
                or written
            )
        if written:
            included_count += 1
    return included_count


def add_attachment_files(
    archive: zipfile.ZipFile,
    root: str,
    rows: list[dict[str, Any]],
    register_folder: str,
    subfolder: str,
    attachment_key: str,
    parent_id_key: str,
) -> int:
    included_count = 0
    used_names: set[str] = set()
    for row in rows:
        case_folder = export_slug(
            row.get("case_number") or f"Vorgang_{row.get('customer_case_id')}"
        )
        for attachment in row.get(attachment_key) or []:
            filename = export_slug(
                attachment.get("original_filename"),
                f"Anhang_{attachment.get('id')}",
            )
            suffix = Path(str(attachment.get("original_filename") or "")).suffix
            if suffix and not filename.endswith(suffix):
                filename = f"{filename}{suffix}"
            archive_name = (
                f"{root}/01_Vorgaenge/{case_folder}/{register_folder}/"
                f"{subfolder}/{row.get(parent_id_key)}_{filename}"
            )
            if archive_name in used_names:
                archive_name = str(
                    Path(archive_name).with_name(f"{attachment.get('id')}_{filename}")
                )
            used_names.add(archive_name)
            if archive_write_local_file(archive, archive_name, attachment.get("storage_path")):
                included_count += 1
    return included_count


def add_case_export_directories(archive: zipfile.ZipFile, root: str, case_folder: str) -> None:
    for folder in CUSTOMER_EXPORT_CASE_FOLDERS:
        archive.writestr(f"{root}/01_Vorgaenge/{case_folder}/{folder}/", "")
        archive.writestr(f"{root}/01_Vorgaenge/{case_folder}/{folder}/Dateien/", "")
    for folder in CUSTOMER_EXPORT_DOCUMENT_FOLDERS:
        archive.writestr(f"{root}/01_Vorgaenge/{case_folder}/Dokumente/{folder}/", "")


def documents_for_register(case: dict[str, Any], register_code: str) -> list[dict[str, Any]]:
    documents = case.get("documents") or []
    if register_code == "dokumente":
        return documents
    return [
        document
        for document in documents
        if str(document.get("register_code") or "") == register_code
    ]


def supplier_communications(case: dict[str, Any]) -> list[dict[str, Any]]:
    communications: list[dict[str, Any]] = []
    for confirmation in case.get("supplier_order_confirmations") or []:
        for communication in confirmation.get("communications") or []:
            communications.append(
                {
                    **communication,
                    "confirmation_id": confirmation.get("id"),
                    "supplier_name": confirmation.get("supplier_name"),
                    "confirmation_number": confirmation.get("confirmation_number"),
                }
            )
    return communications


def case_register_payload(
    case: dict[str, Any],
    register_code: str,
    tasks: list[dict[str, Any]],
    emails: list[dict[str, Any]],
) -> dict[str, Any]:
    sections = case.get("sections") or {}
    payload: dict[str, Any] = {
        "register_code": register_code,
        "register_label": CUSTOMER_EXPORT_REGISTER_LABELS[register_code],
        "case": {
            "id": case.get("id"),
            "case_number": case.get("case_number"),
            "case_title": case.get("case_title"),
            "case_status": case.get("case_status"),
            "status_phase": case.get("status_phase"),
            "status_phase_name": case.get("status_phase_name"),
            "carat_order_number": case.get("carat_order_number"),
        },
        "documents": documents_for_register(case, register_code),
    }
    if register_code in {"anfrage", "planung"}:
        payload["project_objects"] = sections.get("project_objects") or {}
    if register_code == "beratung":
        payload["project_contacts"] = sections.get("project_contacts") or {}
    if register_code in {"angebot_auftrag", "rechnung_abschluss"}:
        payload["document_section"] = sections.get("documents") or {}
    if register_code == "planung":
        payload["carat_imports"] = case.get("carat_imports") or []
    if register_code == "abwicklung":
        payload["process_control"] = sections.get("process_control") or {}
        payload["tasks"] = tasks
        payload["supplier_orders"] = case.get("supplier_orders") or []
        payload["supplier_order_confirmations"] = (
            case.get("supplier_order_confirmations") or []
        )
    if register_code == "rechnung_abschluss":
        payload["supplier_order_confirmations"] = (
            case.get("supplier_order_confirmations") or []
        )
    if register_code == "kommunikation":
        payload["notes"] = case.get("notes") or []
        payload["emails"] = emails
        payload["supplier_communications"] = supplier_communications(case)
    if register_code == "dokumente":
        payload["document_section"] = sections.get("documents") or {}
        payload["document_count"] = len(payload["documents"])
    return payload


def register_export_pdf_lines(payload: dict[str, Any]) -> list[str]:
    case = payload.get("case") or {}
    lines = [
        f"Register: {payload.get('register_label')}",
        f"Vorgangsnummer: {case.get('case_number') or 'ohne Nummer'}",
        f"Titel: {case.get('case_title') or 'Kuechenprojekt'}",
        f"Status: {case.get('status_phase_name') or case.get('case_status') or ''}",
        f"Dokumente: {len(payload.get('documents') or [])}",
    ]
    for key, label in [
        ("project_objects", "Projektgrundlagen"),
        ("project_contacts", "Kontakte"),
        ("document_section", "Dokumentenregister"),
        ("process_control", "Prozesssteuerung"),
    ]:
        value = payload.get(key)
        if isinstance(value, dict) and value:
            lines.append(f"{label}: {len(value)} Felder")
    for key, label in [
        ("tasks", "Aufgaben"),
        ("notes", "Notizen"),
        ("emails", "E-Mails"),
        ("carat_imports", "CARAT-Importe"),
        ("supplier_orders", "Lieferantenbestellungen"),
        ("supplier_order_confirmations", "Lieferanten-AB"),
        ("supplier_communications", "Lieferantenkommunikation"),
    ]:
        value = payload.get(key)
        if isinstance(value, list):
            lines.append(f"{label}: {len(value)}")
    documents = payload.get("documents") or []
    for document in documents[:12]:
        lines.append(
            " - Dokument: "
            + str(
                document.get("title")
                or document.get("original_filename")
                or document.get("id")
                or ""
            )
        )
    return lines


def add_case_register_exports(
    archive: zipfile.ZipFile,
    root: str,
    case: dict[str, Any],
    tasks: list[dict[str, Any]],
    emails: list[dict[str, Any]],
) -> None:
    case_folder = export_slug(case.get("case_number") or f"Vorgang_{case.get('id')}")
    for register_code, label, folder in CUSTOMER_EXPORT_CASE_REGISTERS:
        payload = case_register_payload(case, register_code, tasks, emails)
        register_root = f"{root}/01_Vorgaenge/{case_folder}/{folder}"
        archive.writestr(
            f"{register_root}/register.json",
            json.dumps(payload, ensure_ascii=False, indent=2),
        )
        archive.writestr(
            f"{register_root}/Registerakte.pdf",
            simple_pdf(
                f"{label} {case.get('case_number') or ''}",
                register_export_pdf_lines(payload),
            ),
        )


def customer_file_export(customer_id: str, access_email: str) -> dict[str, Any]:
    context = require_primary_user(access_email)
    state = customers_state(access_email)
    customer = next(
        (item for item in state.get("customers", []) if str(item.get("id")) == str(customer_id)),
        None,
    )
    if not customer:
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_not_found")

    exported_at = export_timestamp(berlin_now())
    customer_cases = [
        case
        for case in state.get("customer_cases", [])
        if str(case.get("customer_id")) == str(customer.get("id"))
    ]
    document_rows = customer_export_document_rows(customer_id, context)
    task_rows = customer_export_task_rows(customer_id, context)
    email_rows = customer_export_email_rows(customer_id, context)
    tasks_by_case = rows_by_case(task_rows)
    emails_by_case = rows_by_case(email_rows)
    export_metadata = {
        "last_exported_at": exported_at,
        "last_exported_by": access_email,
        "scope": "customer_file",
        "format": "zip",
    }
    customer.setdefault("file_sections", {})[CUSTOMER_EXPORT_SECTION_CODE] = export_metadata

    root = export_folder(customer)
    filename = f"Kundenakte_{root}_{berlin_now().strftime('%Y-%m-%d_%H-%M')}.zip"
    payload = {
        "export": export_metadata,
        "customer": customer,
        "cases": customer_cases,
        "registers": CUSTOMER_EXPORT_CASE_REGISTERS,
        "tasks": task_rows,
        "emails": email_rows,
        "document_files_included": 0,
        "task_attachment_files_included": 0,
        "email_attachment_files_included": 0,
    }

    buffer = BytesIO()
    pdf_title = customer.get("display_name") or customer.get("customer_number") or customer_id
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            f"{root}/00_Stammdaten/Kundenakte_{root}.pdf",
            simple_pdf(
                f"Kundenakte {pdf_title}",
                customer_export_pdf_lines(customer, customer_cases, exported_at),
            ),
        )
        archive.writestr(
            f"{root}/00_Stammdaten/customer.json",
            json.dumps(customer, ensure_ascii=False, indent=2),
        )
        archive.writestr(
            f"{root}/01_Vorgaenge/customer_cases.json",
            json.dumps(customer_cases, ensure_ascii=False, indent=2),
        )
        for case in customer_cases:
            case_folder = export_slug(case.get("case_number") or f"Vorgang_{case.get('id')}")
            add_case_export_directories(archive, root, case_folder)
            archive.writestr(
                f"{root}/01_Vorgaenge/{case_folder}/Vorgangsakte.pdf",
                simple_pdf(
                    case.get("case_title") or case.get("case_number") or "Vorgangsakte",
                    [
                        f"Vorgangsnummer: {case.get('case_number') or 'ohne Nummer'}",
                        f"CARAT: {case.get('carat_order_number') or 'Nicht hinterlegt'}",
                        f"Status: {case.get('status_phase_name') or case.get('case_status') or ''}",
                        f"Dokumente: {len(case.get('documents') or [])}",
                        f"Notizen: {len(case.get('notes') or [])}",
                    ],
                ),
            )
            archive.writestr(
                f"{root}/01_Vorgaenge/{case_folder}/metadata.json",
                json.dumps(case, ensure_ascii=False, indent=2),
            )
            add_case_register_exports(
                archive,
                root,
                case,
                tasks_by_case.get(str(case.get("id")), []),
                emails_by_case.get(str(case.get("id")), []),
            )
        payload["document_files_included"] = add_existing_document_files(
            archive,
            root,
            document_rows,
        )
        payload["task_attachment_files_included"] = add_attachment_files(
            archive,
            root,
            task_rows,
            CUSTOMER_EXPORT_REGISTER_FOLDERS["abwicklung"],
            "Aufgaben_Anhaenge",
            "attachments",
            "id",
        )
        payload["email_attachment_files_included"] = add_attachment_files(
            archive,
            root,
            email_rows,
            CUSTOMER_EXPORT_REGISTER_FOLDERS["kommunikation"],
            "E-Mail_Anhaenge",
            "attachments",
            "id",
        )
        archive.writestr(
            f"{root}/metadata.json",
            json.dumps(payload, ensure_ascii=False, indent=2),
        )

    save_customer_section(customer_id, CUSTOMER_EXPORT_SECTION_CODE, export_metadata, access_email)
    return {
        "filename": filename,
        "content_type": "application/zip",
        "body": buffer.getvalue(),
    }


def save_customer_case(
    case_id: str,
    data: dict[str, Any],
    access_email: str,
) -> dict[str, Any]:
    context = require_primary_user(access_email)
    payload = {
        "case_id": case_id,
        "case_title": str(data.get("case_title", "")).strip(),
        "carat_order_number": normalize_carat_order_number(data.get("carat_order_number", "")),
        "case_status": str(data.get("case_status", "active")).strip() or "active",
        "status_phase_id": str(data.get("status_phase_id") or "").strip(),
        "responsible_user_id": str(
            data.get("responsible_user_id")
            or data.get("owner_user_id")
            or context["primary_user_id"]
        ).strip(),
        "context": context,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_case AS (
          SELECT cc.id
          FROM app.customer_cases cc
          LEFT JOIN app.customers c ON c.id = cc.customer_id
          WHERE cc.id = NULLIF((SELECT data->>'case_id' FROM payload), '')::bigint
            AND cc.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        updated AS (
          UPDATE app.customer_cases cc
          SET
            case_title = NULLIF(data->>'case_title', ''),
            carat_order_number = NULLIF(data->>'carat_order_number', ''),
            case_status = data->>'case_status',
            status_phase_id = NULLIF(data->>'status_phase_id', '')::smallint,
            status_phase = NULLIF(data->>'status_phase_id', '')::smallint,
            responsible_user_id = NULLIF(data->>'responsible_user_id', '')::bigint,
            owner_user_id = COALESCE(
              cc.owner_user_id,
              NULLIF(data->>'responsible_user_id', '')::bigint
            ),
            updated_at = now()
          FROM payload
          WHERE cc.id = (SELECT id FROM visible_case)
          RETURNING cc.id
        )
        SELECT jsonb_build_object('ok', TRUE, 'case_id', (SELECT id FROM updated))::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("case_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_case_not_found")
    return result


def create_customer_case(data: dict[str, Any], access_email: str) -> dict[str, Any]:
    context = require_primary_user(access_email)
    payload = {
        "customer_id": str(data.get("customer_id") or "").strip(),
        "case_number": generate_case_number(),
        "case_title": str(data.get("case_title", "")).strip(),
        "carat_order_number": normalize_carat_order_number(data.get("carat_order_number", "")),
        "case_type": str(data.get("case_type", "")).strip(),
        "case_status": str(data.get("case_status", "active")).strip() or "active",
        "status_phase_id": str(data.get("status_phase_id") or "1").strip(),
        "responsible_user_id": str(
            data.get("responsible_user_id")
            or data.get("owner_user_id")
            or context["primary_user_id"]
        ).strip(),
        "actor_user_id": context["primary_user_id"],
        "context": context,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_customer AS (
          SELECT c.id, c.display_name, c.customer_type, c.owner_user_id
          FROM app.customers c
          WHERE c.id = NULLIF((SELECT data->>'customer_id' FROM payload), '')::bigint
            AND c.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        created AS (
          INSERT INTO app.customer_cases (
            case_number,
            customer_display_name,
            status_phase,
            owner_user_id,
            customer_id,
            case_title,
            case_type,
            carat_order_number,
            case_status,
            status_phase_id,
            created_by_user_id,
            responsible_user_id
          )
          SELECT
            data->>'case_number',
            visible_customer.display_name,
            NULLIF(data->>'status_phase_id', '')::smallint,
            COALESCE(
              NULLIF(data->>'responsible_user_id', '')::bigint,
              visible_customer.owner_user_id
            ),
            visible_customer.id,
            NULLIF(data->>'case_title', ''),
            CASE
              WHEN NULLIF(data->>'case_type', '') IS NOT NULL THEN data->>'case_type'
              WHEN visible_customer.customer_type = 'company' THEN 'kitchen_project_b2b'
              ELSE 'kitchen_project'
            END,
            NULLIF(data->>'carat_order_number', ''),
            data->>'case_status',
            NULLIF(data->>'status_phase_id', '')::smallint,
            NULLIF(data->>'actor_user_id', '')::bigint,
            COALESCE(
              NULLIF(data->>'responsible_user_id', '')::bigint,
              visible_customer.owner_user_id
            )
          FROM payload, visible_customer
          RETURNING id
        ),
        event AS (
          INSERT INTO app.communication_events (
            event_type,
            customer_case_id,
            actor_user_id,
            title,
            body
          )
          SELECT
            'customer_case_created',
            created.id,
            NULLIF((SELECT data->>'actor_user_id' FROM payload), '')::bigint,
            COALESCE(NULLIF((SELECT data->>'case_title' FROM payload), ''), 'Neuer Vorgang'),
            NULL
          FROM created
        )
        SELECT jsonb_build_object('ok', TRUE, 'case_id', (SELECT id FROM created))::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("case_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_not_found")
    return result


def save_customer_case_section(
    case_id: str,
    section_code: str,
    data: dict[str, Any],
    access_email: str,
) -> dict[str, Any]:
    context = require_primary_user(access_email)
    payload = {
        "case_id": case_id,
        "section_code": section_code,
        "payload_json": {
            key: value
            for key, value in data.items()
            if not key.startswith("_")
        },
        "actor_user_id": context["primary_user_id"],
        "context": context,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_case AS (
          SELECT cc.id
          FROM app.customer_cases cc
          LEFT JOIN app.customers c ON c.id = cc.customer_id
          WHERE cc.id = NULLIF((SELECT data->>'case_id' FROM payload), '')::bigint
            AND cc.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        upserted AS (
          INSERT INTO app.customer_case_sections (
            customer_case_id,
            section_code,
            payload_json,
            updated_by_user_id
          )
          SELECT
            (SELECT id FROM visible_case),
            data->>'section_code',
            data->'payload_json',
            NULLIF(data->>'actor_user_id', '')::bigint
          FROM payload
          WHERE EXISTS (SELECT 1 FROM visible_case)
          ON CONFLICT (customer_case_id, section_code) DO UPDATE
          SET
            payload_json = EXCLUDED.payload_json,
            updated_by_user_id = EXCLUDED.updated_by_user_id,
            updated_at = now()
          RETURNING id
        )
        SELECT jsonb_build_object('ok', TRUE, 'section_id', (SELECT id FROM upserted))::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("section_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_case_not_found")
    return result


def save_customer_case_note(
    case_id: str,
    data: dict[str, Any],
    access_email: str,
) -> dict[str, Any]:
    context = require_primary_user(access_email)
    body = str(data.get("body", "")).strip()
    if not body:
        raise ApiError(HTTPStatus.BAD_REQUEST, "case_note_body_required")
    payload = {
        "case_id": case_id,
        "note_type": str(data.get("note_type", "general")).strip() or "general",
        "body": body,
        "actor_user_id": context["primary_user_id"],
        "context": context,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_case AS (
          SELECT cc.id
          FROM app.customer_cases cc
          LEFT JOIN app.customers c ON c.id = cc.customer_id
          WHERE cc.id = NULLIF((SELECT data->>'case_id' FROM payload), '')::bigint
            AND cc.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        inserted AS (
          INSERT INTO app.customer_case_notes (
            customer_case_id,
            note_type,
            body,
            created_by_user_id
          )
          SELECT
            (SELECT id FROM visible_case),
            data->>'note_type',
            data->>'body',
            NULLIF(data->>'actor_user_id', '')::bigint
          FROM payload
          WHERE EXISTS (SELECT 1 FROM visible_case)
          RETURNING id
        ),
        touched AS (
          UPDATE app.customer_cases cc
          SET updated_at = now()
          WHERE cc.id = (SELECT id FROM visible_case)
        )
        SELECT jsonb_build_object('ok', TRUE, 'note_id', (SELECT id FROM inserted))::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("note_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_case_not_found")
    return result


def normalize_document_choice(
    data: dict[str, Any],
    key: str,
    allowed: set[str],
    default: str,
) -> str:
    value = str(data.get(key, "")).strip()
    return value if value in allowed else default


def visible_customer_case(case_id: str, context: dict[str, Any]) -> dict[str, Any]:
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        )
        SELECT COALESCE((
          SELECT jsonb_build_object(
            'id', cc.id,
            'customer_id', cc.customer_id,
            'case_number', cc.case_number
          )
          FROM app.customer_cases cc
          LEFT JOIN app.customers c ON c.id = cc.customer_id
          WHERE cc.id = NULLIF((SELECT data->>'case_id' FROM payload), '')::bigint
            AND cc.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ), '{}'::jsonb)::text;
        """,
        {"payload": json.dumps({"case_id": case_id, "context": context})},
    )
    if not result.get("id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_case_not_found")
    return result


def create_customer_case_document_metadata(
    case_id: str,
    data: dict[str, Any],
    files: list[FileUpload],
    access_email: str,
) -> dict[str, Any]:
    context = require_primary_user(access_email)
    title = str(data.get("title", "")).strip()
    if not title:
        raise ApiError(HTTPStatus.BAD_REQUEST, "document_title_required")

    visible_case = visible_customer_case(case_id, context)
    upload = first_document_upload(files)
    is_carat_upload = bool(upload and is_carat_prjz_upload(upload))
    document_category = normalize_document_choice(
        data,
        "document_category",
        DOCUMENT_CATEGORIES,
        "from_customer",
    )
    if is_carat_upload:
        document_category = "order_processing"
    register_code = DOCUMENT_CATEGORY_REGISTERS.get(document_category, "anfrage")
    file_payload: dict[str, Any] = {
        "original_filename": None,
        "content_type": None,
        "file_size_bytes": None,
        "storage_backend": "local",
        "object_storage_bucket": None,
        "object_storage_key": None,
        "content_sha256": None,
    }
    if upload:
        content_type = normalize_document_file_type(upload)
        object_key = customer_case_document_object_key(
            int(visible_case.get("customer_id") or 0),
            case_id,
            document_category,
            upload.filename,
        )
        object_storage_request("PUT", object_key, upload.content, content_type)
        file_payload = {
            "original_filename": safe_upload_filename(upload.filename),
            "content_type": content_type,
            "file_size_bytes": len(upload.content),
            "storage_backend": "object_storage",
            "object_storage_bucket": OBJECT_STORAGE_BUCKET,
            "object_storage_key": object_key,
            "content_sha256": sha256_hex(upload.content),
        }

    payload = {
        "case_id": case_id,
        "register_code": register_code,
        "document_category": document_category,
        "document_type": (
            "carat_project"
            if is_carat_upload
            else normalize_document_choice(
                data,
                "document_type",
                DOCUMENT_TYPES,
                "other",
            )
        ),
        "document_status": normalize_document_choice(
            data,
            "document_status",
            DOCUMENT_STATUSES,
            "received",
        ),
        "title": title,
        "note": str(data.get("note", "")).strip(),
        "version_label": str(data.get("version_label", "1")).strip() or "1",
        "replaces_document_id": str(data.get("replaces_document_id", "")).strip(),
        "replace_latest_carat_project": (
            is_carat_upload and str(data.get("carat_upload_mode", "")).strip() == "replace_latest"
        ),
        "actor_user_id": context["primary_user_id"],
        "context": context,
        **file_payload,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_case AS (
          SELECT cc.id
          FROM app.customer_cases cc
          LEFT JOIN app.customers c ON c.id = cc.customer_id
          WHERE cc.id = NULLIF((SELECT data->>'case_id' FROM payload), '')::bigint
            AND cc.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        replacement AS (
          SELECT d.id
          FROM app.customer_case_documents d
          WHERE d.customer_case_id = (SELECT id FROM visible_case)
            AND (
              d.id = NULLIF((SELECT data->>'replaces_document_id' FROM payload), '')::bigint
              OR (
                COALESCE(
                  (SELECT (data->>'replace_latest_carat_project')::boolean FROM payload),
                  FALSE
                )
                AND d.document_type = 'carat_project'
                AND d.document_status <> 'archived'
                AND d.is_current_version = TRUE
              )
            )
          ORDER BY
            CASE
              WHEN d.id = NULLIF((SELECT data->>'replaces_document_id' FROM payload), '')::bigint
                THEN 0
              ELSE 1
            END,
            d.created_at DESC,
            d.id DESC
          LIMIT 1
        ),
        marked_replaced AS (
          UPDATE app.customer_case_documents d
          SET
            document_status = 'replaced',
            is_current_version = FALSE,
            updated_at = now()
          WHERE d.id = (SELECT id FROM replacement)
          RETURNING id
        ),
        replaced_carat_import AS (
          SELECT ci.id
          FROM app.customer_case_carat_imports ci
          WHERE ci.document_id = (SELECT id FROM marked_replaced)
        ),
        canceled_replaced_supplier_orders AS (
          UPDATE app.supplier_orders so
          SET
            status = 'canceled',
            updated_at = now()
          WHERE so.source_carat_import_id IN (SELECT id FROM replaced_carat_import)
            AND so.status <> 'canceled'
          RETURNING id
        ),
        inserted AS (
          INSERT INTO app.customer_case_documents (
            customer_case_id,
            register_code,
            document_category,
            document_type,
            document_status,
            title,
            note,
            version_label,
            is_current_version,
            replaces_document_id,
            original_filename,
            storage_path,
            content_type,
            file_size_bytes,
            storage_backend,
            object_storage_bucket,
            object_storage_key,
            content_sha256,
            uploaded_by_user_id,
            source_system
          )
          SELECT
            (SELECT id FROM visible_case),
            data->>'register_code',
            data->>'document_category',
            data->>'document_type',
            data->>'document_status',
            data->>'title',
            NULLIF(data->>'note', ''),
            data->>'version_label',
            TRUE,
            (SELECT id FROM replacement),
            NULLIF(data->>'original_filename', ''),
            NULL,
            NULLIF(data->>'content_type', ''),
            NULLIF(data->>'file_size_bytes', '')::bigint,
            COALESCE(NULLIF(data->>'storage_backend', ''), 'local'),
            NULLIF(data->>'object_storage_bucket', ''),
            NULLIF(data->>'object_storage_key', ''),
            NULLIF(data->>'content_sha256', ''),
            NULLIF(data->>'actor_user_id', '')::bigint,
            'manual_upload'
          FROM payload
          WHERE EXISTS (SELECT 1 FROM visible_case)
          RETURNING id
        ),
        touched AS (
          UPDATE app.customer_cases cc
          SET updated_at = now()
          WHERE cc.id = (SELECT id FROM visible_case)
        )
        SELECT jsonb_build_object(
          'ok', TRUE,
          'document_id', (SELECT id FROM inserted),
          'canceled_supplier_order_count', (SELECT count(*) FROM canceled_replaced_supplier_orders)
        )::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("document_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_case_not_found")
    if upload and is_carat_prjz_upload(upload):
        store_carat_prjz_analysis(
            int(case_id),
            int(result["document_id"]),
            upload,
            context,
        )
    return result


def store_carat_prjz_analysis(
    case_id: int,
    document_id: int,
    upload: FileUpload,
    context: dict[str, Any],
) -> dict[str, Any]:
    try:
        analysis = parse_prjz_content(upload.content, upload.filename)
        status = "analysis_ready"
        error = None
    except ValueError as exc:
        analysis = {
            "source_filename": safe_upload_filename(upload.filename),
            "parser_version": CARAT_PRJZ_PARSER_VERSION,
            "line_count": 0,
            "suppliers": [],
            "positions": [],
        }
        status = "failed"
        error = str(exc)
    summary = {
        key: value
        for key, value in analysis.items()
        if key not in {"positions"}
    }
    if error:
        summary["error"] = error
    payload = {
        "case_id": case_id,
        "document_id": document_id,
        "parser_version": CARAT_PRJZ_PARSER_VERSION,
        "source_filename": analysis.get("source_filename") or safe_upload_filename(upload.filename),
        "carat_version": analysis.get("carat_version"),
        "project_number": analysis.get("project_number"),
        "project_name": analysis.get("project_name"),
        "customer_name": analysis.get("customer_name"),
        "currency": analysis.get("currency"),
        "supplier_count": len(analysis.get("suppliers") or []),
        "position_count": len(analysis.get("positions") or []),
        "status": status,
        "summary_json": summary,
        "positions": analysis.get("positions") or [],
        "actor_user_id": context.get("primary_user_id"),
    }
    return psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        removed_old_positions AS (
          DELETE FROM app.customer_case_carat_import_positions p
          USING app.customer_case_carat_imports i, payload
          WHERE p.import_id = i.id
            AND i.document_id = (payload.data->>'document_id')::bigint
        ),
        upserted_import AS (
          INSERT INTO app.customer_case_carat_imports (
            customer_case_id,
            document_id,
            parser_version,
            source_filename,
            carat_version,
            project_number,
            project_name,
            customer_name,
            currency,
            supplier_count,
            position_count,
            status,
            summary_json,
            created_by_user_id
          )
          SELECT
            (data->>'case_id')::bigint,
            (data->>'document_id')::bigint,
            data->>'parser_version',
            NULLIF(data->>'source_filename', ''),
            NULLIF(data->>'carat_version', ''),
            NULLIF(data->>'project_number', ''),
            NULLIF(data->>'project_name', ''),
            NULLIF(data->>'customer_name', ''),
            NULLIF(data->>'currency', ''),
            COALESCE((data->>'supplier_count')::integer, 0),
            COALESCE((data->>'position_count')::integer, 0),
            data->>'status',
            data->'summary_json',
            NULLIF(data->>'actor_user_id', '')::bigint
          FROM payload
          ON CONFLICT (document_id) DO UPDATE
          SET
            parser_version = EXCLUDED.parser_version,
            source_filename = EXCLUDED.source_filename,
            carat_version = EXCLUDED.carat_version,
            project_number = EXCLUDED.project_number,
            project_name = EXCLUDED.project_name,
            customer_name = EXCLUDED.customer_name,
            currency = EXCLUDED.currency,
            supplier_count = EXCLUDED.supplier_count,
            position_count = EXCLUDED.position_count,
            status = EXCLUDED.status,
            summary_json = EXCLUDED.summary_json,
            updated_at = now()
          RETURNING id
        ),
        inserted_positions AS (
          INSERT INTO app.customer_case_carat_import_positions (
            import_id,
            source_line,
            position_number,
            supplier_code,
            supplier_name,
            article_code,
            title,
            description,
            quantity,
            dimensions_json,
            raw_json
          )
          SELECT
            (SELECT id FROM upserted_import),
            NULLIF(position->>'source_line', '')::integer,
            NULLIF(position->>'position_number', ''),
            NULLIF(position->>'supplier_code', ''),
            NULLIF(position->>'supplier_name', ''),
            NULLIF(position->>'article_code', ''),
            COALESCE(NULLIF(position->>'title', ''), 'CARAT Position'),
            NULLIF(position->>'description', ''),
            NULLIF(position->>'quantity', '')::numeric,
            COALESCE(position->'dimensions', '{}'::jsonb),
            position
          FROM payload,
          LATERAL jsonb_array_elements(data->'positions') AS position
          RETURNING import_id
        )
        SELECT jsonb_build_object(
          'ok', TRUE,
          'import_id', (SELECT id FROM upserted_import),
          'position_count', (SELECT count(*) FROM inserted_positions)
        )::text;
        """,
        {"payload": json.dumps(payload)},
    )


def download_customer_case_document(
    case_id: str,
    document_id: str,
    access_email: str,
) -> dict[str, Any]:
    context = require_primary_user(access_email)
    payload = {
        "case_id": case_id,
        "document_id": document_id,
        "context": context,
    }
    document = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_case AS (
          SELECT cc.id
          FROM app.customer_cases cc
          LEFT JOIN app.customers c ON c.id = cc.customer_id
          WHERE cc.id = NULLIF((SELECT data->>'case_id' FROM payload), '')::bigint
            AND cc.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        )
        SELECT COALESCE((
          SELECT jsonb_build_object(
            'id', d.id,
            'title', d.title,
            'original_filename', d.original_filename,
            'storage_path', d.storage_path,
            'content_type', d.content_type,
            'storage_backend', d.storage_backend,
            'object_storage_key', d.object_storage_key
          )
          FROM app.customer_case_documents d
          WHERE d.id = NULLIF((SELECT data->>'document_id' FROM payload), '')::bigint
            AND d.customer_case_id = (SELECT id FROM visible_case)
            AND d.document_status <> 'archived'
          LIMIT 1
        ), '{}'::jsonb)::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not document.get("id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_case_document_not_found")

    content_type = str(document.get("content_type") or "application/octet-stream")
    filename = safe_upload_filename(
        str(document.get("original_filename") or document.get("title") or f"dokument-{document_id}")
    )
    if document.get("storage_backend") == "object_storage" and document.get("object_storage_key"):
        return {
            "body": object_storage_request("GET", str(document["object_storage_key"])),
            "content_type": content_type,
            "filename": filename,
        }

    storage_path = str(document.get("storage_path") or "")
    if not storage_path:
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_case_document_file_not_found")
    try:
        resolved_path = Path(storage_path).resolve(strict=True)
        upload_root = UPLOAD_ROOT.resolve(strict=False)
    except OSError as exc:
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_case_document_file_not_found") from exc
    if not resolved_path.is_relative_to(upload_root) or not resolved_path.is_file():
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_case_document_file_not_found")
    return {
        "body": resolved_path.read_bytes(),
        "content_type": content_type,
        "filename": filename,
    }


def archive_customer_case_document(
    case_id: str,
    document_id: str,
    access_email: str,
) -> dict[str, Any]:
    context = require_primary_user(access_email)
    payload = {
        "case_id": case_id,
        "document_id": document_id,
        "actor_user_id": context["primary_user_id"],
        "context": context,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_case AS (
          SELECT cc.id
          FROM app.customer_cases cc
          LEFT JOIN app.customers c ON c.id = cc.customer_id
          WHERE cc.id = NULLIF((SELECT data->>'case_id' FROM payload), '')::bigint
            AND cc.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        archived AS (
          UPDATE app.customer_case_documents d
          SET
            document_status = 'archived',
            is_current_version = FALSE,
            archived_at = now(),
            archived_by_user_id = NULLIF((SELECT data->>'actor_user_id' FROM payload), '')::bigint,
            updated_at = now()
          WHERE d.id = NULLIF((SELECT data->>'document_id' FROM payload), '')::bigint
            AND d.customer_case_id = (SELECT id FROM visible_case)
          RETURNING id
        ),
        touched AS (
          UPDATE app.customer_cases cc
          SET updated_at = now()
          WHERE cc.id = (SELECT id FROM visible_case)
        )
        SELECT jsonb_build_object('ok', TRUE, 'document_id', (SELECT id FROM archived))::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("document_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_case_document_not_found")
    return result


def selected_carat_position_ids(data: dict[str, Any]) -> list[int]:
    ids: list[int] = []
    for key, value in data.items():
        if key.startswith("position_") and normalize_bool(value) == "true":
            raw_id = key.removeprefix("position_")
            if raw_id.isdigit():
                ids.append(int(raw_id))
    return sorted(set(ids))


def sync_supplier_orders_from_carat_selection(
    import_id: int, actor_user_id: int | None
) -> dict[str, Any]:
    payload = {"import_id": import_id, "actor_user_id": actor_user_id}
    return psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        selected_positions AS (
          SELECT
            ci.customer_case_id,
            ci.id AS import_id,
            cip.id AS carat_position_id,
            COALESCE(NULLIF(cip.supplier_name, ''), 'Ohne Lieferant') AS supplier_name,
            lower(regexp_replace(
              COALESCE(NULLIF(cip.supplier_name, ''), 'Ohne Lieferant'),
              '[^[:alnum:]]+',
              ' ',
              'g'
            )) AS normalized_supplier_name,
            cip.position_number,
            cip.article_code,
            cip.title,
            cip.description,
            cip.quantity,
            cip.raw_json
          FROM app.customer_case_carat_imports ci
          JOIN app.customer_case_carat_import_positions cip ON cip.import_id = ci.id
          WHERE ci.id = (SELECT (data->>'import_id')::bigint FROM payload)
            AND cip.selection_status IN ('selected', 'transferred')
            AND btrim(lower(regexp_replace(
              COALESCE(NULLIF(cip.supplier_name, ''), 'Ohne Lieferant'),
              '[^[:alnum:]]+',
              ' ',
              'g'
            ))) <> 'bilddaten'
            AND NOT (
              COALESCE(cip.article_code, '') = '46000000000'
              AND btrim(lower(regexp_replace(COALESCE(cip.title, ''), '[^[:alnum:]]+', ' ', 'g')))
                ~ '^(decke|wand [0-9]+)$'
            )
        ),
        upserted_suppliers AS (
          INSERT INTO app.suppliers (name, normalized_name)
          SELECT DISTINCT supplier_name, normalized_supplier_name
          FROM selected_positions
          ON CONFLICT (normalized_name) DO UPDATE
          SET name = EXCLUDED.name,
              updated_at = now()
          RETURNING id, normalized_name
        ),
        all_suppliers AS (
          SELECT id, normalized_name FROM upserted_suppliers
          UNION
          SELECT s.id, s.normalized_name
          FROM app.suppliers s
          JOIN selected_positions sp ON sp.normalized_supplier_name = s.normalized_name
        ),
        upserted_orders AS (
          INSERT INTO app.supplier_orders (
            customer_case_id,
            supplier_id,
            source_carat_import_id,
            order_number,
            title,
            status,
            created_by_user_id
          )
          SELECT DISTINCT
            sp.customer_case_id,
            s.id,
            sp.import_id,
            cc.carat_order_number,
            sp.supplier_name || ' Bestellung',
            'ordered',
            NULLIF((SELECT data->>'actor_user_id' FROM payload), '')::bigint
          FROM selected_positions sp
          JOIN all_suppliers s ON s.normalized_name = sp.normalized_supplier_name
          JOIN app.customer_cases cc ON cc.id = sp.customer_case_id
          WHERE NOT EXISTS (
            SELECT 1
            FROM app.supplier_orders existing
            WHERE existing.customer_case_id = sp.customer_case_id
              AND existing.supplier_id = s.id
              AND existing.source_carat_import_id = sp.import_id
          )
          RETURNING id
        ),
        affected_orders AS (
          SELECT so.id
          FROM app.supplier_orders so
          WHERE so.source_carat_import_id = (SELECT (data->>'import_id')::bigint FROM payload)
        ),
        removed_positions AS (
          DELETE FROM app.supplier_order_positions sop
          WHERE sop.supplier_order_id IN (SELECT id FROM affected_orders)
            AND sop.source_carat_position_id IS NOT NULL
        ),
        inserted_positions AS (
          INSERT INTO app.supplier_order_positions (
            supplier_order_id,
            source_carat_position_id,
            position_number,
            article_code,
            title,
            description,
            quantity,
            raw_json
          )
          SELECT
            so.id,
            sp.carat_position_id,
            sp.position_number,
            sp.article_code,
            sp.title,
            sp.description,
            sp.quantity,
            sp.raw_json
          FROM selected_positions sp
          JOIN all_suppliers s ON s.normalized_name = sp.normalized_supplier_name
          JOIN app.supplier_orders so ON so.customer_case_id = sp.customer_case_id
            AND so.supplier_id = s.id
            AND so.source_carat_import_id = sp.import_id
          RETURNING supplier_order_id
        ),
        updated_counts AS (
          UPDATE app.supplier_orders so
          SET
            ordered_position_count = (
              SELECT count(*)
              FROM app.supplier_order_positions sop
              WHERE sop.supplier_order_id = so.id
            ),
            updated_at = now()
          WHERE so.id IN (SELECT id FROM affected_orders)
          RETURNING so.id
        )
        SELECT jsonb_build_object(
          'ok', TRUE,
          'supplier_order_count', (SELECT count(*) FROM updated_counts),
          'supplier_order_position_count', (SELECT count(*) FROM inserted_positions)
        )::text;
        """,
        {"payload": json.dumps(payload)},
    )


def fetch_confirmation_match_context(confirmation_id: int) -> dict[str, Any]:
    return psql_json(
        """
        WITH confirmation AS (
          SELECT *
          FROM app.supplier_order_confirmations
          WHERE id = :'confirmation_id'::bigint
        )
        SELECT jsonb_build_object(
          'confirmation', COALESCE((SELECT to_jsonb(c) FROM confirmation c), '{}'::jsonb),
          'order_positions', COALESCE((
            SELECT jsonb_agg(to_jsonb(op) ORDER BY op.id)
            FROM app.supplier_order_positions op
            WHERE op.supplier_order_id = (SELECT supplier_order_id FROM confirmation)
          ), '[]'::jsonb),
          'confirmation_positions', COALESCE((
            SELECT jsonb_agg(to_jsonb(cp) ORDER BY cp.id)
            FROM app.supplier_order_confirmation_positions cp
            WHERE cp.confirmation_id = :'confirmation_id'::bigint
          ), '[]'::jsonb)
        )::text;
        """,
        {"confirmation_id": str(confirmation_id)},
    )


def exception_payload(
    confirmation_id: int,
    difference_type: str,
    severity: str,
    message: str,
    order_position_id: Any = None,
    confirmation_position_id: Any = None,
    ordered_value: Any = None,
    confirmed_value: Any = None,
    difference_value: Decimal | None = None,
) -> dict[str, Any]:
    return {
        "confirmation_id": confirmation_id,
        "difference_type": difference_type,
        "severity": severity,
        "message": message,
        "order_position_id": order_position_id,
        "confirmation_position_id": confirmation_position_id,
        "ordered_value": None if ordered_value is None else str(ordered_value),
        "confirmed_value": None if confirmed_value is None else str(confirmed_value),
        "difference_value": None if difference_value is None else str(difference_value),
    }


def recompute_supplier_confirmation_matching(confirmation_id: int) -> dict[str, Any]:
    context = fetch_confirmation_match_context(confirmation_id)
    confirmation = context.get("confirmation") or {}
    if not confirmation.get("id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "confirmation_not_found")

    order_positions = context.get("order_positions") or []
    confirmation_positions = context.get("confirmation_positions") or []
    order_by_article = {
        normalize_article_code(position.get("article_code")): position
        for position in order_positions
        if normalize_article_code(position.get("article_code"))
    }
    matched_order_ids: set[int] = set()
    exceptions: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []

    for position in confirmation_positions:
        position_id = int(position["id"])
        article_key = normalize_article_code(position.get("article_code"))
        matched_order = order_by_article.get(article_key) if article_key else None
        position_exceptions: list[dict[str, Any]] = []
        severity = "green"
        match_status = "matched"

        if not matched_order:
            severity = "red"
            match_status = "manual_review_required"
            position_exceptions.append(
                exception_payload(
                    confirmation_id,
                    "extra_position",
                    "red",
                    "AB-Position ist keiner bestellten Position zugeordnet.",
                    confirmation_position_id=position_id,
                    confirmed_value=position.get("article_code") or position.get("title"),
                )
            )
        else:
            matched_order_ids.add(int(matched_order["id"]))
            ordered_quantity = decimal_from(matched_order.get("quantity"))
            confirmed_quantity = decimal_from(position.get("quantity"))
            if ordered_quantity is not None and confirmed_quantity is not None:
                quantity_delta = confirmed_quantity - ordered_quantity
                if quantity_delta != 0:
                    severity = "yellow"
                    match_status = "matched_with_warning"
                    position_exceptions.append(
                        exception_payload(
                            confirmation_id,
                            "quantity",
                            "yellow",
                            "Menge weicht von der Bestellung ab.",
                            matched_order["id"],
                            position_id,
                            ordered_quantity,
                            confirmed_quantity,
                            quantity_delta,
                        )
                    )
            elif ordered_quantity is not None and confirmed_quantity is None:
                severity = "red"
                match_status = "manual_review_required"
                position_exceptions.append(
                    exception_payload(
                        confirmation_id,
                        "unreadable_field",
                        "red",
                        "Menge der AB-Position fehlt oder ist nicht lesbar.",
                        matched_order["id"],
                        position_id,
                        ordered_quantity,
                        None,
                    )
                )

            ordered_price = decimal_from(matched_order.get("ordered_net_price"))
            confirmed_price = decimal_from(position.get("confirmed_net_price"))
            if ordered_price is not None and confirmed_price is not None:
                price_delta = confirmed_price - ordered_price
                if price_delta != 0:
                    severity = "yellow" if severity != "red" else severity
                    match_status = "matched_with_warning"
                    position_exceptions.append(
                        exception_payload(
                            confirmation_id,
                            "net_price",
                            "yellow",
                            "Netto-Preis weicht ab und muss bestätigt werden.",
                            matched_order["id"],
                            position_id,
                            ordered_price,
                            confirmed_price,
                            price_delta,
                        )
                    )
            elif ordered_price is not None and confirmed_price is None:
                severity = "red"
                match_status = "manual_review_required"
                position_exceptions.append(
                    exception_payload(
                        confirmation_id,
                        "unreadable_field",
                        "red",
                        "Netto-Preis der AB-Position fehlt oder ist nicht lesbar.",
                        matched_order["id"],
                        position_id,
                        ordered_price,
                        None,
                    )
                )

            ordered_week = matched_order.get("ordered_delivery_week")
            confirmed_week = position.get("confirmed_delivery_week")
            ordered_date = matched_order.get("ordered_delivery_date")
            confirmed_date = position.get("confirmed_delivery_date")
            if ordered_date and confirmed_date:
                ordered_dt = datetime.strptime(str(ordered_date), "%Y-%m-%d").date()
                confirmed_dt = datetime.strptime(str(confirmed_date), "%Y-%m-%d").date()
                day_delta = (confirmed_dt - ordered_dt).days
                if day_delta >= 7:
                    severity = "red"
                    match_status = "manual_review_required"
                    position_exceptions.append(
                        exception_payload(
                            confirmation_id,
                            "delivery_date",
                            "red",
                            "Liefertermin weicht mindestens eine Woche ab.",
                            matched_order["id"],
                            position_id,
                            ordered_date,
                            confirmed_date,
                            Decimal(day_delta),
                        )
                    )
                elif day_delta > 0:
                    severity = "yellow" if severity != "red" else severity
                    match_status = "matched_with_warning"
                    position_exceptions.append(
                        exception_payload(
                            confirmation_id,
                            "delivery_date",
                            "yellow",
                            "Liefertermin weicht innerhalb des Montagepuffers ab.",
                            matched_order["id"],
                            position_id,
                            ordered_date,
                            confirmed_date,
                            Decimal(day_delta),
                        )
                    )
            elif ordered_week and confirmed_week and str(ordered_week) != str(confirmed_week):
                severity = "yellow" if severity != "red" else severity
                match_status = "matched_with_warning"
                position_exceptions.append(
                    exception_payload(
                        confirmation_id,
                        "delivery_date",
                        "yellow",
                        "Liefer-KW weicht von der Bestellung ab.",
                        matched_order["id"],
                        position_id,
                        ordered_week,
                        confirmed_week,
                    )
                )

        exceptions.extend(position_exceptions)
        updates.append(
            {
                "id": position_id,
                "matched_order_position_id": matched_order.get("id") if matched_order else None,
                "severity": severity,
                "match_status": match_status,
            }
        )

    for order_position in order_positions:
        order_position_id = int(order_position["id"])
        if order_position_id not in matched_order_ids:
            exceptions.append(
                exception_payload(
                    confirmation_id,
                    "missing_position",
                    "red",
                    "Bestellte Position fehlt in der AB.",
                    order_position_id=order_position_id,
                    ordered_value=order_position.get("article_code") or order_position.get("title"),
                )
            )

    matched_position_count = len(matched_order_ids)
    ordered_position_count = len(order_positions)
    confirmation_position_count = len(confirmation_positions)
    unmatched_order_position_count = max(ordered_position_count - matched_position_count, 0)
    unmatched_confirmation_position_count = len(
        [update for update in updates if not update.get("matched_order_position_id")]
    )
    match_rate = (
        Decimal(matched_position_count) / Decimal(ordered_position_count)
        if ordered_position_count
        else Decimal("0")
    )
    status = (
        "context_revision_required"
        if ordered_position_count and matched_position_count == 0
        else "exceptions_open"
        if exceptions
        else "matched"
    )
    payload = {
        "confirmation_id": confirmation_id,
        "updates": updates,
        "exceptions": exceptions,
        "ordered_position_count": ordered_position_count,
        "confirmation_position_count": confirmation_position_count,
        "matched_position_count": matched_position_count,
        "unmatched_order_position_count": unmatched_order_position_count,
        "unmatched_confirmation_position_count": unmatched_confirmation_position_count,
        "match_rate": str(match_rate),
        "status": status,
    }
    return psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        removed_exceptions AS (
          DELETE FROM app.supplier_order_confirmation_exceptions
          WHERE confirmation_id = (SELECT (data->>'confirmation_id')::bigint FROM payload)
        ),
        position_updates AS (
          UPDATE app.supplier_order_confirmation_positions cp
          SET
            matched_order_position_id =
              NULLIF(update_data->>'matched_order_position_id', '')::bigint,
            severity = update_data->>'severity',
            match_status = update_data->>'match_status',
            updated_at = now()
          FROM payload,
          LATERAL jsonb_array_elements(data->'updates') AS update_data
          WHERE cp.id = (update_data->>'id')::bigint
          RETURNING cp.id
        ),
        inserted_exceptions AS (
          INSERT INTO app.supplier_order_confirmation_exceptions (
            confirmation_id,
            confirmation_position_id,
            order_position_id,
            difference_type,
            severity,
            status,
            ordered_value,
            confirmed_value,
            difference_value,
            requires_confirmation,
            message
          )
          SELECT
            (exception->>'confirmation_id')::bigint,
            NULLIF(exception->>'confirmation_position_id', '')::bigint,
            NULLIF(exception->>'order_position_id', '')::bigint,
            exception->>'difference_type',
            exception->>'severity',
            'open',
            NULLIF(exception->>'ordered_value', ''),
            NULLIF(exception->>'confirmed_value', ''),
            NULLIF(exception->>'difference_value', '')::numeric,
            TRUE,
            exception->>'message'
          FROM payload,
          LATERAL jsonb_array_elements(data->'exceptions') AS exception
        ),
        updated_confirmation AS (
          UPDATE app.supplier_order_confirmations soc
          SET
            status = (SELECT data->>'status' FROM payload),
            ordered_position_count =
              (SELECT (data->>'ordered_position_count')::integer FROM payload),
            confirmation_position_count =
              (SELECT (data->>'confirmation_position_count')::integer FROM payload),
            matched_position_count =
              (SELECT (data->>'matched_position_count')::integer FROM payload),
            unmatched_order_position_count =
              (SELECT (data->>'unmatched_order_position_count')::integer FROM payload),
            unmatched_confirmation_position_count =
              (SELECT (data->>'unmatched_confirmation_position_count')::integer FROM payload),
            match_rate = (SELECT (data->>'match_rate')::numeric FROM payload),
            updated_at = now()
          WHERE soc.id = (SELECT (data->>'confirmation_id')::bigint FROM payload)
          RETURNING soc.id, soc.status
        ),
        updated_inbox AS (
          UPDATE app.supplier_confirmation_inbox_items inbox
          SET
            status = CASE
              WHEN (SELECT status FROM updated_confirmation) = 'context_revision_required'
                THEN 'context_revision_required'
              ELSE 'matching_complete'
            END,
            review_required = EXISTS (
              SELECT 1
              FROM app.supplier_order_confirmation_exceptions ex
              WHERE ex.confirmation_id = (SELECT id FROM updated_confirmation)
                AND ex.status = 'open'
            ),
            review_reason = CASE
              WHEN (SELECT status FROM updated_confirmation) = 'context_revision_required'
                THEN 'possible_wrong_context'
              ELSE review_reason
            END,
            updated_at = now()
          FROM app.supplier_order_confirmations soc
          WHERE soc.id = (SELECT id FROM updated_confirmation)
            AND inbox.id = soc.inbox_item_id
        )
        SELECT jsonb_build_object(
          'ok', TRUE,
          'confirmation_id', (SELECT id FROM updated_confirmation),
          'status', (SELECT status FROM updated_confirmation),
          'exception_count', jsonb_array_length((SELECT data->'exceptions' FROM payload))
        )::text;
        """,
        {"payload": json.dumps(payload)},
    )


def create_supplier_order_confirmation(
    case_id: str,
    data: dict[str, Any],
    access_email: str,
) -> dict[str, Any]:
    context = require_primary_user(access_email)
    positions = parse_confirmation_positions(data.get("confirmation_positions"))
    payload = {
        "case_id": case_id,
        "supplier_order_id": str(data.get("supplier_order_id", "")).strip(),
        "document_id": str(data.get("document_id", "")).strip(),
        "confirmation_number": str(data.get("confirmation_number", "")).strip(),
        "positions": positions,
        "actor_user_id": context["primary_user_id"],
        "context": context,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_case AS (
          SELECT cc.id
          FROM app.customer_cases cc
          LEFT JOIN app.customers c ON c.id = cc.customer_id
          WHERE cc.id = NULLIF((SELECT data->>'case_id' FROM payload), '')::bigint
            AND cc.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        visible_order AS (
          SELECT so.*
          FROM app.supplier_orders so
          WHERE so.id = NULLIF((SELECT data->>'supplier_order_id' FROM payload), '')::bigint
            AND so.customer_case_id = (SELECT id FROM visible_case)
          LIMIT 1
        ),
        inbox AS (
          INSERT INTO app.supplier_confirmation_inbox_items (
            customer_case_id,
            document_id,
            source_type,
            status,
            confirmed_supplier_id,
            confirmed_order_id,
            confirmed_case_id,
            proposal_level,
            review_required,
            created_by_user_id
          )
          SELECT
            (SELECT id FROM visible_case),
            NULLIF(data->>'document_id', '')::bigint,
            'manual_entry',
            'context_confirmed',
            (SELECT supplier_id FROM visible_order),
            (SELECT id FROM visible_order),
            (SELECT id FROM visible_case),
            'strong_order_match',
            FALSE,
            NULLIF(data->>'actor_user_id', '')::bigint
          FROM payload
          WHERE EXISTS (SELECT 1 FROM visible_order)
          RETURNING id
        ),
        confirmation AS (
          INSERT INTO app.supplier_order_confirmations (
            inbox_item_id,
            customer_case_id,
            supplier_order_id,
            supplier_id,
            document_id,
            confirmation_number,
            status,
            created_by_user_id
          )
          SELECT
            (SELECT id FROM inbox),
            (SELECT id FROM visible_case),
            (SELECT id FROM visible_order),
            (SELECT supplier_id FROM visible_order),
            NULLIF(data->>'document_id', '')::bigint,
            NULLIF(data->>'confirmation_number', ''),
            'matching_in_progress',
            NULLIF(data->>'actor_user_id', '')::bigint
          FROM payload
          WHERE EXISTS (SELECT 1 FROM inbox)
          RETURNING id
        ),
        inserted_positions AS (
          INSERT INTO app.supplier_order_confirmation_positions (
            confirmation_id,
            position_number,
            article_code,
            title,
            description,
            quantity,
            confirmed_net_price,
            confirmed_delivery_week,
            confirmed_delivery_date,
            match_status,
            severity,
            raw_json
          )
          SELECT
            (SELECT id FROM confirmation),
            position->>'position_number',
            NULLIF(position->>'article_code', ''),
            COALESCE(NULLIF(position->>'title', ''), 'AB Position'),
            NULLIF(position->>'description', ''),
            NULLIF(position->>'quantity', '')::numeric,
            NULLIF(position->>'confirmed_net_price', '')::numeric,
            NULLIF(position->>'confirmed_delivery_week', ''),
            NULLIF(position->>'confirmed_delivery_date', '')::date,
            'manual_review_required',
            'yellow',
            position
          FROM payload,
          LATERAL jsonb_array_elements(data->'positions') AS position
          WHERE EXISTS (SELECT 1 FROM confirmation)
        )
        SELECT jsonb_build_object(
          'ok', TRUE,
          'confirmation_id', (SELECT id FROM confirmation),
          'position_count', (SELECT count(*) FROM inserted_positions)
        )::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("confirmation_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "supplier_order_not_found")
    recomputed = recompute_supplier_confirmation_matching(int(result["confirmation_id"]))
    return {"ok": True, **result, "matching": recomputed}


def create_supplier_communication_draft(
    confirmation_id: int,
    exception_id: int,
    action: str,
    note: str,
    actor_user_id: int | None,
) -> None:
    communication_type = {
        "request_corrected_ab": "corrected_ab_request",
        "request_price_clarification": "price_clarification",
        "request_delivery_clarification": "delivery_date_clarification",
        "request_alternative_article": "alternative_article_request",
        "request_quantity_clarification": "quantity_position_clarification",
    }.get(action, "general_clarification")
    payload = {
        "confirmation_id": confirmation_id,
        "exception_id": exception_id,
        "communication_type": communication_type,
        "note": note,
        "actor_user_id": actor_user_id,
    }
    psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (
          SELECT
            soc.customer_case_id,
            soc.supplier_id,
            soc.confirmation_number,
            so.order_number,
            s.name AS supplier_name,
            ex.message,
            ex.difference_type
          FROM app.supplier_order_confirmations soc
          JOIN app.supplier_orders so ON so.id = soc.supplier_order_id
          JOIN app.suppliers s ON s.id = soc.supplier_id
          JOIN app.supplier_order_confirmation_exceptions ex ON ex.confirmation_id = soc.id
          WHERE soc.id = (SELECT (data->>'confirmation_id')::bigint FROM payload)
            AND ex.id = (SELECT (data->>'exception_id')::bigint FROM payload)
        ),
        communication AS (
          INSERT INTO app.supplier_communications (
            customer_case_id,
            supplier_id,
            confirmation_id,
            exception_id,
            communication_type,
            status,
            subject,
            body,
            created_by_user_id
          )
          SELECT
            customer_case_id,
            supplier_id,
            (SELECT (data->>'confirmation_id')::bigint FROM payload),
            (SELECT (data->>'exception_id')::bigint FROM payload),
            (SELECT data->>'communication_type' FROM payload),
            'draft',
            'Rückfrage zur Auftragsbestätigung'
              || COALESCE(' ' || NULLIF(confirmation_number, ''), ''),
            'Guten Tag,' || chr(10) || chr(10)
              || 'bitte prüfen Sie folgende Abweichung zu unserer Bestellung'
              || COALESCE(' ' || NULLIF(order_number, ''), '')
              || ':' || chr(10)
              || message || chr(10) || chr(10)
              || COALESCE(
                NULLIF((SELECT data->>'note' FROM payload), ''),
                'Bitte senden Sie uns eine Rückmeldung bzw. korrigierte AB.'
              )
              || chr(10) || chr(10)
              || 'Vielen Dank.',
            NULLIF((SELECT data->>'actor_user_id' FROM payload), '')::bigint
          FROM context
          RETURNING id, customer_case_id, supplier_id
        ),
        follow_up AS (
          INSERT INTO app.supplier_follow_ups (
            customer_case_id,
            supplier_id,
            communication_id,
            confirmation_id,
            title,
            status,
            due_at,
            responsible_user_id
          )
          SELECT
            customer_case_id,
            supplier_id,
            id,
            (SELECT (data->>'confirmation_id')::bigint FROM payload),
            'Lieferantenrückmeldung zur AB prüfen',
            'waiting',
            now() + interval '3 days',
            NULLIF((SELECT data->>'actor_user_id' FROM payload), '')::bigint
          FROM communication
        )
        SELECT jsonb_build_object('ok', TRUE)::text;
        """,
        {"payload": json.dumps(payload)},
    )


def decide_supplier_confirmation_exception(
    confirmation_id: str,
    exception_id: str,
    data: dict[str, Any],
    access_email: str,
) -> dict[str, Any]:
    context = require_primary_user(access_email)
    action = str(data.get("action", "accept")).strip() or "accept"
    note = str(data.get("note", "")).strip()
    if action not in {
        "accept",
        "resolve",
        "reject",
        "request_corrected_ab",
        "request_price_clarification",
        "request_delivery_clarification",
        "request_alternative_article",
        "request_quantity_clarification",
    }:
        raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_exception_action")
    new_status = "accepted" if action == "accept" else "resolved"
    if action == "reject":
        new_status = "rejected"
    if action.startswith("request_"):
        new_status = "waiting_for_supplier"
    payload = {
        "confirmation_id": confirmation_id,
        "exception_id": exception_id,
        "action": action,
        "new_status": new_status,
        "note": note,
        "actor_user_id": context["primary_user_id"],
        "context": context,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_confirmation AS (
          SELECT soc.*
          FROM app.supplier_order_confirmations soc
          JOIN app.customer_cases cc ON cc.id = soc.customer_case_id
          LEFT JOIN app.customers c ON c.id = cc.customer_id
          WHERE soc.id = NULLIF((SELECT data->>'confirmation_id' FROM payload), '')::bigint
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        visible_exception AS (
          SELECT ex.*
          FROM app.supplier_order_confirmation_exceptions ex
          WHERE ex.id = NULLIF((SELECT data->>'exception_id' FROM payload), '')::bigint
            AND ex.confirmation_id = (SELECT id FROM visible_confirmation)
          LIMIT 1
        ),
        updated_exception AS (
          UPDATE app.supplier_order_confirmation_exceptions ex
          SET
            status = (SELECT data->>'new_status' FROM payload),
            resolved_by_user_id = NULLIF((SELECT data->>'actor_user_id' FROM payload), '')::bigint,
            resolved_at = now(),
            resolution_action = (SELECT data->>'action' FROM payload),
            resolution_note = NULLIF((SELECT data->>'note' FROM payload), ''),
            updated_at = now()
          WHERE ex.id = (SELECT id FROM visible_exception)
          RETURNING ex.*
        ),
        decision AS (
          INSERT INTO app.supplier_order_confirmation_decisions (
            confirmation_id,
            exception_id,
            actor_user_id,
            action,
            previous_status,
            new_status,
            ordered_value,
            confirmed_value,
            note
          )
          SELECT
            (SELECT id FROM visible_confirmation),
            (SELECT id FROM visible_exception),
            NULLIF(data->>'actor_user_id', '')::bigint,
            data->>'action',
            (SELECT status FROM visible_exception),
            data->>'new_status',
            (SELECT ordered_value FROM visible_exception),
            (SELECT confirmed_value FROM visible_exception),
            NULLIF(data->>'note', '')
          FROM payload
          WHERE EXISTS (SELECT 1 FROM updated_exception)
          RETURNING id
        ),
        open_exceptions AS (
          SELECT count(*) AS count
          FROM app.supplier_order_confirmation_exceptions ex
          WHERE ex.confirmation_id = (SELECT id FROM visible_confirmation)
            AND ex.status = 'open'
            AND ex.id <> (SELECT id FROM visible_exception)
        ),
        updated_confirmation AS (
          UPDATE app.supplier_order_confirmations soc
          SET
            status = CASE
              WHEN (SELECT data->>'new_status' FROM payload) = 'waiting_for_supplier'
                THEN 'suspended'
              WHEN (SELECT count FROM open_exceptions) = 0
                THEN 'approved'
              ELSE soc.status
            END,
            approved_by_user_id = CASE
              WHEN (SELECT count FROM open_exceptions) = 0
                THEN NULLIF((SELECT data->>'actor_user_id' FROM payload), '')::bigint
              ELSE approved_by_user_id
            END,
            approved_at = CASE
              WHEN (SELECT count FROM open_exceptions) = 0 THEN now()
              ELSE approved_at
            END,
            updated_at = now()
          WHERE soc.id = (SELECT id FROM visible_confirmation)
          RETURNING soc.id, soc.status
        )
        SELECT jsonb_build_object(
          'ok', TRUE,
          'confirmation_id', (SELECT id FROM updated_confirmation),
          'exception_id', (SELECT id FROM updated_exception),
          'confirmation_status', (SELECT status FROM updated_confirmation),
          'decision_id', (SELECT id FROM decision)
        )::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("exception_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "confirmation_exception_not_found")
    if action.startswith("request_"):
        create_supplier_communication_draft(
            int(confirmation_id),
            int(exception_id),
            action,
            note,
            int(context["primary_user_id"]),
        )
    return result


def select_carat_import_positions(
    case_id: str,
    import_id: str,
    data: dict[str, Any],
    access_email: str,
) -> dict[str, Any]:
    context = require_primary_user(access_email)
    position_ids = selected_carat_position_ids(data)
    action = str(data.get("carat_action") or "transfer").strip()
    if action not in {"transfer", "reset"}:
        raise ApiError(HTTPStatus.BAD_REQUEST, "carat_action_invalid")
    payload = {
        "case_id": case_id,
        "import_id": import_id,
        "position_ids": position_ids,
        "action": action,
        "actor_user_id": context["primary_user_id"],
        "context": context,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_case AS (
          SELECT cc.id
          FROM app.customer_cases cc
          LEFT JOIN app.customers c ON c.id = cc.customer_id
          WHERE cc.id = NULLIF((SELECT data->>'case_id' FROM payload), '')::bigint
            AND cc.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR cc.responsible_user_id IN (SELECT id FROM scope_users)
              OR c.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        visible_import AS (
          SELECT ci.id
          FROM app.customer_case_carat_imports ci
          WHERE ci.id = NULLIF((SELECT data->>'import_id' FROM payload), '')::bigint
            AND ci.customer_case_id = (SELECT id FROM visible_case)
          LIMIT 1
        ),
        requested_positions AS (
          SELECT jsonb_array_elements_text(data->'position_ids')::bigint AS id
          FROM payload
        ),
        reset_previous_selection AS (
          UPDATE app.customer_case_carat_import_positions p
          SET
            selection_status = 'candidate',
            selected_by_user_id = NULL,
            selected_at = NULL
          WHERE p.import_id = (SELECT id FROM visible_import)
            AND p.selection_status = 'selected'
            AND (SELECT data->>'action' FROM payload) = 'transfer'
        ),
        reset_requested_positions AS (
          UPDATE app.customer_case_carat_import_positions p
          SET
            selection_status = 'candidate',
            selected_by_user_id = NULL,
            selected_at = NULL
          WHERE p.import_id = (SELECT id FROM visible_import)
            AND p.id IN (SELECT id FROM requested_positions)
            AND p.selection_status IN ('selected', 'transferred')
            AND (SELECT data->>'action' FROM payload) = 'reset'
          RETURNING p.id
        ),
        selected_positions AS (
          UPDATE app.customer_case_carat_import_positions p
          SET
            selection_status = 'selected',
            selected_by_user_id = NULLIF((SELECT data->>'actor_user_id' FROM payload), '')::bigint,
            selected_at = now()
          WHERE p.import_id = (SELECT id FROM visible_import)
            AND p.id IN (SELECT id FROM requested_positions)
            AND p.selection_status = 'candidate'
            AND (SELECT data->>'action' FROM payload) = 'transfer'
          RETURNING p.id
        ),
        import_status AS (
          UPDATE app.customer_case_carat_imports ci
          SET
            status = CASE
              WHEN EXISTS (
                SELECT 1
                FROM app.customer_case_carat_import_positions p
                WHERE p.import_id = (SELECT id FROM visible_import)
                  AND p.selection_status IN ('selected', 'transferred')
              ) THEN 'partially_transferred'
              ELSE 'analysis_ready'
            END,
            updated_at = now()
          WHERE ci.id = (SELECT id FROM visible_import)
        )
        SELECT jsonb_build_object(
          'ok', TRUE,
          'action', (SELECT data->>'action' FROM payload),
          'selected_count', (SELECT count(*) FROM selected_positions),
          'reset_count', (SELECT count(*) FROM reset_requested_positions),
          'import_id', (SELECT id FROM visible_import)
        )::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("import_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "carat_import_not_found")
    result["supplier_orders"] = sync_supplier_orders_from_carat_selection(
        int(result["import_id"]),
        int(context["primary_user_id"]),
    )
    if result.get("action") == "transfer":
        psql_json(
            """
            WITH payload AS (SELECT :'payload'::jsonb AS data),
            transferred AS (
              UPDATE app.customer_case_carat_import_positions p
              SET selection_status = 'transferred'
              FROM payload
              WHERE p.import_id = (data->>'import_id')::bigint
                AND p.selection_status = 'selected'
              RETURNING p.id
            )
            SELECT jsonb_build_object(
              'ok', TRUE,
              'transferred_count', (SELECT count(*) FROM transferred)
            )::text
            FROM payload;
            """,
            {"payload": json.dumps({"import_id": result["import_id"]})},
        )
    return result


def save_task_attachment(task_id: int, upload: FileUpload, uploaded_by_user_id: int) -> None:
    content_type = normalize_attachment_type(upload)
    safe_name = safe_upload_filename(upload.filename)
    task_dir = UPLOAD_ROOT / "tasks" / str(task_id)
    task_dir.mkdir(parents=True, exist_ok=True)
    storage_path = task_dir / f"{uuid4().hex}-{safe_name}"
    storage_path.write_bytes(upload.content)
    psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data)
        INSERT INTO app.task_attachments (
          task_id,
          original_filename,
          storage_path,
          content_type,
          file_size_bytes,
          uploaded_by_user_id
        )
        SELECT
          (data->>'task_id')::bigint,
          data->>'original_filename',
          data->>'storage_path',
          data->>'content_type',
          (data->>'file_size_bytes')::bigint,
          (data->>'uploaded_by_user_id')::bigint
        FROM payload;
        SELECT jsonb_build_object('ok', TRUE)::text;
        """,
        {
            "payload": json.dumps(
                {
                    "task_id": task_id,
                    "original_filename": upload.filename,
                    "storage_path": str(storage_path),
                    "content_type": content_type,
                    "file_size_bytes": len(upload.content),
                    "uploaded_by_user_id": uploaded_by_user_id,
                }
            )
        },
    )


def resolve_customer_case_id(
    data: dict[str, Any],
    access_email: str,
    *,
    required: bool,
) -> str | None:
    context = current_user_context(access_email)
    explicit_value = str(data.get("customer_case_id") or data.get("related_case_id") or "").strip()
    search_value = str(
        data.get("customer_case_search")
        or data.get("customer_display_name")
        or data.get("case_number")
        or ""
    ).strip()
    embedded_id = re.search(r"\[id:(\d+)\]", search_value)
    if embedded_id:
        explicit_value = embedded_id.group(1)
    if explicit_value:
        search_value = explicit_value
    if not search_value:
        if required:
            raise ApiError(HTTPStatus.BAD_REQUEST, "customer_case_required")
        return None

    result = psql_json(
        """
        WITH context AS (
          SELECT :'context'::jsonb AS data
        ),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        candidates AS (
          SELECT cc.id
          FROM app.customer_cases cc
          LEFT JOIN app.customers c ON c.id = cc.customer_id
          WHERE cc.is_active = TRUE
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR EXISTS (
                SELECT 1
                FROM app.tasks t
                JOIN app.task_assignments ta ON ta.task_id = t.id
                WHERE t.related_case_id = cc.id
                  AND ta.user_id IN (SELECT id FROM scope_users)
              )
            )
            AND (
              CASE
                WHEN :'explicit_value' <> '' THEN cc.id = :'explicit_value'::bigint
                ELSE
                  lower(COALESCE(cc.case_number, '')) = lower(:'search_value')
                  OR lower(cc.customer_display_name) = lower(:'search_value')
                  OR lower(COALESCE(c.customer_number, '')) = lower(:'search_value')
                  OR lower(COALESCE(c.primary_email, '')) = lower(:'search_value')
                  OR cc.case_number ILIKE '%' || :'search_value' || '%'
                  OR cc.customer_display_name ILIKE '%' || :'search_value' || '%'
                  OR COALESCE(c.customer_number, '') ILIKE '%' || :'search_value' || '%'
                  OR COALESCE(c.primary_email, '') ILIKE '%' || :'search_value' || '%'
              END
            )
          ORDER BY
            CASE
              WHEN lower(COALESCE(cc.case_number, '')) = lower(:'search_value') THEN 0
              WHEN lower(cc.customer_display_name) = lower(:'search_value') THEN 1
              ELSE 2
            END,
            cc.updated_at DESC
          LIMIT 2
        )
        SELECT jsonb_build_object(
          'count', (SELECT count(*) FROM candidates),
          'id', (SELECT id FROM candidates LIMIT 1)
        )::text;
        """,
        {
            "context": json.dumps(context),
            "explicit_value": explicit_value,
            "search_value": search_value,
        },
    )
    count = int(result.get("count") or 0)
    if count == 0:
        if required:
            raise ApiError(HTTPStatus.NOT_FOUND, "customer_case_not_found")
        return None
    if count > 1 and not explicit_value:
        raise ApiError(HTTPStatus.BAD_REQUEST, "customer_case_search_ambiguous")
    return str(result["id"])


def create_task(data: dict[str, Any], files: list[FileUpload], access_email: str) -> dict[str, Any]:
    context = require_primary_user(access_email)
    actor_user_id = int(context["primary_user_id"])
    assigned_user_id = int(data.get("assigned_user_id") or actor_user_id)
    title = str(data.get("title", "")).strip()
    if not title:
        raise ApiError(HTTPStatus.BAD_REQUEST, "task_title_required")
    related_case_id = resolve_customer_case_id(data, access_email, required=False)
    payload = {
        "title": title,
        "description": str(data.get("description", "")).strip() or None,
        "status_code": str(data.get("status_code", "new")).strip() or "new",
        "priority": str(data.get("priority", "normal")).strip() or "normal",
        "due_at": str(data.get("due_at", "")).strip(),
        "reminder_at": str(data.get("reminder_at", "")).strip(),
        "reminder_email_enabled": normalize_bool(data.get("reminder_email_enabled")),
        "reminder_overview_enabled": normalize_bool(data.get("reminder_overview_enabled", "true")),
        "related_case_id": related_case_id or "",
        "assigned_user_id": assigned_user_id,
        "created_by_user_id": actor_user_id,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        status AS (
          SELECT id
          FROM app.task_statuses
          WHERE code = (SELECT data->>'status_code' FROM payload)
        ),
        inserted_task AS (
          INSERT INTO app.tasks (
            title,
            description,
            status_id,
            priority,
            due_at,
            reminder_at,
            reminder_email_enabled,
            reminder_overview_enabled,
            related_case_id,
            created_by_user_id
          )
          SELECT
            data->>'title',
            NULLIF(data->>'description', ''),
            (SELECT id FROM status),
            data->>'priority',
            NULLIF(data->>'due_at', '')::timestamptz,
            NULLIF(data->>'reminder_at', '')::timestamptz,
            (data->>'reminder_email_enabled')::boolean,
            (data->>'reminder_overview_enabled')::boolean,
            NULLIF(data->>'related_case_id', '')::bigint,
            (data->>'created_by_user_id')::bigint
          FROM payload
          RETURNING id
        ),
        assignment AS (
          INSERT INTO app.task_assignments (task_id, user_id, assigned_by_user_id)
          SELECT
            inserted_task.id,
            (data->>'assigned_user_id')::bigint,
            (data->>'created_by_user_id')::bigint
          FROM inserted_task, payload
          ON CONFLICT (task_id, user_id) DO UPDATE
          SET
            assigned_by_user_id = EXCLUDED.assigned_by_user_id,
            created_at = app.task_assignments.created_at
          RETURNING task_id
        ),
        overview_reminder AS (
          INSERT INTO app.task_reminders (task_id, user_id, remind_at, channel)
          SELECT
            inserted_task.id,
            (data->>'assigned_user_id')::bigint,
            COALESCE(
              NULLIF(data->>'reminder_at', '')::timestamptz,
              NULLIF(data->>'due_at', '')::timestamptz
            ),
            'overview'
          FROM inserted_task, payload
          WHERE (data->>'reminder_overview_enabled')::boolean
            AND COALESCE(NULLIF(data->>'reminder_at', ''), NULLIF(data->>'due_at', '')) IS NOT NULL
          ON CONFLICT DO NOTHING
        ),
        email_reminder AS (
          INSERT INTO app.task_reminders (task_id, user_id, remind_at, channel)
          SELECT
            inserted_task.id,
            (data->>'assigned_user_id')::bigint,
            COALESCE(
              NULLIF(data->>'reminder_at', '')::timestamptz,
              NULLIF(data->>'due_at', '')::timestamptz
            ),
            'email'
          FROM inserted_task, payload
          WHERE (data->>'reminder_email_enabled')::boolean
            AND COALESCE(NULLIF(data->>'reminder_at', ''), NULLIF(data->>'due_at', '')) IS NOT NULL
          ON CONFLICT DO NOTHING
        ),
        event AS (
          INSERT INTO app.communication_events (
            event_type,
            customer_case_id,
            task_id,
            actor_user_id,
            title,
            body
          )
          SELECT
            'task_created',
            NULLIF(data->>'related_case_id', '')::bigint,
            inserted_task.id,
            (data->>'created_by_user_id')::bigint,
            data->>'title',
            NULLIF(data->>'description', '')
          FROM inserted_task, payload
        )
        SELECT jsonb_build_object('ok', TRUE, 'task_id', (SELECT id FROM inserted_task))::text;
        """,
        {"payload": json.dumps(payload)},
    )
    task_id = int(result["task_id"])
    for upload in files:
        if upload.field_name == "attachment":
            save_task_attachment(task_id, upload, actor_user_id)
    return {"ok": True, "task_id": task_id}


def update_task(
    task_id: str,
    data: dict[str, Any],
    files: list[FileUpload],
    access_email: str,
) -> dict[str, Any]:
    context = require_primary_user(access_email)
    actor_user_id = int(context["primary_user_id"])
    assigned_user_id = int(data.get("assigned_user_id") or actor_user_id)
    title = str(data.get("title", "")).strip()
    if not task_id:
        raise ApiError(HTTPStatus.BAD_REQUEST, "task_id_required")
    if not title:
        raise ApiError(HTTPStatus.BAD_REQUEST, "task_title_required")
    related_case_id = resolve_customer_case_id(data, access_email, required=False)
    payload = {
        "task_id": task_id,
        "title": title,
        "description": str(data.get("description", "")).strip() or None,
        "status_code": str(data.get("status_code", "new")).strip() or "new",
        "priority": str(data.get("priority", "normal")).strip() or "normal",
        "due_at": str(data.get("due_at", "")).strip(),
        "reminder_at": str(data.get("reminder_at", "")).strip(),
        "reminder_email_enabled": normalize_bool(data.get("reminder_email_enabled")),
        "reminder_overview_enabled": normalize_bool(data.get("reminder_overview_enabled", "true")),
        "related_case_id": related_case_id or "",
        "assigned_user_id": assigned_user_id,
        "actor_user_id": actor_user_id,
        "context": context,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_task AS (
          SELECT t.id
          FROM app.tasks t
          LEFT JOIN app.task_assignments ta ON ta.task_id = t.id
          WHERE t.id = (SELECT (data->>'task_id')::bigint FROM payload)
            AND t.deleted_at IS NULL
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR t.created_by_user_id IN (SELECT id FROM scope_users)
              OR ta.user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        status AS (
          SELECT id
          FROM app.task_statuses
          WHERE code = (SELECT data->>'status_code' FROM payload)
        ),
        updated_task AS (
          UPDATE app.tasks t
          SET
            title = data->>'title',
            description = NULLIF(data->>'description', ''),
            status_id = (SELECT id FROM status),
            priority = data->>'priority',
            due_at = NULLIF(data->>'due_at', '')::timestamptz,
            reminder_at = NULLIF(data->>'reminder_at', '')::timestamptz,
            reminder_email_enabled = (data->>'reminder_email_enabled')::boolean,
            reminder_overview_enabled = (data->>'reminder_overview_enabled')::boolean,
            related_case_id = NULLIF(data->>'related_case_id', '')::bigint
          FROM payload
          WHERE t.id = (SELECT id FROM visible_task)
          RETURNING t.id, t.related_case_id
        ),
        deleted_assignments AS (
          DELETE FROM app.task_assignments ta
          WHERE ta.task_id = (SELECT id FROM updated_task)
            AND ta.user_id <> (SELECT (data->>'assigned_user_id')::bigint FROM payload)
        ),
        assignment AS (
          INSERT INTO app.task_assignments (task_id, user_id, assigned_by_user_id)
          SELECT
            updated_task.id,
            (data->>'assigned_user_id')::bigint,
            (data->>'actor_user_id')::bigint
          FROM updated_task, payload
          ON CONFLICT (task_id, user_id) DO UPDATE
          SET
            assigned_by_user_id = EXCLUDED.assigned_by_user_id,
            created_at = app.task_assignments.created_at
        ),
        deleted_reminders AS (
          DELETE FROM app.task_reminders tr
          WHERE tr.task_id = (SELECT id FROM updated_task)
        ),
        overview_reminder AS (
          INSERT INTO app.task_reminders (task_id, user_id, remind_at, channel)
          SELECT
            updated_task.id,
            (data->>'assigned_user_id')::bigint,
            COALESCE(
              NULLIF(data->>'reminder_at', '')::timestamptz,
              NULLIF(data->>'due_at', '')::timestamptz
            ),
            'overview'
          FROM updated_task, payload
          WHERE (data->>'reminder_overview_enabled')::boolean
            AND COALESCE(NULLIF(data->>'reminder_at', ''), NULLIF(data->>'due_at', '')) IS NOT NULL
          ON CONFLICT DO NOTHING
        ),
        email_reminder AS (
          INSERT INTO app.task_reminders (task_id, user_id, remind_at, channel)
          SELECT
            updated_task.id,
            (data->>'assigned_user_id')::bigint,
            COALESCE(
              NULLIF(data->>'reminder_at', '')::timestamptz,
              NULLIF(data->>'due_at', '')::timestamptz
            ),
            'email'
          FROM updated_task, payload
          WHERE (data->>'reminder_email_enabled')::boolean
            AND COALESCE(NULLIF(data->>'reminder_at', ''), NULLIF(data->>'due_at', '')) IS NOT NULL
          ON CONFLICT DO NOTHING
        ),
        event AS (
          INSERT INTO app.communication_events (
            event_type,
            customer_case_id,
            task_id,
            actor_user_id,
            title,
            body
          )
          SELECT
            'task_updated',
            updated_task.related_case_id,
            updated_task.id,
            (data->>'actor_user_id')::bigint,
            data->>'title',
            NULLIF(data->>'description', '')
          FROM updated_task, payload
        )
        SELECT jsonb_build_object('ok', TRUE, 'task_id', (SELECT id FROM updated_task))::text;
        """,
        {"payload": json.dumps(payload)},
    )
    updated_task_id = result.get("task_id")
    if not updated_task_id:
        raise ApiError(HTTPStatus.NOT_FOUND, "task_not_found")
    for upload in files:
        if upload.field_name == "attachment":
            save_task_attachment(int(updated_task_id), upload, actor_user_id)
    return {"ok": True, "task_id": updated_task_id}


def set_task_lifecycle(task_id: str, action: str, access_email: str) -> dict[str, Any]:
    context = require_primary_user(access_email)
    actor_user_id = int(context["primary_user_id"])
    if action not in {"archive", "delete"}:
        raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_task_action")
    payload = {
        "task_id": task_id,
        "actor_user_id": actor_user_id,
        "context": context,
        "action": action,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_task AS (
          SELECT t.id, t.related_case_id, t.title
          FROM app.tasks t
          LEFT JOIN app.task_assignments ta ON ta.task_id = t.id
          WHERE t.id = (SELECT (data->>'task_id')::bigint FROM payload)
            AND t.deleted_at IS NULL
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR t.created_by_user_id IN (SELECT id FROM scope_users)
              OR ta.user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        updated_task AS (
          UPDATE app.tasks t
          SET
            archived_at = CASE
              WHEN (SELECT data->>'action' FROM payload) = 'archive' THEN now()
              ELSE t.archived_at
            END,
            archived_by_user_id = CASE
              WHEN (SELECT data->>'action' FROM payload) = 'archive'
              THEN (SELECT (data->>'actor_user_id')::bigint FROM payload)
              ELSE t.archived_by_user_id
            END,
            deleted_at = CASE
              WHEN (SELECT data->>'action' FROM payload) = 'delete' THEN now()
              ELSE t.deleted_at
            END,
            deleted_by_user_id = CASE
              WHEN (SELECT data->>'action' FROM payload) = 'delete'
              THEN (SELECT (data->>'actor_user_id')::bigint FROM payload)
              ELSE t.deleted_by_user_id
            END
          WHERE t.id = (SELECT id FROM visible_task)
          RETURNING t.id
        ),
        event AS (
          INSERT INTO app.communication_events (
            event_type,
            customer_case_id,
            task_id,
            actor_user_id,
            title
          )
          SELECT
            CASE
              WHEN (data->>'action') = 'archive' THEN 'task_archived'
              ELSE 'task_moved_to_trash'
            END,
            visible_task.related_case_id,
            visible_task.id,
            (data->>'actor_user_id')::bigint,
            visible_task.title
          FROM payload, visible_task
          WHERE EXISTS (SELECT 1 FROM updated_task)
        )
        SELECT jsonb_build_object('ok', TRUE, 'task_id', (SELECT id FROM updated_task))::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("task_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "task_not_found")
    return {"ok": True, "task_id": result["task_id"], "action": action}


def assign_email(data: dict[str, Any], access_email: str) -> dict[str, Any]:
    context = require_primary_user(access_email)
    actor_user_id = int(context["primary_user_id"])
    email_message_id = str(data.get("email_message_id", "")).strip()
    case_id = resolve_customer_case_id(data, access_email, required=True)
    if not email_message_id:
        raise ApiError(HTTPStatus.BAD_REQUEST, "email_message_id_required")
    payload = {
        "email_message_id": email_message_id,
        "customer_case_id": case_id,
        "actor_user_id": actor_user_id,
        "context": context,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        target_case AS (
          SELECT cc.id
          FROM app.customer_cases cc
          WHERE cc.id = (SELECT (data->>'customer_case_id')::bigint FROM payload)
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
              OR EXISTS (
                SELECT 1
                FROM app.tasks t
                JOIN app.task_assignments ta ON ta.task_id = t.id
                WHERE t.related_case_id = cc.id
                  AND ta.user_id IN (SELECT id FROM scope_users)
              )
            )
          LIMIT 1
        ),
        visible_email AS (
          SELECT em.id, em.subject
          FROM app.email_messages em
          LEFT JOIN app.email_case_links ecl ON ecl.email_message_id = em.id
          LEFT JOIN app.customer_cases cc ON cc.id = ecl.customer_case_id
          WHERE em.id = (SELECT (data->>'email_message_id')::bigint FROM payload)
            AND em.deleted_at IS NULL
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR em.assigned_user_id IS NULL
              OR em.assigned_user_id IN (SELECT id FROM scope_users)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        link AS (
          INSERT INTO app.email_case_links (
            email_message_id,
            customer_case_id,
            assigned_by_user_id
          )
          SELECT
            visible_email.id,
            target_case.id,
            (data->>'actor_user_id')::bigint
          FROM payload, target_case, visible_email
          ON CONFLICT DO NOTHING
        ),
        updated_email AS (
          UPDATE app.email_messages em
          SET
            is_unassigned = FALSE,
            assigned_user_id = (data->>'actor_user_id')::bigint
          FROM payload
          WHERE em.id = (SELECT id FROM visible_email)
          RETURNING em.id, em.subject
        ),
        suggestion_decisions AS (
          UPDATE app.email_assignment_suggestions eas
          SET
            status = CASE
              WHEN eas.suggested_case_id = (SELECT id FROM target_case) THEN 'accepted'
              ELSE 'rejected'
            END,
            decided_by_user_id = (data->>'actor_user_id')::bigint,
            decided_at = now()
          FROM payload
          WHERE eas.email_message_id = (SELECT id FROM updated_email)
            AND eas.status = 'pending'
        ),
        event AS (
          INSERT INTO app.communication_events (
            event_type,
            customer_case_id,
            email_message_id,
            actor_user_id,
            title
          )
          SELECT
            'email_assigned',
            target_case.id,
            updated_email.id,
            (data->>'actor_user_id')::bigint,
            updated_email.subject
          FROM payload, target_case, updated_email
        )
        SELECT jsonb_build_object(
          'ok', TRUE,
          'email_message_id', (SELECT id FROM updated_email),
          'customer_case_id', (SELECT id FROM target_case)
        )::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("email_message_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "email_not_found")
    if not result.get("customer_case_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "customer_case_not_found")
    return result


def set_email_lifecycle(email_message_id: str, action: str, access_email: str) -> dict[str, Any]:
    context = require_primary_user(access_email)
    actor_user_id = int(context["primary_user_id"])
    if action not in {"archive", "delete"}:
        raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_email_action")
    payload = {
        "email_message_id": email_message_id,
        "actor_user_id": actor_user_id,
        "context": context,
        "action": action,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_email AS (
          SELECT em.id, em.subject
          FROM app.email_messages em
          LEFT JOIN app.email_case_links ecl ON ecl.email_message_id = em.id
          LEFT JOIN app.customer_cases cc ON cc.id = ecl.customer_case_id
          WHERE em.id = (SELECT (data->>'email_message_id')::bigint FROM payload)
            AND em.deleted_at IS NULL
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR em.assigned_user_id IS NULL
              OR em.assigned_user_id IN (SELECT id FROM scope_users)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        updated_email AS (
          UPDATE app.email_messages em
          SET
            archived_at = CASE
              WHEN (SELECT data->>'action' FROM payload) = 'archive' THEN now()
              ELSE em.archived_at
            END,
            archived_by_user_id = CASE
              WHEN (SELECT data->>'action' FROM payload) = 'archive'
              THEN (SELECT (data->>'actor_user_id')::bigint FROM payload)
              ELSE em.archived_by_user_id
            END,
            deleted_at = CASE
              WHEN (SELECT data->>'action' FROM payload) = 'delete' THEN now()
              ELSE em.deleted_at
            END,
            deleted_by_user_id = CASE
              WHEN (SELECT data->>'action' FROM payload) = 'delete'
              THEN (SELECT (data->>'actor_user_id')::bigint FROM payload)
              ELSE em.deleted_by_user_id
            END
          WHERE em.id = (SELECT id FROM visible_email)
          RETURNING em.id
        ),
        linked_cases AS (
          SELECT ecl.customer_case_id
          FROM app.email_case_links ecl
          WHERE ecl.email_message_id = (SELECT id FROM updated_email)
        ),
        event AS (
          INSERT INTO app.communication_events (
            event_type,
            customer_case_id,
            email_message_id,
            actor_user_id,
            title
          )
          SELECT
            CASE
              WHEN (data->>'action') = 'archive' THEN 'email_archived'
              ELSE 'email_moved_to_trash'
            END,
            linked_cases.customer_case_id,
            visible_email.id,
            (data->>'actor_user_id')::bigint,
            visible_email.subject
          FROM payload, visible_email
          LEFT JOIN linked_cases ON TRUE
          WHERE EXISTS (SELECT 1 FROM updated_email)
        )
        SELECT jsonb_build_object(
          'ok', TRUE,
          'email_message_id', (SELECT id FROM updated_email)
        )::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("email_message_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "email_not_found")
    return {"ok": True, "email_message_id": result["email_message_id"], "action": action}


def decide_email_suggestion(suggestion_id: str, decision: str, access_email: str) -> dict[str, Any]:
    context = require_primary_user(access_email)
    actor_user_id = int(context["primary_user_id"])
    if decision not in {"accepted", "rejected"}:
        raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_suggestion_decision")
    payload = {
        "suggestion_id": suggestion_id,
        "decision": decision,
        "actor_user_id": actor_user_id,
        "context": context,
    }
    result = psql_json(
        """
        WITH payload AS (SELECT :'payload'::jsonb AS data),
        context AS (SELECT data->'context' AS data FROM payload),
        scope_users AS (
          SELECT jsonb_array_elements_text(data->'scope_user_ids')::bigint AS id
          FROM context
        ),
        visible_suggestion AS (
          SELECT
            eas.id,
            eas.email_message_id,
            eas.suggested_case_id,
            em.subject
          FROM app.email_assignment_suggestions eas
          JOIN app.email_messages em ON em.id = eas.email_message_id
          LEFT JOIN app.customer_cases cc ON cc.id = eas.suggested_case_id
          WHERE eas.id = (SELECT (data->>'suggestion_id')::bigint FROM payload)
            AND eas.status = 'pending'
            AND em.deleted_at IS NULL
            AND (
              (SELECT (data->>'is_admin')::boolean FROM context)
              OR em.assigned_user_id IS NULL
              OR em.assigned_user_id IN (SELECT id FROM scope_users)
              OR cc.owner_user_id IN (SELECT id FROM scope_users)
            )
          LIMIT 1
        ),
        updated_suggestion AS (
          UPDATE app.email_assignment_suggestions eas
          SET
            status = (SELECT data->>'decision' FROM payload),
            decided_by_user_id = (SELECT (data->>'actor_user_id')::bigint FROM payload),
            decided_at = now()
          WHERE eas.id = (SELECT id FROM visible_suggestion)
          RETURNING eas.id
        ),
        link AS (
          INSERT INTO app.email_case_links (
            email_message_id,
            customer_case_id,
            assigned_by_user_id
          )
          SELECT
            visible_suggestion.email_message_id,
            visible_suggestion.suggested_case_id,
            (data->>'actor_user_id')::bigint
          FROM payload, visible_suggestion
          WHERE (data->>'decision') = 'accepted'
            AND visible_suggestion.suggested_case_id IS NOT NULL
          ON CONFLICT DO NOTHING
        ),
        updated_email AS (
          UPDATE app.email_messages em
          SET
            is_unassigned = FALSE,
            assigned_user_id = (data->>'actor_user_id')::bigint
          FROM payload, visible_suggestion
          WHERE (data->>'decision') = 'accepted'
            AND em.id = visible_suggestion.email_message_id
          RETURNING em.id
        ),
        other_suggestions AS (
          UPDATE app.email_assignment_suggestions eas
          SET
            status = 'rejected',
            decided_by_user_id = (data->>'actor_user_id')::bigint,
            decided_at = now()
          FROM payload, visible_suggestion
          WHERE (data->>'decision') = 'accepted'
            AND eas.email_message_id = visible_suggestion.email_message_id
            AND eas.id <> visible_suggestion.id
            AND eas.status = 'pending'
        ),
        event AS (
          INSERT INTO app.communication_events (
            event_type,
            customer_case_id,
            email_message_id,
            actor_user_id,
            title,
            tenant_id,
            skill_pack_id,
            selected_module_ids,
            validator_results_json,
            confirmation_status,
            action_result_json,
            role_context_json
          )
          SELECT
            CASE
              WHEN (data->>'decision') = 'accepted'
              THEN 'email_assignment_suggestion_accepted'
              ELSE 'email_assignment_suggestion_rejected'
            END,
            visible_suggestion.suggested_case_id,
            visible_suggestion.email_message_id,
            (data->>'actor_user_id')::bigint,
            visible_suggestion.subject,
            'daskuechenhaus',
            'daskuechenhaus-email-assignment',
            ARRAY[
              'crm-email-case-matching',
              'crm-email-assignment-reasoning'
            ]::text[],
            jsonb_build_array(
              jsonb_build_object(
                'validator_id',
                'tenant-profile-validator',
                'status',
                'passed'
              ),
              jsonb_build_object(
                'validator_id',
                'skill-scope-compatibility-validator',
                'status',
                'passed'
              ),
              jsonb_build_object(
                'validator_id',
                'crm-action-audit-validator',
                'status',
                'passed'
              )
            ),
            (data->>'decision'),
            jsonb_build_object(
              'decision',
              data->>'decision',
              'email_message_id',
              visible_suggestion.email_message_id,
              'customer_case_id',
              visible_suggestion.suggested_case_id
            ),
            jsonb_build_object(
              'principal_email',
              data->'context'->>'email',
              'role_bundle_ids',
              data->'context'->'roles',
              'scope_user_ids',
              data->'context'->'scope_user_ids'
            )
          FROM payload, visible_suggestion
          WHERE EXISTS (SELECT 1 FROM updated_suggestion)
        )
        SELECT jsonb_build_object(
          'ok', TRUE,
          'suggestion_id', (SELECT id FROM updated_suggestion),
          'email_message_id', COALESCE(
            (SELECT id FROM updated_email),
            (SELECT email_message_id FROM visible_suggestion)
          )
        )::text;
        """,
        {"payload": json.dumps(payload)},
    )
    if not result.get("suggestion_id"):
        raise ApiError(HTTPStatus.NOT_FOUND, "suggestion_not_found")
    return result


class Handler(BaseHTTPRequestHandler):
    server_version = "DaskuechenhausAdminApi/1.0"

    def do_GET(self) -> None:
        self.handle_request()

    def do_POST(self) -> None:
        self.handle_request()

    def log_message(self, format: str, *args: object) -> None:
        return

    def handle_request(self) -> None:
        try:
            self.authorize()
            parsed = urlparse(self.path)
            parts = [part for part in parsed.path.split("/") if part]
            if self.command == "GET" and parsed.path == "/health":
                self.write_json(
                    {
                        "ok": True,
                        "object_storage": {
                            "configured": object_storage_configured(),
                            "bucket": OBJECT_STORAGE_BUCKET,
                            "endpoint": OBJECT_STORAGE_ENDPOINT,
                            "region": OBJECT_STORAGE_REGION,
                        },
                    }
                )
                return
            if self.command == "GET" and parsed.path == "/admin/state":
                self.write_json(admin_state())
                return
            if self.command == "GET" and parsed.path == "/overview/state":
                access_email = self.headers.get("x-access-user-email", "").strip().lower()
                self.write_json(overview_state(access_email))
                return
            if self.command == "GET" and parsed.path == "/customers/state":
                access_email = self.headers.get("x-access-user-email", "").strip().lower()
                self.write_json(customers_state(access_email))
                return
            if self.command == "GET" and parsed.path == "/customers/search":
                access_email = self.headers.get("x-access-user-email", "").strip().lower()
                params = parse_qs(parsed.query)
                query = params.get("q", [""])[0]
                customer_filter = params.get("status", ["all"])[0]
                self.write_json(search_customers(query, access_email, customer_filter))
                return
            if (
                self.command == "GET"
                and len(parts) == 4
                and parts[:2] == ["customers", "customers"]
                and parts[3] == "export"
            ):
                access_email = self.headers.get("x-access-user-email", "").strip().lower()
                export = customer_file_export(parts[2], access_email)
                self.write_binary(
                    export["body"],
                    export["content_type"],
                    export["filename"],
                )
                return
            if (
                self.command == "GET"
                and len(parts) == 6
                and parts[:2] == ["customers", "cases"]
                and parts[3] == "documents"
                and parts[5] == "download"
            ):
                access_email = self.headers.get("x-access-user-email", "").strip().lower()
                download = download_customer_case_document(parts[2], parts[4], access_email)
                self.write_binary(
                    download["body"],
                    download["content_type"],
                    download["filename"],
                )
                return
            if self.command == "POST":
                data, files = request_payload(self)
                access_email = self.headers.get("x-access-user-email", "").strip().lower()
                if parts == ["admin", "users"]:
                    self.write_json(upsert_user(data))
                    return
                if len(parts) == 3 and parts[:2] == ["admin", "users"]:
                    self.write_json(upsert_user(data, parts[2]))
                    return
                if len(parts) == 4 and parts[:2] == ["admin", "users"] and parts[3] == "roles":
                    self.write_json(save_roles(parts[2], data))
                    return
                if len(parts) == 4 and parts[:2] == ["admin", "users"] and parts[3] == "workdays":
                    self.write_json(save_workdays(parts[2], data))
                    return
                if parts == ["admin", "company-settings"]:
                    self.write_json(save_company(data))
                    return
                if parts == ["admin", "integrations"]:
                    self.write_json(save_integration(data))
                    return
                if parts == ["customers", "customers"]:
                    self.write_json(save_customer(data, access_email))
                    return
                if len(parts) == 3 and parts[:2] == ["customers", "customers"]:
                    self.write_json(save_customer(data, access_email, parts[2]))
                    return
                if (
                    len(parts) == 5
                    and parts[:2] == ["customers", "customers"]
                    and parts[3] == "sections"
                ):
                    self.write_json(save_customer_section(parts[2], parts[4], data, access_email))
                    return
                if parts == ["customers", "cases"]:
                    self.write_json(create_customer_case(data, access_email))
                    return
                if len(parts) == 3 and parts[:2] == ["customers", "cases"]:
                    self.write_json(save_customer_case(parts[2], data, access_email))
                    return
                if (
                    len(parts) == 5
                    and parts[:2] == ["customers", "cases"]
                    and parts[3] == "sections"
                ):
                    self.write_json(
                        save_customer_case_section(parts[2], parts[4], data, access_email)
                    )
                    return
                if (
                    len(parts) == 4
                    and parts[:2] == ["customers", "cases"]
                    and parts[3] == "notes"
                ):
                    self.write_json(save_customer_case_note(parts[2], data, access_email))
                    return
                if (
                    len(parts) == 4
                    and parts[:2] == ["customers", "cases"]
                    and parts[3] == "documents"
                ):
                    self.write_json(
                        create_customer_case_document_metadata(parts[2], data, files, access_email)
                    )
                    return
                if (
                    len(parts) == 6
                    and parts[:2] == ["customers", "cases"]
                    and parts[3] == "documents"
                    and parts[5] == "archive"
                ):
                    self.write_json(
                        archive_customer_case_document(parts[2], parts[4], access_email)
                    )
                    return
                if (
                    len(parts) == 6
                    and parts[:2] == ["customers", "cases"]
                    and parts[3] == "carat-imports"
                    and parts[5] == "positions"
                ):
                    self.write_json(
                        select_carat_import_positions(parts[2], parts[4], data, access_email)
                    )
                    return
                if (
                    len(parts) == 4
                    and parts[:2] == ["customers", "cases"]
                    and parts[3] == "confirmations"
                ):
                    self.write_json(
                        create_supplier_order_confirmation(parts[2], data, access_email)
                    )
                    return
                if (
                    len(parts) == 6
                    and parts[:2] == ["customers", "confirmations"]
                    and parts[3] == "exceptions"
                    and parts[5] == "decide"
                ):
                    self.write_json(
                        decide_supplier_confirmation_exception(
                            parts[2],
                            parts[4],
                            data,
                            access_email,
                        )
                    )
                    return
                if parts == ["overview", "tasks"]:
                    self.write_json(create_task(data, files, access_email))
                    return
                if len(parts) == 3 and parts[:2] == ["overview", "tasks"]:
                    self.write_json(update_task(parts[2], data, files, access_email))
                    return
                if len(parts) == 4 and parts[:2] == ["overview", "tasks"] and parts[3] == "archive":
                    self.write_json(set_task_lifecycle(parts[2], "archive", access_email))
                    return
                if len(parts) == 4 and parts[:2] == ["overview", "tasks"] and parts[3] == "delete":
                    self.write_json(set_task_lifecycle(parts[2], "delete", access_email))
                    return
                if parts == ["overview", "emails", "assign"]:
                    self.write_json(assign_email(data, access_email))
                    return
                if (
                    len(parts) == 5
                    and parts[:3] == ["overview", "emails", "suggestions"]
                    and parts[4] == "accept"
                ):
                    self.write_json(decide_email_suggestion(parts[3], "accepted", access_email))
                    return
                if (
                    len(parts) == 4
                    and parts[:2] == ["overview", "emails"]
                    and parts[3] == "archive"
                ):
                    self.write_json(set_email_lifecycle(parts[2], "archive", access_email))
                    return
                if len(parts) == 4 and parts[:2] == ["overview", "emails"] and parts[3] == "delete":
                    self.write_json(set_email_lifecycle(parts[2], "delete", access_email))
                    return
            raise ApiError(HTTPStatus.NOT_FOUND, "not_found")
        except ApiError as error:
            payload = {"ok": False, "error": error.message}
            payload.update(error.details)
            self.write_json(payload, error.status)
        except Exception:
            traceback.print_exc()
            self.write_json(
                {"ok": False, "error": "internal_error"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def authorize(self) -> None:
        if self.path == "/health":
            return
        expected = read_token()
        supplied = self.headers.get("x-dkh-admin-api-token", "")
        authorization = self.headers.get("authorization", "")
        if authorization.startswith("Bearer "):
            supplied = authorization.removeprefix("Bearer ").strip()
        if not supplied or supplied != expected:
            raise ApiError(HTTPStatus.UNAUTHORIZED, "unauthorized")
        email = self.headers.get("x-access-user-email", "").strip().lower()
        if ALLOWED_EMAILS and email not in ALLOWED_EMAILS:
            raise ApiError(HTTPStatus.FORBIDDEN, "forbidden")

    def write_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def write_binary(
        self,
        body: bytes,
        content_type: str,
        filename: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        safe_content_type = safe_response_content_type(content_type)
        safe_filename = safe_response_filename(filename)
        self.send_response(status)
        self.send_header("content-type", safe_content_type)
        self.send_header("cache-control", "no-store")
        self.send_header("content-disposition", f"attachment; filename*=UTF-8''{safe_filename}")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
