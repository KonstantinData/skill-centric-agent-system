#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import secrets
import string
import subprocess
import traceback
from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default as email_policy
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

DATABASE = os.environ.get("DKH_ADMIN_DATABASE", "tenant_daskuechenhaus")
HOST = os.environ.get("DKH_ADMIN_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("DKH_ADMIN_API_PORT", "8715"))
TOKEN_FILE = os.environ.get("DKH_ADMIN_API_TOKEN_FILE", "/etc/daskuechenhaus/admin-api-token")
UPLOAD_ROOT = Path(os.environ.get("DKH_ADMIN_UPLOAD_ROOT", "/var/lib/daskuechenhaus/uploads"))
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

NUMBER_ALPHABET = string.ascii_uppercase + string.digits
CARAT_ORDER_NUMBER_PATTERN = re.compile(r"^[A-Za-z0-9]{1,5}-[A-Za-z0-9]{1,3}$")


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


def psql_json(sql: str, variables: dict[str, str] | None = None) -> Any:
    command = ["psql", "-X", "-q", "-t", "-A", "-d", DATABASE]
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


def normalize_attachment_type(upload: FileUpload) -> str:
    extension = Path(upload.filename).suffix.lower()
    expected_type = ALLOWED_TASK_ATTACHMENT_EXTENSIONS.get(extension)
    if upload.content_type in ALLOWED_TASK_ATTACHMENT_TYPES:
        return upload.content_type
    if expected_type:
        return expected_type
    raise ApiError(HTTPStatus.BAD_REQUEST, "unsupported_task_attachment_type")


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
            owner_user_id = COALESCE(cc.owner_user_id, NULLIF(data->>'responsible_user_id', '')::bigint),
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
        ),
        assignment AS (
          INSERT INTO app.task_assignments (task_id, user_id, assigned_by_user_id)
          SELECT
            updated_task.id,
            (data->>'assigned_user_id')::bigint,
            (data->>'actor_user_id')::bigint
          FROM updated_task, payload
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
                self.write_json({"ok": True})
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
                if len(parts) == 3 and parts[:2] == ["customers", "cases"]:
                    self.write_json(save_customer_case(parts[2], data, access_email))
                    return
                if (
                    len(parts) == 5
                    and parts[:2] == ["customers", "cases"]
                    and parts[3] == "sections"
                ):
                    self.write_json(save_customer_case_section(parts[2], parts[4], data, access_email))
                    return
                if (
                    len(parts) == 4
                    and parts[:2] == ["customers", "cases"]
                    and parts[3] == "notes"
                ):
                    self.write_json(save_customer_case_note(parts[2], data, access_email))
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


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
