from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_PATH = REPO_ROOT / "scripts" / "hetzner" / "daskuechenhaus_admin_api.py"
SERVICE_PATH = REPO_ROOT / "scripts" / "hetzner" / "daskuechenhaus-admin-api.service"
MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0001_admin_area.sql"
)


def test_daskuechenhaus_admin_api_runs_on_hetzner_runtime_plane_only() -> None:
    source = API_PATH.read_text(encoding="utf-8")
    service = SERVICE_PATH.read_text(encoding="utf-8")

    assert "tenant_daskuechenhaus" in source
    assert "ThreadingHTTPServer((HOST, PORT), Handler)" in source
    assert '"127.0.0.1"' in source
    assert "psql" in source
    assert "DKH_ADMIN_API_TOKEN_FILE" in source
    assert "x-dkh-admin-api-token" in source
    assert "x-access-user-email" in source
    assert "cloudflare_access" in source
    assert "User=tenant_daskuechenhaus_app" in service
    assert "DKH_ADMIN_API_HOST=127.0.0.1" in service
    assert "DKH_ADMIN_API_PORT=8715" in service


def test_daskuechenhaus_admin_api_exposes_required_admin_routes() -> None:
    source = API_PATH.read_text(encoding="utf-8")

    assert 'parsed.path == "/admin/state"' in source
    assert 'parts == ["admin", "users"]' in source
    assert 'parts[:2] == ["admin", "users"]' in source
    assert 'parts[3] == "roles"' in source
    assert 'parts[3] == "workdays"' in source
    assert 'parts == ["admin", "company-settings"]' in source
    assert 'parts == ["admin", "integrations"]' in source


def test_daskuechenhaus_admin_api_exposes_required_overview_routes() -> None:
    source = API_PATH.read_text(encoding="utf-8")

    assert 'parsed.path == "/overview/state"' in source
    assert 'parts == ["overview", "tasks"]' in source
    assert 'set_task_lifecycle(parts[2], "archive", access_email)' in source
    assert 'set_task_lifecycle(parts[2], "delete", access_email)' in source
    assert 'parts == ["overview", "emails", "assign"]' in source
    assert "decide_email_suggestion" in source
    assert 'parts[4] == "accept"' in source
    assert 'parts[4] in {"accept", "reject"}' not in source
    assert 'set_email_lifecycle(parts[2], "archive", access_email)' in source
    assert 'set_email_lifecycle(parts[2], "delete", access_email)' in source
    assert "current_user_context" in source
    assert "scope_user_ids" in source
    assert "user_delegations" in source


def test_daskuechenhaus_admin_api_exposes_required_customer_routes() -> None:
    source = API_PATH.read_text(encoding="utf-8")

    assert 'parsed.path == "/customers/state"' in source
    assert 'parsed.path == "/customers/search"' in source
    assert 'parts == ["customers", "customers"]' in source
    assert 'parts[:2] == ["customers", "customers"]' in source
    assert "customers_state" in source
    assert "search_customers" in source
    assert "save_customer" in source
    assert "customer_display_name" in source
    assert "app.customers" in source
    assert "app.customer_addresses" in source
    assert "app.customer_cases" in source
    assert "customer_name_required" in source
    assert "customer_not_found" in source
    assert "customer_duplicate_found" in source
    assert "customer_duplicate_matches" in source
    assert "normalize_phone_number" in source
    assert '"primary_email": str(data.get("primary_email", "")).strip().lower()' in source
    assert (
        '"primary_phone_normalized": normalize_phone_number(data.get("primary_phone", ""))'
        in source
    )
    assert (
        '"primary_mobile_normalized": normalize_phone_number(data.get("primary_mobile", ""))'
        in source
    )
    assert '"case_type": str(' in source
    assert '"kitchen_project_b2b"' in source


def test_daskuechenhaus_admin_api_keeps_cockpit_actions_human_confirmed() -> None:
    source = API_PATH.read_text(encoding="utf-8")

    assert "resolve_customer_case_id" in source
    assert "customer_case_search_ambiguous" in source
    assert "email_assignment_suggestions" in source
    assert "email_assignment_suggestion_accepted" in source
    assert "suggestion_decisions" in source
    assert "other_suggestions" in source
    assert "is_unassigned = FALSE" in source
    assert "em.archived_at IS NULL" in source
    assert "em.deleted_at IS NULL" in source
    assert "t.archived_at IS NULL" in source
    assert "t.deleted_at IS NULL" in source
    assert "communication_events" in source


def test_daskuechenhaus_admin_api_handles_task_uploads_on_hetzner() -> None:
    source = API_PATH.read_text(encoding="utf-8")
    service = SERVICE_PATH.read_text(encoding="utf-8")

    assert "multipart/form-data" in source
    assert "FileUpload" in source
    assert "ALLOWED_TASK_ATTACHMENT_TYPES" in source
    assert "save_task_attachment" in source
    assert "DKH_ADMIN_UPLOAD_ROOT=" in service
    assert "/var/lib/daskuechenhaus/uploads" in service
    assert "ReadWritePaths=/var/lib/daskuechenhaus/uploads" in service


def test_daskuechenhaus_admin_migration_seeds_initial_admin_and_company() -> None:
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "'k.milonas@schober-daskuechenhaus.de'" in migration
    assert "'Konstantin'" in migration
    assert "'Milonas'" in migration
    assert "INSERT INTO app.user_roles" in migration
    assert "INSERT INTO app.user_security_settings" in migration
    assert "INSERT INTO app.company_settings" in migration
