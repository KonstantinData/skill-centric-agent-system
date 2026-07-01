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
SEARCH_FIRST_MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0008_customer_search_first_deduplication.sql"
)
CUSTOMER_FILE_DESKTOP_MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0009_customer_file_desktop.sql"
)
CARAT_IMPORT_MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0012_carat_prjz_imports.sql"
)
SUPPLIER_CONFIRMATION_MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0013_supplier_order_confirmations.sql"
)
CUSTOMER_CASE_ARCHIVE_MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0015_customer_case_archive.sql"
)


def load_migration() -> str:
    return CUSTOMER_DATABASE_MIGRATION_PATH.read_text(encoding="utf-8")


def test_customer_database_migration_exists() -> None:
    assert CUSTOMER_DATABASE_MIGRATION_PATH.exists()
    assert SEARCH_FIRST_MIGRATION_PATH.exists()
    assert CUSTOMER_FILE_DESKTOP_MIGRATION_PATH.exists()
    assert CARAT_IMPORT_MIGRATION_PATH.exists()
    assert SUPPLIER_CONFIRMATION_MIGRATION_PATH.exists()
    assert CUSTOMER_CASE_ARCHIVE_MIGRATION_PATH.exists()


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


def test_customer_file_desktop_migration_seeds_eleven_status_phases() -> None:
    migration = CUSTOMER_FILE_DESKTOP_MIGRATION_PATH.read_text(encoding="utf-8")

    expected_phases = {
        "(1, 'inquiry', 'Anfrage'",
        "(2, 'consultation', 'Beratung'",
        "(3, 'planning', 'Planung'",
        "(4, 'offer', 'Angebot'",
        "(5, 'order', 'Auftrag'",
        "(6, 'order_processing', 'Bestellabwicklung'",
        "(7, 'order_confirmation_check', 'AB-Kontrolle'",
        "(8, 'delivery_installation', 'Lieferung und Montage'",
        "(9, 'invoice', 'Rechnung'",
        "(10, 'service_complaint', 'Kundendienst/Reklamation'",
        "(11, 'closed', 'Abgeschlossen'",
    }

    for phase in expected_phases:
        assert phase in migration

    assert (
        "CONSTRAINT customer_case_status_phases_range CHECK (phase BETWEEN 1 AND 11)"
        in migration
    )


def test_customer_case_archive_migration_adds_restore_metadata() -> None:
    migration = CUSTOMER_CASE_ARCHIVE_MIGRATION_PATH.read_text(encoding="utf-8")

    assert "ALTER TABLE app.customer_cases" in migration
    assert "ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ" in migration
    assert (
        "ADD COLUMN IF NOT EXISTS archived_by_user_id BIGINT REFERENCES app.users (id)"
        in migration
    )
    assert "ADD COLUMN IF NOT EXISTS archive_note TEXT" in migration
    assert "customer_cases_archive_idx" in migration
    assert "WHERE is_active = TRUE" in migration


def test_customer_file_desktop_migration_adds_flexible_sections() -> None:
    migration = CUSTOMER_FILE_DESKTOP_MIGRATION_PATH.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS app.customer_file_sections" in migration
    assert "CREATE TABLE IF NOT EXISTS app.customer_case_sections" in migration
    assert "payload_json JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "ADD COLUMN IF NOT EXISTS payload_json" in migration
    assert "SET payload_json = payload" in migration
    assert "DROP CONSTRAINT customer_file_sections_code;" in migration
    assert "DROP CONSTRAINT customer_case_sections_code;" in migration
    assert "section_code ~ '^[a-z][a-z0-9_]*$'" in migration
    assert "customer_file_sections_customer_code_key" in migration
    assert "customer_case_sections_case_code_key" in migration
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE" in migration
    assert "tenant_daskuechenhaus_app" in migration


def test_customer_case_document_metadata_migration_extends_document_records() -> None:
    migration = (
        REPO_ROOT
        / "migrations"
        / "hetzner"
        / "tenants"
        / "daskuechenhaus"
        / "0010_customer_case_document_metadata.sql"
    ).read_text(encoding="utf-8")

    assert "ALTER TABLE app.customer_case_documents" in migration
    assert "ADD COLUMN IF NOT EXISTS register_code" in migration
    assert "ADD COLUMN IF NOT EXISTS document_category" in migration
    assert "ADD COLUMN IF NOT EXISTS document_status" in migration
    assert "ADD COLUMN IF NOT EXISTS version_label" in migration
    assert "ALTER COLUMN original_filename DROP NOT NULL" in migration
    assert "customer_case_documents_register_code" in migration
    assert "customer_case_documents_category" in migration
    assert "'order_processing'" in migration
    assert "'carat_project'" in migration
    assert "ELSE 'customer_document'" in migration
    assert "ELSE 'other'" in migration
    assert "customer_case_documents_status" in migration
    assert "customer_case_documents_case_register_idx" in migration
    assert "tenant_daskuechenhaus_app" in migration


def test_customer_case_document_object_storage_migration_adds_file_backend_contract() -> None:
    migration = (
        REPO_ROOT
        / "migrations"
        / "hetzner"
        / "tenants"
        / "daskuechenhaus"
        / "0011_customer_document_object_storage.sql"
    ).read_text(encoding="utf-8")

    assert "ADD COLUMN IF NOT EXISTS storage_backend" in migration
    assert "ADD COLUMN IF NOT EXISTS object_storage_bucket" in migration
    assert "ADD COLUMN IF NOT EXISTS object_storage_key" in migration
    assert "ADD COLUMN IF NOT EXISTS content_sha256" in migration
    assert "customer_case_documents_object_storage_complete" in migration
    assert "customer_case_documents_content_sha256" in migration
    assert "customer_case_documents_allowed_content_type" in migration
    assert "customer_case_documents_object_storage_idx" in migration
    assert "'image/webp'" in migration
    assert "'application/vnd.openxmlformats-officedocument.wordprocessingml.document'" in migration
    assert "'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'" in migration
    assert "'application/zip'" in migration
    assert "'application/x-zip-compressed'" in migration
    assert "'application/octet-stream'" in migration
    assert "'from_customer'" in migration
    assert "'measurement'" in migration
    assert "'planning'" in migration
    assert "'offer'" in migration
    assert "'order_processing'" in migration
    assert "'complaint_service'" in migration
    assert "'delivery_installation'" in migration
    assert "'invoice'" in migration
    assert "tenant_daskuechenhaus_app" in migration


def test_customer_database_adds_carat_prjz_import_analysis_tables() -> None:
    migration = CARAT_IMPORT_MIGRATION_PATH.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS app.customer_case_carat_imports" in migration
    assert "CREATE TABLE IF NOT EXISTS app.customer_case_carat_import_positions" in migration
    assert "document_id BIGINT NOT NULL REFERENCES app.customer_case_documents" in migration
    assert "selection_status IN ('candidate', 'selected', 'ignored', 'transferred')" in migration
    assert "customer_case_carat_imports_document_unique" in migration
    assert "'carat_project'" in migration
    assert "'application/zip'" in migration
    assert "'application/x-zip-compressed'" in migration
    assert "'application/octet-stream'" in migration
    assert "tenant_daskuechenhaus_app" in migration


def test_customer_database_adds_supplier_confirmation_cockpit_tables() -> None:
    migration = SUPPLIER_CONFIRMATION_MIGRATION_PATH.read_text(encoding="utf-8")

    for table_name in (
        "app.suppliers",
        "app.supplier_contacts",
        "app.supplier_orders",
        "app.supplier_order_positions",
        "app.supplier_confirmation_inbox_items",
        "app.supplier_order_confirmations",
        "app.supplier_order_confirmation_positions",
        "app.supplier_order_confirmation_exceptions",
        "app.supplier_order_confirmation_decisions",
        "app.supplier_communications",
        "app.supplier_follow_ups",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in migration

    assert (
        "inbox_item_id BIGINT NOT NULL REFERENCES app.supplier_confirmation_inbox_items"
        in migration
    )
    assert "'context_revision_required'" in migration
    assert "match_rate NUMERIC" in migration
    assert "difference_type IN (" in migration
    assert "'missing_position'" in migration
    assert "'extra_position'" in migration
    assert "'corrected_ab_request'" in migration
    assert "supplier_orders.manage" in migration
    assert "supplier_confirmations.manage" in migration
    assert "tenant_daskuechenhaus_app" in migration


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


def test_customer_search_first_migration_adds_deduplication_contract() -> None:
    migration = SEARCH_FIRST_MIGRATION_PATH.read_text(encoding="utf-8")

    assert "primary_phone_normalized" in migration
    assert "primary_mobile_normalized" in migration
    assert "phone_normalized" in migration
    assert "mobile_normalized" in migration
    assert "DROP INDEX IF EXISTS app.customers_primary_email_unique_idx" in migration
    assert "CREATE UNIQUE INDEX IF NOT EXISTS customers_primary_email_unique_idx" not in migration
    assert "customers_primary_phone_normalized_unique_idx" in migration
    assert "customers_primary_mobile_normalized_unique_idx" in migration
    assert "object_customer_label TEXT" in migration
    assert "customers_object_customer_label CHECK" in migration
    assert "'architect'" in migration
    assert "'developer'" in migration
    assert "'joinery'" in migration
    assert "tax_treatment TEXT" in migration
    assert "customers_tax_treatment CHECK" in migration
    assert "'switzerland_export'" in migration
    assert "'nato_forces'" in migration
    assert "customers_source CHECK" in migration
    assert "'walk_in'" in migration
    assert "'website'" in migration
    assert "'recommendation'" in migration
    assert "'b2b_network'" in migration
    assert "'kitchen_project_b2b'" in migration
    assert "customers_search_first_idx" in migration
    assert "customer_contacts_search_first_idx" in migration
