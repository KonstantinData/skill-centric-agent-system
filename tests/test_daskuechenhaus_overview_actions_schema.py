from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0006_overview_action_state.sql"
)


def load_migration() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8")


def test_overview_action_state_migration_exists() -> None:
    assert MIGRATION_PATH.exists()


def test_overview_action_state_uses_soft_delete_columns() -> None:
    migration = load_migration()

    assert "ALTER TABLE app.tasks" in migration
    assert "archived_at TIMESTAMPTZ" in migration
    assert "archived_by_user_id BIGINT REFERENCES app.users (id)" in migration
    assert "deleted_at TIMESTAMPTZ" in migration
    assert "deleted_by_user_id BIGINT REFERENCES app.users (id)" in migration
    assert "ALTER TABLE app.email_messages" in migration


def test_overview_action_state_adds_permission_and_grants() -> None:
    migration = load_migration()

    assert "'overview.actions.manage'" in migration
    assert "WHERE roles.code IN ('admin', 'sales', 'employee')" in migration
    assert "tenant_daskuechenhaus_app" in migration
