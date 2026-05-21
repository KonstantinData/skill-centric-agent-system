from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_SCHEMA_PATH = REPO_ROOT / "schemas" / "module.schema.json"
PROFILE_SCHEMA_PATH = REPO_ROOT / "schemas" / "runtime-profile.schema.json"
CONTROL_PLANE_SCHEMA_PATH = REPO_ROOT / "schemas" / "cloudflare-control-plane.schema.json"
RUNTIME_PLANE_SCHEMA_PATH = REPO_ROOT / "schemas" / "hetzner-runtime-plane.schema.json"
MODULE_EXAMPLE_PATH = REPO_ROOT / "examples" / "modules" / "git-diff-analysis.json"
PROFILE_EXAMPLE_PATH = REPO_ROOT / "examples" / "profiles" / "code-review-profile.json"
CONTROL_PLANE_EXAMPLE_PATH = (
    REPO_ROOT / "examples" / "control-plane" / "cloudflare-control-plane.json"
)
RUNTIME_PLANE_EXAMPLE_PATH = (
    REPO_ROOT / "examples" / "runtime-plane" / "hetzner-runtime-plane.json"
)
D1_MIGRATION_PATH = (
    REPO_ROOT / "migrations" / "cloudflare" / "d1" / "0001_control_plane.sql"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def module_schema() -> dict[str, Any]:
    schema = load_json(MODULE_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture(scope="module")
def profile_schema() -> dict[str, Any]:
    schema = load_json(PROFILE_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture(scope="module")
def control_plane_schema() -> dict[str, Any]:
    schema = load_json(CONTROL_PLANE_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture(scope="module")
def runtime_plane_schema() -> dict[str, Any]:
    schema = load_json(RUNTIME_PLANE_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture
def module_example() -> dict[str, Any]:
    return load_json(MODULE_EXAMPLE_PATH)


@pytest.fixture
def profile_example() -> dict[str, Any]:
    return load_json(PROFILE_EXAMPLE_PATH)


@pytest.fixture
def control_plane_example() -> dict[str, Any]:
    return load_json(CONTROL_PLANE_EXAMPLE_PATH)


@pytest.fixture
def runtime_plane_example() -> dict[str, Any]:
    return load_json(RUNTIME_PLANE_EXAMPLE_PATH)


def assert_valid(schema: dict[str, Any], instance: dict[str, Any]) -> None:
    Draft202012Validator(schema).validate(instance)


def assert_invalid(schema: dict[str, Any], instance: dict[str, Any], message_part: str) -> None:
    with pytest.raises(ValidationError, match=message_part):
        Draft202012Validator(schema).validate(instance)


def selected_profile_modules(profile: dict[str, Any]) -> set[str]:
    selected: set[str] = set()
    for field in (
        "instructions",
        "skills",
        "tools",
        "knowledge_scopes",
        "data_scopes",
        "memory_scopes",
        "policies",
        "validators",
    ):
        selected.update(profile[field])
    return selected


def assert_profile_version_pins_selected_modules(profile: dict[str, Any]) -> None:
    selected = selected_profile_modules(profile)
    pinned = set(profile["module_versions"])
    missing = selected - pinned
    extra = pinned - selected
    assert not missing, f"missing version pins: {sorted(missing)}"
    assert not extra, f"unselected version pins: {sorted(extra)}"


def assert_control_plane_references_are_valid(control_plane: dict[str, Any]) -> None:
    records = control_plane["records"]
    modules = {module["id"]: module for module in records["modules"]}
    module_versions = {
        module_version["id"]: module_version for module_version in records["module_versions"]
    }
    knowledge_sources = {
        knowledge_source["id"]: knowledge_source
        for knowledge_source in records["knowledge_sources"]
    }
    knowledge_documents = {
        knowledge_document["id"]: knowledge_document
        for knowledge_document in records["knowledge_documents"]
    }
    memory_records = {
        memory_record["id"]: memory_record for memory_record in records["memory_records"]
    }

    for module in records["modules"]:
        current_version = module_versions.get(module["current_version_id"])
        assert current_version, f"missing current module version: {module['current_version_id']}"
        assert current_version["module_id"] == module["id"]

    for module_version in records["module_versions"]:
        assert module_version["module_id"] in modules

    for dependency in records["module_dependencies"]:
        assert dependency["module_version_id"] in module_versions
        dependency_module = modules.get(dependency["dependency_id"])
        assert dependency_module, f"missing dependency module: {dependency['dependency_id']}"
        assert dependency_module["kind"] == dependency["dependency_kind"]

    for document in records["knowledge_documents"]:
        assert document["source_id"] in knowledge_sources

    for chunk in records["knowledge_chunks"]:
        assert chunk["document_id"] in knowledge_documents
        scope_module = modules.get(chunk["scope_id"])
        assert scope_module, f"missing knowledge scope: {chunk['scope_id']}"
        assert scope_module["kind"] == "knowledge_scope"

    for memory_record in records["memory_records"]:
        scope_module = modules.get(memory_record["memory_scope_id"])
        assert scope_module, f"missing memory scope: {memory_record['memory_scope_id']}"
        assert scope_module["kind"] == "memory_scope", (
            f"invalid memory scope kind: {scope_module['kind']}"
        )

    for scope_binding in records["scope_bindings"]:
        scope_module = modules.get(scope_binding["scope_id"])
        assert scope_module, f"missing scope binding target: {scope_binding['scope_id']}"
        assert scope_module["kind"] == scope_binding["scope_kind"]
        policy_module = modules.get(scope_binding["policy_id"])
        assert policy_module, f"missing scope binding policy: {scope_binding['policy_id']}"
        assert policy_module["kind"] == "policy"

    for policy_binding in records["policy_bindings"]:
        policy_module = modules.get(policy_binding["policy_id"])
        assert policy_module, f"missing policy binding policy: {policy_binding['policy_id']}"
        assert policy_module["kind"] == "policy"
        if policy_binding["target_kind"] == "module":
            assert policy_binding["target_id"] in modules
        elif policy_binding["target_kind"] == "knowledge_source":
            assert policy_binding["target_id"] in knowledge_sources
        elif policy_binding["target_kind"] == "knowledge_document":
            assert policy_binding["target_id"] in knowledge_documents
        elif policy_binding["target_kind"] == "memory_record":
            assert policy_binding["target_id"] in memory_records
        elif policy_binding["target_kind"] == "scope":
            assert policy_binding["target_id"] in modules


def assert_runtime_plane_references_are_valid(runtime_plane: dict[str, Any]) -> None:
    records = runtime_plane["records"]
    runs = {run["id"]: run for run in records["runtime_runs"]}
    steps = {step["id"]: step for step in records["runtime_steps"]}

    for step in records["runtime_steps"]:
        assert step["run_id"] in runs

    for invocation in records["tool_invocations"]:
        assert invocation["run_id"] in runs
        assert invocation["step_id"] in steps

    for validation_result in records["validation_results"]:
        assert validation_result["run_id"] in runs
        assert validation_result["step_id"] in steps

    for candidate in records["memory_candidates"]:
        assert candidate["run_id"] in runs
        assert candidate["source_step_id"] in steps
        assert candidate["profile_id"] == runs[candidate["run_id"]]["profile_id"]


def create_d1_control_plane_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(load_text(D1_MIGRATION_PATH))
    return connection


def insert_control_plane_fixture(
    connection: sqlite3.Connection,
    control_plane: dict[str, Any],
) -> None:
    records = control_plane["records"]

    connection.executemany(
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
            :id,
            :name,
            :kind,
            :status,
            :current_version_id,
            :created_at,
            :updated_at
        )
        """,
        records["modules"],
    )
    connection.executemany(
        """
        INSERT INTO module_versions (
            id,
            module_id,
            version,
            source_uri,
            checksum,
            selection_base_score,
            created_at
        )
        VALUES (
            :id,
            :module_id,
            :version,
            :source_uri,
            :checksum,
            :selection_base_score,
            :created_at
        )
        """,
        records["module_versions"],
    )
    connection.executemany(
        """
        INSERT INTO module_dependencies (
            id,
            module_version_id,
            dependency_kind,
            dependency_id,
            is_required
        )
        VALUES (
            :id,
            :module_version_id,
            :dependency_kind,
            :dependency_id,
            :is_required
        )
        """,
        [
            {
                **dependency,
                "is_required": int(dependency["is_required"]),
            }
            for dependency in records["module_dependencies"]
        ],
    )
    connection.executemany(
        """
        INSERT INTO knowledge_sources (
            id,
            name,
            source_type,
            uri,
            owner,
            sensitivity,
            status
        )
        VALUES (
            :id,
            :name,
            :source_type,
            :uri,
            :owner,
            :sensitivity,
            :status
        )
        """,
        records["knowledge_sources"],
    )
    connection.executemany(
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
            :id,
            :source_id,
            :version,
            :content_uri,
            :manifest_uri,
            :checksum,
            :status
        )
        """,
        records["knowledge_documents"],
    )
    connection.executemany(
        """
        INSERT INTO knowledge_chunks (
            id,
            document_id,
            chunk_index,
            content_uri,
            vector_id,
            scope_id,
            token_count
        )
        VALUES (
            :id,
            :document_id,
            :chunk_index,
            :content_uri,
            :vector_id,
            :scope_id,
            :token_count
        )
        """,
        records["knowledge_chunks"],
    )
    connection.executemany(
        """
        INSERT INTO memory_records (
            id,
            memory_scope_id,
            version,
            content_uri,
            manifest_uri,
            source_run_id,
            source_profile_id,
            sensitivity,
            retention_policy,
            status
        )
        VALUES (
            :id,
            :memory_scope_id,
            :version,
            :content_uri,
            :manifest_uri,
            :source_run_id,
            :source_profile_id,
            :sensitivity,
            :retention_policy,
            :status
        )
        """,
        records["memory_records"],
    )
    connection.executemany(
        """
        INSERT INTO scope_bindings (
            id,
            scope_id,
            scope_kind,
            principal_kind,
            principal_id,
            policy_id,
            effect
        )
        VALUES (
            :id,
            :scope_id,
            :scope_kind,
            :principal_kind,
            :principal_id,
            :policy_id,
            :effect
        )
        """,
        records["scope_bindings"],
    )
    connection.executemany(
        """
        INSERT INTO policy_bindings (
            id,
            policy_id,
            target_kind,
            target_id,
            effect,
            priority
        )
        VALUES (
            :id,
            :policy_id,
            :target_kind,
            :target_id,
            :effect,
            :priority
        )
        """,
        records["policy_bindings"],
    )
    connection.executemany(
        """
        INSERT INTO ingestion_jobs (
            id,
            job_type,
            status,
            source_uri,
            target_kind,
            target_id,
            attempts,
            created_at,
            updated_at
        )
        VALUES (
            :id,
            :job_type,
            :status,
            :source_uri,
            :target_kind,
            :target_id,
            :attempts,
            :created_at,
            :updated_at
        )
        """,
        records["ingestion_jobs"],
    )
    connection.executemany(
        """
        INSERT INTO audit_events (
            id,
            event_type,
            actor_id,
            target_kind,
            target_id,
            created_at,
            retention_policy,
            archive_after,
            archive_uri
        )
        VALUES (
            :id,
            :event_type,
            :actor_id,
            :target_kind,
            :target_id,
            :created_at,
            :retention_policy,
            :archive_after,
            :archive_uri
        )
        """,
        [
            {
                **audit_event,
                "archive_uri": audit_event.get("archive_uri"),
            }
            for audit_event in records["audit_events"]
        ],
    )


def test_module_example_matches_schema(
    module_schema: dict[str, Any],
    module_example: dict[str, Any],
) -> None:
    assert_valid(module_schema, module_example)


def test_runtime_profile_example_matches_schema_and_version_contract(
    profile_schema: dict[str, Any],
    profile_example: dict[str, Any],
) -> None:
    assert_valid(profile_schema, profile_example)
    assert_profile_version_pins_selected_modules(profile_example)


def test_control_plane_example_matches_schema_and_reference_contract(
    control_plane_schema: dict[str, Any],
    control_plane_example: dict[str, Any],
) -> None:
    assert_valid(control_plane_schema, control_plane_example)
    assert_control_plane_references_are_valid(control_plane_example)


def test_runtime_plane_example_matches_schema_and_reference_contract(
    runtime_plane_schema: dict[str, Any],
    runtime_plane_example: dict[str, Any],
) -> None:
    assert_valid(runtime_plane_schema, runtime_plane_example)
    assert_runtime_plane_references_are_valid(runtime_plane_example)


@pytest.mark.parametrize(
    ("mutator", "message_part"),
    [
        (
            lambda module: module.pop("selection"),
            "'selection' is a required property",
        ),
        (
            lambda module: module.__setitem__("kind", "agent"),
            "'agent' is not one of",
        ),
        (
            lambda module: module.__setitem__("version", "v1"),
            "'v1' does not match",
        ),
        (
            lambda module: module["selection"]["score_modifiers"][0].__setitem__("weight", 2),
            "2 is greater than the maximum of 1",
        ),
        (
            lambda module: module.pop("task_signals"),
            "'task_signals' is a required property",
        ),
    ],
)
def test_invalid_module_metadata_is_rejected(
    module_schema: dict[str, Any],
    module_example: dict[str, Any],
    mutator: Any,
    message_part: str,
) -> None:
    invalid_module = deepcopy(module_example)
    mutator(invalid_module)

    assert_invalid(module_schema, invalid_module, message_part)


def test_keyword_only_module_metadata_is_rejected(
    module_schema: dict[str, Any],
    module_example: dict[str, Any],
) -> None:
    keyword_only_module = {
        key: value
        for key, value in module_example.items()
        if key not in {"capability_class", "domain_tags", "task_signals", "selection"}
    }

    assert_invalid(module_schema, keyword_only_module, "'capability_class' is a required property")


@pytest.mark.parametrize(
    ("mutator", "message_part"),
    [
        (
            lambda profile: profile.pop("module_versions"),
            "'module_versions' is a required property",
        ),
        (
            lambda profile: profile.__setitem__("risk_level", "severe"),
            "'severe' is not one of",
        ),
        (
            lambda profile: profile["limits"].pop("max_tokens"),
            "'max_tokens' is a required property",
        ),
        (
            lambda profile: profile["failure_policy"].__setitem__(
                "on_policy_denial",
                "continue_anyway",
            ),
            "'continue_anyway' is not one of",
        ),
    ],
)
def test_invalid_runtime_profiles_are_rejected_by_schema(
    profile_schema: dict[str, Any],
    profile_example: dict[str, Any],
    mutator: Any,
    message_part: str,
) -> None:
    invalid_profile = deepcopy(profile_example)
    mutator(invalid_profile)

    assert_invalid(profile_schema, invalid_profile, message_part)


def test_runtime_profile_rejects_missing_version_pin(
    profile_schema: dict[str, Any],
    profile_example: dict[str, Any],
) -> None:
    invalid_profile = deepcopy(profile_example)
    invalid_profile["module_versions"].pop("git-diff-analysis")

    assert_valid(profile_schema, invalid_profile)
    with pytest.raises(AssertionError, match="missing version pins"):
        assert_profile_version_pins_selected_modules(invalid_profile)


def test_runtime_profile_rejects_unselected_version_pin(
    profile_schema: dict[str, Any],
    profile_example: dict[str, Any],
) -> None:
    invalid_profile = deepcopy(profile_example)
    invalid_profile["module_versions"]["unselected-module"] = "0.1.0"

    assert_valid(profile_schema, invalid_profile)
    with pytest.raises(AssertionError, match="unselected version pins"):
        assert_profile_version_pins_selected_modules(invalid_profile)


@pytest.mark.parametrize(
    ("mutator", "message_part"),
    [
        (
            lambda control_plane: control_plane["records"]["modules"][0].pop("id"),
            "'id' is a required property",
        ),
        (
            lambda control_plane: control_plane["records"]["audit_events"][0].pop(
                "retention_policy"
            ),
            "'retention_policy' is a required property",
        ),
        (
            lambda control_plane: control_plane["records"]["audit_events"][0].pop("archive_after"),
            "'archive_after' is a required property",
        ),
    ],
)
def test_invalid_control_plane_records_are_rejected_by_schema(
    control_plane_schema: dict[str, Any],
    control_plane_example: dict[str, Any],
    mutator: Any,
    message_part: str,
) -> None:
    invalid_control_plane = deepcopy(control_plane_example)
    mutator(invalid_control_plane)

    assert_invalid(control_plane_schema, invalid_control_plane, message_part)


def test_control_plane_rejects_invalid_scope_reference(
    control_plane_schema: dict[str, Any],
    control_plane_example: dict[str, Any],
) -> None:
    invalid_control_plane = deepcopy(control_plane_example)
    invalid_control_plane["records"]["memory_records"][0]["memory_scope_id"] = (
        "mod-git-diff-analysis"
    )

    assert_valid(control_plane_schema, invalid_control_plane)
    with pytest.raises(AssertionError, match="kind"):
        assert_control_plane_references_are_valid(invalid_control_plane)


def test_cloudflare_d1_migration_contains_required_tables_and_indexes() -> None:
    expected_tables = {
        "modules",
        "module_versions",
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
    migration_sql = load_text(D1_MIGRATION_PATH)

    assert "FOREIGN KEY (module_id) REFERENCES modules (id)" in migration_sql
    assert "FOREIGN KEY (source_id) REFERENCES knowledge_sources (id)" in migration_sql
    assert "FOREIGN KEY (memory_scope_id) REFERENCES modules (id)" in migration_sql
    assert "FOREIGN KEY (policy_id) REFERENCES modules (id)" in migration_sql
    assert "selection_base_score >= 0" in migration_sql
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


@pytest.mark.parametrize(
    ("mutator", "message_part"),
    [
        (
            lambda runtime_plane: runtime_plane["records"]["runtime_runs"][0].pop("id"),
            "'id' is a required property",
        ),
        (
            lambda runtime_plane: runtime_plane["records"]["memory_candidates"][0].pop(
                "validator_status"
            ),
            "'validator_status' is a required property",
        ),
        (
            lambda runtime_plane: runtime_plane["records"]["memory_candidates"][0].pop(
                "policy_status"
            ),
            "'policy_status' is a required property",
        ),
    ],
)
def test_invalid_runtime_plane_records_are_rejected_by_schema(
    runtime_plane_schema: dict[str, Any],
    runtime_plane_example: dict[str, Any],
    mutator: Any,
    message_part: str,
) -> None:
    invalid_runtime_plane = deepcopy(runtime_plane_example)
    mutator(invalid_runtime_plane)

    assert_invalid(runtime_plane_schema, invalid_runtime_plane, message_part)


def test_runtime_plane_rejects_invalid_runtime_reference(
    runtime_plane_schema: dict[str, Any],
    runtime_plane_example: dict[str, Any],
) -> None:
    invalid_runtime_plane = deepcopy(runtime_plane_example)
    invalid_runtime_plane["records"]["memory_candidates"][0]["source_step_id"] = "missing-step"

    assert_valid(runtime_plane_schema, invalid_runtime_plane)
    with pytest.raises(AssertionError):
        assert_runtime_plane_references_are_valid(invalid_runtime_plane)
