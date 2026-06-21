from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0001_admin_area.sql"
)
OVERVIEW_MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0002_overview_workspace.sql"
)
MAIL_RUNTIME_MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0003_mail_runtime_configuration.sql"
)
MAIL_IMPORT_STATE_MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0004_mail_import_state.sql"
)
CUSTOMER_DATABASE_MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0005_customer_database.sql"
)
OVERVIEW_ACTION_STATE_MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0006_overview_action_state.sql"
)


def load_migration() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8")


def test_daskuechenhaus_admin_area_migration_exists() -> None:
    assert MIGRATION_PATH.exists()
    assert OVERVIEW_MIGRATION_PATH.exists()
    assert MAIL_RUNTIME_MIGRATION_PATH.exists()
    assert MAIL_IMPORT_STATE_MIGRATION_PATH.exists()
    assert CUSTOMER_DATABASE_MIGRATION_PATH.exists()
    assert OVERVIEW_ACTION_STATE_MIGRATION_PATH.exists()


def test_admin_area_migration_creates_expected_tables() -> None:
    migration = load_migration()

    expected_tables = {
        "app.users",
        "app.roles",
        "app.permissions",
        "app.role_permissions",
        "app.user_roles",
        "app.user_preferences",
        "app.user_workdays",
        "app.user_notification_settings",
        "app.user_security_settings",
        "app.company_settings",
        "app.admin_settings",
        "app.integrations",
        "app.integration_connections",
        "audit.change_log",
    }

    for table in expected_tables:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in migration


def test_admin_area_migration_has_primary_and_foreign_keys() -> None:
    migration = load_migration()

    assert "PRIMARY KEY" in migration
    assert "REFERENCES app.users (id)" in migration
    assert "REFERENCES app.roles (id)" in migration
    assert "REFERENCES app.permissions (id)" in migration
    assert "REFERENCES app.integrations (id)" in migration


def test_workday_schema_matches_admin_form_requirements() -> None:
    migration = load_migration()

    assert "weekday SMALLINT NOT NULL" in migration
    assert "CONSTRAINT user_workdays_weekday_range CHECK (weekday BETWEEN 1 AND 6)" in migration
    assert "morning_start_time TIME" in migration
    assert "morning_end_time TIME" in migration
    assert "afternoon_start_time TIME" in migration
    assert "afternoon_end_time TIME" in migration
    assert "CONSTRAINT user_workdays_working_day_has_time CHECK" in migration
    assert "CONSTRAINT user_workdays_window_order CHECK" in migration


def test_security_schema_uses_cloudflare_access_without_passwords() -> None:
    migration = load_migration()

    assert "external_identity_provider TEXT NOT NULL DEFAULT 'cloudflare_access'" in migration
    assert "password_login_enabled BOOLEAN NOT NULL DEFAULT FALSE" in migration
    assert "CONSTRAINT user_security_settings_password_disabled CHECK" in migration
    assert "password_hash" not in migration


def test_admin_area_migration_seeds_system_roles_and_permissions() -> None:
    migration = load_migration()

    assert "('admin', 'Admin'" in migration
    assert "('employee', 'Mitarbeiter'" in migration
    assert "('sales', 'Verkauf'" in migration
    assert "('admin.view', 'Admin-Bereich ansehen'" in migration
    assert "('admin.users.manage', 'Benutzer verwalten'" in migration


def test_admin_area_allows_duplicate_employee_names() -> None:
    migration = load_migration()

    assert "UNIQUE (first_name" not in migration
    assert "UNIQUE (last_name" not in migration
    assert "UNIQUE (first_name, last_name)" not in migration
    assert "PRIMARY KEY (user_id, role_id)" in migration


def test_admin_area_allows_duplicate_employee_emails_for_role_entries() -> None:
    migration = load_migration()

    assert "CREATE UNIQUE INDEX IF NOT EXISTS users_email_key" not in migration
    assert "DROP INDEX IF EXISTS app.users_email_key" in migration
    assert "CREATE INDEX IF NOT EXISTS users_email_idx ON app.users (email)" in migration


def test_overview_workspace_migration_creates_operational_tables() -> None:
    migration = OVERVIEW_MIGRATION_PATH.read_text(encoding="utf-8")

    expected_tables = {
        "app.customer_cases",
        "app.task_statuses",
        "app.tasks",
        "app.task_assignments",
        "app.task_attachments",
        "app.task_reminders",
        "app.appointments",
        "app.news_items",
        "app.goals",
        "app.goal_events",
        "app.email_accounts",
        "app.email_messages",
        "app.email_participants",
        "app.email_attachments",
        "app.email_case_links",
        "app.email_assignment_suggestions",
        "app.communication_events",
        "app.absences",
        "app.user_delegations",
        "audit.delegated_actions",
    }

    for table in expected_tables:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in migration


def test_overview_workspace_migration_keeps_pk_fk_and_attachment_rules() -> None:
    migration = OVERVIEW_MIGRATION_PATH.read_text(encoding="utf-8")

    assert "PRIMARY KEY" in migration
    assert "REFERENCES app.users (id)" in migration
    assert "REFERENCES app.customer_cases (id)" in migration
    assert "REFERENCES app.tasks (id)" in migration
    assert "REFERENCES app.email_messages (id)" in migration
    assert "REFERENCES app.task_statuses (id)" in migration
    assert "'application/pdf'" in migration
    assert "'image/jpeg'" in migration
    assert "'image/png'" in migration
    assert "'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'" in migration


def test_overview_workspace_migration_supports_delegated_access_audit() -> None:
    migration = OVERVIEW_MIGRATION_PATH.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS app.absences" in migration
    assert "CREATE TABLE IF NOT EXISTS app.user_delegations" in migration
    assert "CREATE TABLE IF NOT EXISTS audit.delegated_actions" in migration
    assert "CONSTRAINT user_delegations_not_self" in migration
    assert "CONSTRAINT user_delegations_time_order" in migration


def test_mail_runtime_migration_stores_only_secret_references() -> None:
    migration = MAIL_RUNTIME_MIGRATION_PATH.read_text(encoding="utf-8")

    assert "ALTER TABLE app.email_accounts" in migration
    assert "assigned_user_id BIGINT REFERENCES app.users (id)" in migration
    assert "imap_username_secret_ref TEXT" in migration
    assert "imap_password_secret_ref TEXT" in migration
    assert "smtp_username_secret_ref TEXT" in migration
    assert "smtp_password_secret_ref TEXT" in migration
    assert "from_address_secret_ref TEXT" in migration
    assert "'DKH_MAIL_K_MILONAS_IMAP_USERNAME'" in migration
    assert "'DKH_MAIL_K_MILONAS_IMAP_PASSWORD'" in migration
    assert "'DKH_MAIL_K_MILONAS_SMTP_USERNAME'" in migration
    assert "'DKH_MAIL_K_MILONAS_SMTP_PASSWORD'" in migration
    assert "'k.milonas@schober-daskuechenhaus.de'" in migration
    assert "WHERE account.email_address = 'k.milonas@schober-daskuechenhaus.de'" in migration
    assert "WHERE email_address = 'info@schober-daskuechenhaus.de'" in migration
    assert "assigned_user_id = NULL" in migration
    assert "JOIN app.roles r ON r.id = ur.role_id" in migration
    assert "r.code = 'sales'" in migration
    assert "IMAP_PASSWORD =" not in migration
    assert "SMTP_PASSWORD =" not in migration
