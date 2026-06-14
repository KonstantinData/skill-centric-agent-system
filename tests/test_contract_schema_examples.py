from __future__ import annotations

# ruff: noqa: F403,F405,I001

from tests.contract_schema_support import *  # noqa: F403


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


def test_human_review_profile_example_matches_schema_and_version_contract(
    profile_schema: dict[str, Any],
    human_review_profile_example: dict[str, Any],
) -> None:
    assert_valid(profile_schema, human_review_profile_example)
    assert_profile_version_pins_selected_modules(human_review_profile_example)
    assert human_review_profile_example["human_review"]["required"] is True
    assert human_review_profile_example["skills"] == []
    assert human_review_profile_example["tools"] == []
    assert human_review_profile_example["knowledge_scopes"] == []
    assert human_review_profile_example["data_scopes"] == []
    assert human_review_profile_example["memory_scopes"] == []


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


def test_composition_context_examples_match_schema(
    composition_context_schema: dict[str, Any],
    composition_context_request_example: dict[str, Any],
    composition_context_response_example: dict[str, Any],
) -> None:
    assert_valid(
        schema_ref(composition_context_schema, "#/$defs/request"),
        composition_context_request_example,
    )
    assert_valid(
        schema_ref(composition_context_schema, "#/$defs/response"),
        composition_context_response_example,
    )


def test_all_composition_context_response_fixtures_match_schema(
    composition_context_schema: dict[str, Any],
) -> None:
    response_schema = schema_ref(composition_context_schema, "#/$defs/response")
    for response_path in COMPOSITION_CONTEXT_RESPONSE_EXAMPLE_PATHS:
        assert_valid(response_schema, load_json(response_path))


def test_retrieval_context_examples_match_schema(
    retrieval_context_schema: dict[str, Any],
    retrieval_context_request_example: dict[str, Any],
    retrieval_context_response_example: dict[str, Any],
) -> None:
    assert_valid(
        schema_ref(retrieval_context_schema, "#/$defs/request"),
        retrieval_context_request_example,
    )
    assert_valid(
        schema_ref(retrieval_context_schema, "#/$defs/response"),
        retrieval_context_response_example,
    )


def test_runtime_output_schema_is_valid(runtime_output_schema: dict[str, Any]) -> None:
    assert runtime_output_schema["$id"] == "urn:scas:schema:runtime-output:0.1.0"


def test_demo_tenant_registry_example_matches_schema(
    tenant_registry_schema: dict[str, Any],
    tenant_registry_example: dict[str, Any],
) -> None:
    assert_valid(tenant_registry_schema, tenant_registry_example)
    assert_tenant_registry_references_are_valid(tenant_registry_example)
    assert tenant_registry_example["tenant_id"] == "demo-tenant"
    assert tenant_registry_example["admin_model"]["assignment_model"] == (
        "users-receive-roles-only"
    )
    assert tenant_registry_example["legal_profile"]["tax"]["tax_number"] is None
