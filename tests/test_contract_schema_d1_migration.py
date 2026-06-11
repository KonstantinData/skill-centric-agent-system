from __future__ import annotations

# ruff: noqa: F403,F405,I001

from tests.contract_schema_support import *  # noqa: F403


def test_cloudflare_d1_migration_contains_required_tables_and_indexes() -> None:
    expected_tables = {
        "modules",
        "module_versions",
        "module_selection_metadata",
        "module_dependencies",
        "knowledge_sources",
        "knowledge_documents",
        "knowledge_chunks",
        "memory_records",
        "scope_bindings",
        "policy_bindings",
        "ingestion_jobs",
        "audit_events",
    }
    expected_indexes = {
        "idx_modules_name",
        "idx_modules_current_version",
        "idx_modules_kind_status",
        "idx_module_versions_module_version",
        "idx_module_selection_metadata_capability",
        "idx_module_dependencies_module_version",
        "idx_module_dependencies_dependency",
        "idx_knowledge_sources_type_status",
        "idx_knowledge_documents_source_version",
        "idx_knowledge_chunks_document",
        "idx_knowledge_chunks_scope",
        "idx_memory_records_scope_status",
        "idx_scope_bindings_scope_principal",
        "idx_scope_bindings_policy",
        "idx_policy_bindings_policy_target",
        "idx_ingestion_jobs_status_type",
        "idx_audit_events_archive_after",
        "idx_audit_events_target",
    }

    with create_d1_control_plane_connection() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        indexes = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }

    assert expected_tables <= tables
    assert expected_indexes <= indexes


def test_cloudflare_d1_migration_contains_key_constraints() -> None:
    migration_sql = d1_migration_sql()

    assert "FOREIGN KEY (module_id) REFERENCES modules (id)" in migration_sql
    assert "FOREIGN KEY (module_version_id) REFERENCES module_versions (id)" in migration_sql
    assert "FOREIGN KEY (source_id) REFERENCES knowledge_sources (id)" in migration_sql
    assert "FOREIGN KEY (memory_scope_id) REFERENCES modules (id)" in migration_sql
    assert "FOREIGN KEY (policy_id) REFERENCES modules (id)" in migration_sql
    assert "selection_base_score >= 0" in migration_sql
    assert "json_valid(score_modifiers_json)" in migration_sql
    assert "is_required IN (0, 1)" in migration_sql
    assert "archive_after TEXT NOT NULL" in migration_sql


def test_cloudflare_d1_migration_accepts_control_plane_fixture(
    control_plane_schema: dict[str, Any],
    control_plane_example: dict[str, Any],
) -> None:
    assert_valid(control_plane_schema, control_plane_example)

    with create_d1_control_plane_connection() as connection:
        insert_control_plane_fixture(connection, control_plane_example)

        module_count = connection.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
        audit_event_count = connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
        missing_current_versions = connection.execute(
            """
            SELECT COUNT(*)
            FROM modules AS m
            LEFT JOIN module_versions AS mv
                ON mv.id = m.current_version_id
                AND mv.module_id = m.id
            WHERE mv.id IS NULL
            """
        ).fetchone()[0]

    assert module_count == len(control_plane_example["records"]["modules"])
    assert audit_event_count == len(control_plane_example["records"]["audit_events"])
    assert missing_current_versions == 0


def test_cloudflare_d1_migration_rejects_invalid_enum() -> None:
    with (
        create_d1_control_plane_connection() as connection,
        pytest.raises(sqlite3.IntegrityError),
    ):
        connection.execute(
            """
            INSERT INTO modules (
                id,
                name,
                kind,
                status,
                current_version_id,
                created_at,
                updated_at
            )
            VALUES (
                'mod-invalid',
                'invalid',
                'agent',
                'active',
                'mv-invalid-0-1-0',
                '2026-05-21T20:00:00Z',
                '2026-05-21T20:00:00Z'
            )
            """
        )


def test_cloudflare_d1_migration_rejects_invalid_foreign_key() -> None:
    with (
        create_d1_control_plane_connection() as connection,
        pytest.raises(sqlite3.IntegrityError),
    ):
        connection.execute(
            """
            INSERT INTO knowledge_documents (
                id,
                source_id,
                version,
                content_uri,
                manifest_uri,
                checksum,
                status
            )
            VALUES (
                'kd-missing-source',
                'ks-missing',
                '0.1.0',
                'r2://missing/content.md',
                'r2://missing/manifest.json',
                'sha256:missing',
                'active'
            )
            """
        )
