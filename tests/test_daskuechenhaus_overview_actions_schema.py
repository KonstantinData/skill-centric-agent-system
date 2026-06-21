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
ACTION_AUDIT_MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0007_crm_action_audit_evidence.sql"
)
ADMIN_API_PATH = REPO_ROOT / "scripts" / "hetzner" / "daskuechenhaus_admin_api.py"


def load_migration() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8")


def load_action_audit_migration() -> str:
    return ACTION_AUDIT_MIGRATION_PATH.read_text(encoding="utf-8")


def load_admin_api() -> str:
    return ADMIN_API_PATH.read_text(encoding="utf-8")


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


def test_crm_action_audit_evidence_migration_exists() -> None:
    assert ACTION_AUDIT_MIGRATION_PATH.exists()


def test_crm_action_audit_evidence_columns_are_added() -> None:
    migration = load_action_audit_migration()

    assert "ALTER TABLE app.communication_events" in migration
    assert "tenant_id TEXT NOT NULL DEFAULT 'daskuechenhaus'" in migration
    assert "skill_pack_id TEXT" in migration
    assert "selected_module_ids TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[]" in migration
    assert "validator_results_json JSONB NOT NULL DEFAULT '[]'::jsonb" in migration
    assert "confirmation_status TEXT" in migration
    assert "action_result_json JSONB" in migration
    assert "role_context_json JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "communication_events_confirmation_status" in migration
    assert "communication_events_skill_pack_idx" in migration


def test_email_suggestion_decision_writes_scas_audit_evidence() -> None:
    source = load_admin_api()

    assert "'daskuechenhaus-email-assignment'" in source
    assert "'crm-email-case-matching'" in source
    assert "'crm-email-assignment-reasoning'" in source
    assert "'tenant-profile-validator'" in source
    assert "'skill-scope-compatibility-validator'" in source
    assert "'crm-action-audit-validator'" in source
    assert "confirmation_status" in source
    assert "action_result_json" in source
    assert "role_context_json" in source
    assert "data->'context'->'roles'" in source
    assert "data->'context'->'scope_user_ids'" in source
