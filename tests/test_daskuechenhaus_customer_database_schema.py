from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CUSTOMER_DATABASE_MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0005_customer_database.sql"
)


def load_migration() -> str:
    return CUSTOMER_DATABASE_MIGRATION_PATH.read_text(encoding="utf-8")


def test_customer_database_migration_exists() -> None:
    assert CUSTOMER_DATABASE_MIGRATION_PATH.exists()


def test_customer_database_creates_expected_tables() -> None:
    migration = load_migration()

    expected_tables = {
        "app.customers",
        "app.customer_addresses",
        "app.customer_contacts",
        "app.customer_case_status_phases",
        "app.customer_case_participants",
        "app.customer_case_project_profiles",
        "app.customer_case_notes",
        "app.customer_case_documents",
        "app.customer_case_audit_events",
    }

    for table in expected_tables:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in migration


def test_customer_database_has_primary_and_foreign_keys() -> None:
    migration = load_migration()

    assert "PRIMARY KEY" in migration
    assert "REFERENCES app.customers (id)" in migration
    assert "REFERENCES app.customer_cases (id)" in migration
    assert "REFERENCES app.customer_contacts (id)" in migration
    assert "REFERENCES app.customer_case_status_phases (phase)" in migration
    assert "REFERENCES app.users (id)" in migration


def test_customer_database_keeps_duplicate_names_allowed() -> None:
    migration = load_migration()

    assert "customers_display_name_search_idx" in migration
    assert "UNIQUE (display_name)" not in migration
    assert "CREATE UNIQUE INDEX IF NOT EXISTS customers_display_name" not in migration
    assert "CREATE UNIQUE INDEX IF NOT EXISTS customers_customer_number_key" in migration
    assert "WHERE customer_number IS NOT NULL" in migration


def test_customer_database_extends_existing_customer_cases() -> None:
    migration = load_migration()

    assert "ALTER TABLE app.customer_cases" in migration
    assert "ADD COLUMN IF NOT EXISTS customer_id BIGINT REFERENCES app.customers (id)" in migration
    assert (
        "ADD COLUMN IF NOT EXISTS status_phase_id SMALLINT REFERENCES "
        "app.customer_case_status_phases (phase)"
    ) in migration
    assert "ADD COLUMN IF NOT EXISTS carat_project_number TEXT" in migration
    assert (
        "ADD COLUMN IF NOT EXISTS responsible_user_id BIGINT REFERENCES app.users (id)"
        in migration
    )
    assert "UPDATE app.customer_cases" in migration
    assert "WHERE status_phase_id IS NULL" in migration


def test_customer_database_seeds_ten_status_phases() -> None:
    migration = load_migration()

    expected_phases = {
        "(1, 'new_contact', 'Neuer Kontakt'",
        "(2, 'consultation_planned', 'Erstberatung geplant'",
        "(3, 'consultation_done', 'Beratung abgeschlossen'",
        "(4, 'measurement_planning', 'Aufmass / Planung'",
        "(5, 'offer_created', 'Angebot erstellt'",
        "(6, 'order_confirmed', 'Auftrag erteilt'",
        "(7, 'production_ordered', 'Bestellung / Produktion'",
        "(8, 'delivery_installation', 'Lieferung / Montage'",
        "(9, 'acceptance_invoice', 'Abnahme / Rechnung'",
        "(10, 'aftersales_closed', 'Aftersales / Abgeschlossen'",
    }

    for phase in expected_phases:
        assert phase in migration

    assert (
        "CONSTRAINT customer_case_status_phases_range CHECK (phase BETWEEN 1 AND 10)"
        in migration
    )


def test_customer_database_supports_customer_folder_documents_and_notes() -> None:
    migration = load_migration()

    assert "CREATE TABLE IF NOT EXISTS app.customer_case_notes" in migration
    assert "source IN ('manual', 'email_import', 'system_import', 'scas_agent')" in migration
    assert "CREATE TABLE IF NOT EXISTS app.customer_case_documents" in migration
    assert "'application/pdf'" in migration
    assert "'image/jpeg'" in migration
    assert "'image/png'" in migration
    assert "'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'" in migration
    assert "'email_attachment'" in migration


def test_customer_database_backfills_existing_cases_without_merging_same_names() -> None:
    migration = load_migration()

    assert "FOR case_record IN" in migration
    assert "WHERE customer_id IS NULL" in migration
    assert "source = 'legacy_customer_case'" not in migration
    assert "'legacy_customer_case'" in migration
    assert "RETURNING id INTO new_customer_id" in migration
    assert "SET customer_id = new_customer_id" in migration


def test_customer_database_adds_permissions_and_runtime_grants() -> None:
    migration = load_migration()

    for permission_code in (
        "customers.view",
        "customers.manage",
        "customer_cases.view",
        "customer_cases.manage",
        "customer_notes.manage",
        "customer_documents.manage",
    ):
        assert permission_code in migration

    assert "WHERE roles.code = 'admin'" in migration
    assert "WHERE roles.code = 'sales'" in migration
    assert "WHERE roles.code = 'employee'" in migration
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app" in migration
    assert "tenant_daskuechenhaus_app" in migration
