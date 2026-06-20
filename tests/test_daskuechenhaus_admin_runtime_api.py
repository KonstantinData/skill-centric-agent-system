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
    assert 'parts == ["overview", "emails", "assign"]' in source
    assert "current_user_context" in source
    assert "scope_user_ids" in source
    assert "user_delegations" in source


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
