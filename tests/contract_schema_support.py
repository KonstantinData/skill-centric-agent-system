from __future__ import annotations

import json
import sqlite3
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
RUNTIME_API_SCHEMA_PATH = REPO_ROOT / "schemas" / "runtime-api.schema.json"
COMPOSITION_CONTEXT_SCHEMA_PATH = REPO_ROOT / "schemas" / "composition-context.schema.json"
RETRIEVAL_CONTEXT_SCHEMA_PATH = REPO_ROOT / "schemas" / "retrieval-context.schema.json"
RUNTIME_OUTPUT_SCHEMA_PATH = REPO_ROOT / "schemas" / "runtime-output.schema.json"
TENANT_RUNTIME_EVIDENCE_SCHEMA_PATH = (
    REPO_ROOT / "schemas" / "tenant-runtime-evidence.schema.json"
)
TENANT_REGISTRY_SCHEMA_PATH = REPO_ROOT / "schemas" / "tenant-registry.schema.json"
CRM_SKILL_PACK_SCHEMA_PATH = REPO_ROOT / "schemas" / "crm-skill-pack.schema.json"
CRM_SKILL_PACK_EXAMPLE_PATH = (
    REPO_ROOT / "examples" / "crm-skill-packs" / "generic-email-assignment.json"
)
MODULE_EXAMPLE_PATH = (
    REPO_ROOT
    / "registry"
    / "modules"
    / "common"
    / "skills"
    / "git-diff-analysis"
    / "module.json"
)
PROFILE_EXAMPLE_PATH = REPO_ROOT / "examples" / "profiles" / "code-review-profile.json"
HUMAN_REVIEW_PROFILE_EXAMPLE_PATH = (
    REPO_ROOT / "examples" / "profiles" / "human-review-required-profile.json"
)
CONTROL_PLANE_EXAMPLE_PATH = (
    REPO_ROOT / "examples" / "control-plane" / "cloudflare-control-plane.json"
)
RUNTIME_PLANE_EXAMPLE_PATH = (
    REPO_ROOT / "examples" / "runtime-plane" / "hetzner-runtime-plane.json"
)
COMPOSITION_CONTEXT_REQUEST_EXAMPLE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-request.json"
)
COMPOSITION_CONTEXT_RESPONSE_EXAMPLE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response.json"
)
COMPOSITION_CONTEXT_RESPONSE_EXAMPLE_PATHS = tuple(
    sorted((REPO_ROOT / "examples" / "control-api").glob("composition-context-response*.json"))
)
RETRIEVAL_CONTEXT_REQUEST_EXAMPLE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "retrieval-context-request.json"
)
RETRIEVAL_CONTEXT_RESPONSE_EXAMPLE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "retrieval-context-response.json"
)
TENANT_REGISTRY_EXAMPLE_PATH = REPO_ROOT / "examples" / "tenants" / "tenant-under-test.json"
D1_MIGRATION_DIR = REPO_ROOT / "migrations" / "cloudflare" / "d1"
D1_MIGRATION_PATHS = tuple(sorted(D1_MIGRATION_DIR.glob("*.sql")))


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


@pytest.fixture(scope="module")
def runtime_api_schema() -> dict[str, Any]:
    schema = load_json(RUNTIME_API_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture(scope="module")
def composition_context_schema() -> dict[str, Any]:
    schema = load_json(COMPOSITION_CONTEXT_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture(scope="module")
def retrieval_context_schema() -> dict[str, Any]:
    schema = load_json(RETRIEVAL_CONTEXT_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture(scope="module")
def runtime_output_schema() -> dict[str, Any]:
    schema = load_json(RUNTIME_OUTPUT_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture(scope="module")
def tenant_runtime_evidence_schema() -> dict[str, Any]:
    schema = load_json(TENANT_RUNTIME_EVIDENCE_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture(scope="module")
def tenant_registry_schema() -> dict[str, Any]:
    schema = load_json(TENANT_REGISTRY_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture(scope="module")
def crm_skill_pack_schema() -> dict[str, Any]:
    schema = load_json(CRM_SKILL_PACK_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture
def module_example() -> dict[str, Any]:
    return load_json(MODULE_EXAMPLE_PATH)


@pytest.fixture
def profile_example() -> dict[str, Any]:
    return load_json(PROFILE_EXAMPLE_PATH)


@pytest.fixture
def human_review_profile_example() -> dict[str, Any]:
    return load_json(HUMAN_REVIEW_PROFILE_EXAMPLE_PATH)


@pytest.fixture
def control_plane_example() -> dict[str, Any]:
    return load_json(CONTROL_PLANE_EXAMPLE_PATH)


@pytest.fixture
def runtime_plane_example() -> dict[str, Any]:
    return load_json(RUNTIME_PLANE_EXAMPLE_PATH)


@pytest.fixture
def composition_context_request_example() -> dict[str, Any]:
    return load_json(COMPOSITION_CONTEXT_REQUEST_EXAMPLE_PATH)


@pytest.fixture
def composition_context_response_example() -> dict[str, Any]:
    return load_json(COMPOSITION_CONTEXT_RESPONSE_EXAMPLE_PATH)


@pytest.fixture
def retrieval_context_request_example() -> dict[str, Any]:
    return load_json(RETRIEVAL_CONTEXT_REQUEST_EXAMPLE_PATH)


@pytest.fixture
def retrieval_context_response_example() -> dict[str, Any]:
    return load_json(RETRIEVAL_CONTEXT_RESPONSE_EXAMPLE_PATH)


@pytest.fixture
def tenant_registry_example() -> dict[str, Any]:
    return load_json(TENANT_REGISTRY_EXAMPLE_PATH)


@pytest.fixture
def crm_skill_pack_example() -> dict[str, Any]:
    return load_json(CRM_SKILL_PACK_EXAMPLE_PATH)


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
    tenants = {tenant["id"]: tenant for tenant in records["tenants"]}
    tenant_data_sources = {
        data_source["id"]: data_source
        for data_source in records["tenant_data_sources"]
    }
    tenant_role_bundles = {
        role_bundle["id"]: role_bundle
        for role_bundle in records["tenant_role_bundles"]
    }

    for module in records["modules"]:
        current_version = module_versions.get(module["current_version_id"])
        assert current_version, f"missing current module version: {module['current_version_id']}"
        assert current_version["module_id"] == module["id"]

    for module_version in records["module_versions"]:
        assert module_version["module_id"] in modules

    for metadata in records["module_selection_metadata"]:
        assert metadata["module_version_id"] in module_versions

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

    for hostname in records["tenant_hostnames"]:
        assert hostname["tenant_id"] in tenants

    for data_source in records["tenant_data_sources"]:
        assert data_source["tenant_id"] in tenants

    for role_bundle in records["tenant_role_bundles"]:
        assert role_bundle["tenant_id"] in tenants

    for membership in records["tenant_memberships"]:
        assert membership["tenant_id"] in tenants
        for role_id in membership["role_ids"]:
            role_bundle = tenant_role_bundles.get(role_id)
            assert role_bundle, f"missing tenant role bundle: {role_id}"
            assert role_bundle["tenant_id"] == membership["tenant_id"], (
                f"membership {membership['id']} crosses tenant boundary for role {role_id}"
            )

    for grant in records["tenant_role_capability_grants"]:
        assert grant["tenant_id"] in tenants
        role_bundle = tenant_role_bundles.get(grant["role_bundle_id"])
        assert role_bundle, f"missing tenant role bundle: {grant['role_bundle_id']}"
        assert role_bundle["tenant_id"] == grant["tenant_id"], (
            f"capability grant {grant['id']} crosses tenant boundary"
        )

    for grant in records["tenant_role_data_source_grants"]:
        assert grant["tenant_id"] in tenants
        role_bundle = tenant_role_bundles.get(grant["role_bundle_id"])
        data_source = tenant_data_sources.get(grant["data_source_id"])
        assert role_bundle, f"missing tenant role bundle: {grant['role_bundle_id']}"
        assert data_source, f"missing tenant data source: {grant['data_source_id']}"
        assert role_bundle["tenant_id"] == grant["tenant_id"], (
            f"data source grant {grant['id']} crosses tenant boundary for role"
        )
        assert data_source["tenant_id"] == grant["tenant_id"], (
            f"data source grant {grant['id']} crosses tenant boundary for source"
        )


def assert_runtime_plane_references_are_valid(runtime_plane: dict[str, Any]) -> None:
    records = runtime_plane["records"]
    runs = {run["id"]: run for run in records["runtime_runs"]}
    steps = {step["id"]: step for step in records["runtime_steps"]}

    for step in records["runtime_steps"]:
        assert step["run_id"] in runs

    for event in records["runtime_events"]:
        assert event["run_id"] in runs
        if event["step_id"] is not None:
            assert event["step_id"] in steps

    for checkpoint in records["runtime_checkpoints"]:
        assert checkpoint["run_id"] in runs
        if checkpoint["step_id"] is not None:
            assert checkpoint["step_id"] in steps

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


def assert_tenant_registry_references_are_valid(tenant: dict[str, Any]) -> None:
    tenant_id = tenant["tenant_id"]
    data_sources = {source["id"]: source for source in tenant["data_sources"]}
    role_capabilities = {
        capability
        for role in tenant["role_bundles"]
        for capability in role["capability_grants"]
    }

    assert tenant["area_id"], "tenant area_id must be set"
    assert tenant["memory"]["area_brain_id"].endswith(tenant_id), (
        "tenant memory area brain must be tenant-specific"
    )
    assert tenant["knowledge"]["scope_id"].endswith(tenant_id), (
        "tenant knowledge scope must be tenant-specific"
    )

    for source in tenant["data_sources"]:
        assert source["tenant_id"] == tenant_id, (
            f"data source {source['id']} belongs to {source['tenant_id']}, expected {tenant_id}"
        )

    for role in tenant["role_bundles"]:
        assert role["tenant_id"] == tenant_id, (
            f"role {role['id']} belongs to {role['tenant_id']}, expected {tenant_id}"
        )
        for grant in role["data_source_grants"]:
            source = data_sources.get(grant["data_source_id"])
            assert source, f"role {role['id']} references missing data source"
            assert source["tenant_id"] == role["tenant_id"]

    ui_profile = tenant.get("ui_profile")
    if not ui_profile:
        return

    assert ui_profile["experience_standard"] == "sota-2026-tenant-crm"
    assert ui_profile["brand_assets"]["asset_scope"] == "tenant-owned"
    assert ui_profile["brand_assets"]["logo_path"] == ui_profile["logo_path"]

    workspace_areas = {area["id"]: area for area in ui_profile["workspace_areas"]}
    workspace_routes = {area["route"] for area in ui_profile["workspace_areas"]}
    navigation = ui_profile["navigation"]
    navigation_ids = set(navigation["primary_area_ids"]) | set(navigation["admin_area_ids"])
    missing_navigation_ids = navigation_ids - set(workspace_areas)
    assert not missing_navigation_ids, (
        "tenant UI navigation references missing workspace areas: "
        + ", ".join(sorted(missing_navigation_ids))
    )

    for area_id in navigation["admin_area_ids"]:
        assert workspace_areas[area_id]["admin_only"] is True, (
            f"admin navigation area is not admin-only: {area_id}"
        )

    command_center = ui_profile["command_center"]
    assert command_center["enabled"] is True
    assert "scas-actions" in command_center["surfaces"]
    assert command_center["default_route"] == "/" or (
        command_center["default_route"] in workspace_routes
    ), f"command center default route is not a tenant workspace: {command_center['default_route']}"

    terminology = ui_profile["terminology"]
    for required_term in ("customer", "case", "task", "email", "cockpit"):
        assert required_term in terminology, f"missing tenant terminology: {required_term}"

    for skill_pack in ui_profile["scas_skill_packs"]:
        missing_capabilities = set(skill_pack["required_capabilities"]) - role_capabilities
        assert not missing_capabilities, (
            f"skill pack {skill_pack['id']} references ungranted capabilities: "
            + ", ".join(sorted(missing_capabilities))
        )


def schema_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    return {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": ref,
    }


def create_d1_control_plane_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    for migration_path in D1_MIGRATION_PATHS:
        connection.executescript(load_text(migration_path))
    return connection


def d1_migration_sql() -> str:
    return "\n".join(load_text(path) for path in D1_MIGRATION_PATHS)


def insert_control_plane_fixture(
    connection: sqlite3.Connection,
    control_plane: dict[str, Any],
) -> None:
    records = control_plane["records"]

    connection.executemany(
        """
        INSERT INTO tenants (
            id,
            area_id,
            display_name,
            legal_name,
            status,
            default_locale,
            contact_email,
            contact_phone,
            contact_website,
            memory_area_brain_id,
            shared_promotion_allowed,
            knowledge_scope_id,
            policy_bundle_json,
            validators_json,
            created_at,
            updated_at
        )
        VALUES (
            :id,
            :area_id,
            :display_name,
            :legal_name,
            :status,
            :default_locale,
            :contact_email,
            :contact_phone,
            :contact_website,
            :memory_area_brain_id,
            :shared_promotion_allowed,
            :knowledge_scope_id,
            :policy_bundle_json,
            :validators_json,
            :created_at,
            :updated_at
        )
        """,
        [
            {
                **tenant,
                "shared_promotion_allowed": int(tenant["shared_promotion_allowed"]),
                "policy_bundle_json": json.dumps(tenant["policy_bundle"]),
                "validators_json": json.dumps(tenant["validators"]),
            }
            for tenant in records["tenants"]
        ],
    )
    connection.executemany(
        """
        INSERT INTO tenant_hostnames (
            id,
            tenant_id,
            hostname,
            purpose,
            expected_origin,
            cloudflare_proxy_expected
        )
        VALUES (
            :id,
            :tenant_id,
            :hostname,
            :purpose,
            :expected_origin,
            :cloudflare_proxy_expected
        )
        """,
        [
            {
                **hostname,
                "cloudflare_proxy_expected": int(hostname["cloudflare_proxy_expected"]),
            }
            for hostname in records["tenant_hostnames"]
        ],
    )
    connection.executemany(
        """
        INSERT INTO tenant_data_sources (
            id,
            tenant_id,
            source_type,
            display_name,
            access_modes_json,
            status,
            sensitivity
        )
        VALUES (
            :id,
            :tenant_id,
            :source_type,
            :display_name,
            :access_modes_json,
            :status,
            :sensitivity
        )
        """,
        [
            {
                **data_source,
                "access_modes_json": json.dumps(data_source["access_modes"]),
            }
            for data_source in records["tenant_data_sources"]
        ],
    )
    connection.executemany(
        """
        INSERT INTO tenant_role_bundles (
            id,
            tenant_id,
            display_name,
            role_type,
            assignable_to_users,
            derived_skills_json,
            derived_workflows_json,
            derived_tools_json,
            derived_policies_json,
            derived_validators_json
        )
        VALUES (
            :id,
            :tenant_id,
            :display_name,
            :role_type,
            :assignable_to_users,
            :derived_skills_json,
            :derived_workflows_json,
            :derived_tools_json,
            :derived_policies_json,
            :derived_validators_json
        )
        """,
        [
            {
                **role_bundle,
                "assignable_to_users": int(role_bundle["assignable_to_users"]),
                "derived_skills_json": json.dumps(role_bundle["derived_skills"]),
                "derived_workflows_json": json.dumps(role_bundle["derived_workflows"]),
                "derived_tools_json": json.dumps(role_bundle["derived_tools"]),
                "derived_policies_json": json.dumps(role_bundle["derived_policies"]),
                "derived_validators_json": json.dumps(role_bundle["derived_validators"]),
            }
            for role_bundle in records["tenant_role_bundles"]
        ],
    )
    connection.executemany(
        """
        INSERT INTO tenant_memberships (
            id,
            tenant_id,
            principal_id,
            status,
            role_ids_json,
            created_at,
            updated_at
        )
        VALUES (
            :id,
            :tenant_id,
            :principal_id,
            :status,
            :role_ids_json,
            :created_at,
            :updated_at
        )
        """,
        [
            {
                **membership,
                "role_ids_json": json.dumps(membership["role_ids"]),
            }
            for membership in records["tenant_memberships"]
        ],
    )
    connection.executemany(
        """
        INSERT INTO tenant_role_capability_grants (
            id,
            tenant_id,
            role_bundle_id,
            capability_id
        )
        VALUES (
            :id,
            :tenant_id,
            :role_bundle_id,
            :capability_id
        )
        """,
        records["tenant_role_capability_grants"],
    )
    connection.executemany(
        """
        INSERT INTO tenant_role_data_source_grants (
            id,
            tenant_id,
            role_bundle_id,
            data_source_id,
            access_modes_json
        )
        VALUES (
            :id,
            :tenant_id,
            :role_bundle_id,
            :data_source_id,
            :access_modes_json
        )
        """,
        [
            {
                **grant,
                "access_modes_json": json.dumps(grant["access_modes"]),
            }
            for grant in records["tenant_role_data_source_grants"]
        ],
    )

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
        INSERT INTO module_selection_metadata (
            id,
            module_version_id,
            description,
            capability_class,
            domain_tags_json,
            task_types_json,
            risk_levels_json,
            task_domains_json,
            required_inputs_json,
            phrases_json,
            negative_phrases_json,
            triggers_json,
            inputs_json,
            outputs_json,
            score_modifiers_json,
            requires_all_policies
        )
        VALUES (
            :id,
            :module_version_id,
            :description,
            :capability_class,
            :domain_tags_json,
            :task_types_json,
            :risk_levels_json,
            :task_domains_json,
            :required_inputs_json,
            :phrases_json,
            :negative_phrases_json,
            :triggers_json,
            :inputs_json,
            :outputs_json,
            :score_modifiers_json,
            :requires_all_policies
        )
        """,
        [
            {
                **metadata,
                "domain_tags_json": json.dumps(metadata["domain_tags"]),
                "task_types_json": json.dumps(metadata["task_types"]),
                "risk_levels_json": json.dumps(metadata["risk_levels"]),
                "task_domains_json": json.dumps(metadata["task_domains"]),
                "required_inputs_json": json.dumps(metadata["required_inputs"]),
                "phrases_json": json.dumps(metadata["phrases"]),
                "negative_phrases_json": json.dumps(metadata["negative_phrases"]),
                "triggers_json": json.dumps(metadata["triggers"]),
                "inputs_json": json.dumps(metadata["inputs"]),
                "outputs_json": json.dumps(metadata["outputs"]),
                "score_modifiers_json": json.dumps(metadata["score_modifiers"]),
                "requires_all_policies": int(metadata["requires_all_policies"]),
            }
            for metadata in records["module_selection_metadata"]
        ],
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
