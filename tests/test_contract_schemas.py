from __future__ import annotations

# ruff: noqa: F403,F405,I001

from copy import deepcopy
from tests.contract_schema_support import *  # noqa: F403


@pytest.mark.parametrize(
    ("mutator", "message_part"),
    [
        (
            lambda module: module.pop("selection"),
            "'selection' is a required property",
        ),
        (
            lambda module: module.pop("provenance"),
            "'provenance' is a required property",
        ),
        (
            lambda module: module.pop("selection_evidence"),
            "'selection_evidence' is a required property",
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
            lambda module: module["selection"].__setitem__("mode", "legacy"),
            "'legacy' is not one of",
        ),
        (
            lambda module: module["provenance"]["owner"].__setitem__("type", "team"),
            "'person' was expected",
        ),
        (
            lambda module: module["entrypoint"].pop("guidance"),
            "'guidance' is a required property",
        ),
        (
            lambda module: module["entrypoint"].__setitem__("guidance", "selection_metadata"),
            "'selection_metadata' is not one of",
        ),
        (
            lambda module: module["selection_evidence"].pop("positive_selection"),
            "'positive_selection' is a required property",
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


def test_dependency_only_module_metadata_rejects_direct_scoring(
    module_schema: dict[str, Any],
    module_example: dict[str, Any],
) -> None:
    dependency_only_module = deepcopy(module_example)
    dependency_only_module["selection"]["mode"] = "dependency_only"
    dependency_only_module["selection_evidence"] = {
        "dependency_inclusion": [
            {
                "fixture": "examples/registry/selection-evidence/git-diff-analysis.json",
                "expectation": "included_as_dependency",
                "reason": "test",
            }
        ],
        "no_direct_selection": [
            {
                "fixture": "examples/registry/selection-evidence/git-diff-analysis.json",
                "expectation": "not_directly_selected",
                "reason": "test",
            }
        ],
    }

    assert_invalid(module_schema, dependency_only_module, "should not be valid under")


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
        (
            lambda profile: profile.pop("human_review"),
            "'human_review' is a required property",
        ),
        (
            lambda profile: profile["human_review"].__setitem__("status", "maybe"),
            "'maybe' is not one of",
        ),
        (
            lambda profile: profile.pop("tenant_context"),
            "'tenant_context' is a required property",
        ),
        (
            lambda profile: profile.pop("tenant_authority"),
            "'tenant_authority' is a required property",
        ),
        (
            lambda profile: profile["tenant_context"]["role_derivation"].__setitem__(
                "direct_user_grants_allowed",
                True,
            ),
            "False was expected",
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
            lambda tenant: tenant.pop("role_bundles"),
            "'role_bundles' is a required property",
        ),
        (
            lambda tenant: tenant["admin_model"].__setitem__(
                "assignment_model",
                "users-receive-direct-skill-grants",
            ),
            "'users-receive-roles-only' was expected",
        ),
        (
            lambda tenant: tenant["memory"].__setitem__("shared_promotion_allowed", True),
            "False was expected",
        ),
        (
            lambda tenant: tenant.__setitem__(
                "ui_profile",
                {
                    "logo_path": None,
                    "experience_standard": "sota-2026-tenant-crm",
                    "brand_assets": {
                        "logo_path": None,
                        "favicon_path": None,
                        "app_icon_path": None,
                        "asset_scope": "tenant-owned",
                    },
                    "landing": {
                        "type": "internal-operations-dashboard",
                        "area_presentation": "tiles",
                    },
                    "theme": {
                        "background": "white",
                        "surface": "#fff",
                        "text": "#111",
                        "secondary_text": "#333",
                        "accent": "#76b726",
                        "border": "#76b726",
                    },
                    "navigation": {
                        "primary_area_ids": ["research"],
                        "admin_area_ids": [],
                    },
                    "command_center": {
                        "enabled": True,
                        "surfaces": ["global-search", "scas-actions"],
                        "default_route": "/",
                    },
                    "scas_skill_packs": [
                        {
                            "id": "demo-research-assistance",
                            "task_types": ["tenant-research"],
                            "required_capabilities": ["research"],
                            "status": "planned",
                        }
                    ],
                    "terminology": {
                        "customer": "Customer"
                    },
                    "workspace_areas": [
                        {
                            "id": "research",
                            "display_name": "Research",
                            "description": "Tenant research workspace.",
                            "route": "/research",
                            "required_capability": "research",
                            "admin_only": False,
                            "status": "demo",
                        }
                    ],
                },
            ),
            "'white' does not match",
        ),
    ],
)
def test_invalid_tenant_registry_entries_are_rejected(
    tenant_registry_schema: dict[str, Any],
    tenant_registry_example: dict[str, Any],
    mutator: Any,
    message_part: str,
) -> None:
    invalid_tenant = deepcopy(tenant_registry_example)
    mutator(invalid_tenant)

    assert_invalid(tenant_registry_schema, invalid_tenant, message_part)


def test_tenant_registry_rejects_cross_tenant_role_data_source_reference(
    tenant_registry_schema: dict[str, Any],
    tenant_registry_example: dict[str, Any],
) -> None:
    invalid_tenant = deepcopy(tenant_registry_example)
    invalid_tenant["data_sources"][0]["tenant_id"] = "other-tenant"

    assert_valid(tenant_registry_schema, invalid_tenant)
    with pytest.raises(AssertionError, match="belongs to other-tenant"):
        assert_tenant_registry_references_are_valid(invalid_tenant)


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


def test_invalid_composition_context_request_is_rejected(
    composition_context_schema: dict[str, Any],
    composition_context_request_example: dict[str, Any],
) -> None:
    invalid_request = deepcopy(composition_context_request_example)
    invalid_request["task"].pop("signals")

    assert_invalid(
        schema_ref(composition_context_schema, "#/$defs/request"),
        invalid_request,
        "'signals' is a required property",
    )


def test_invalid_composition_context_response_is_rejected(
    composition_context_schema: dict[str, Any],
    composition_context_response_example: dict[str, Any],
) -> None:
    invalid_response = deepcopy(composition_context_response_example)
    invalid_response["candidate_modules"].append(
        {
            "id": "mod-invalid",
            "name": "invalid",
            "kind": "agent",
            "version": "0.1.0",
            "score": 0.5,
        }
    )

    assert_invalid(
        schema_ref(composition_context_schema, "#/$defs/response"),
        invalid_response,
        "'agent' is not one of",
    )


def test_invalid_retrieval_context_request_is_rejected(
    retrieval_context_schema: dict[str, Any],
    retrieval_context_request_example: dict[str, Any],
) -> None:
    invalid_request = deepcopy(retrieval_context_request_example)
    invalid_request["top_k"] = 0

    assert_invalid(
        schema_ref(retrieval_context_schema, "#/$defs/request"),
        invalid_request,
        "0 is less than the minimum of 1",
    )


def test_invalid_retrieval_context_response_is_rejected(
    retrieval_context_schema: dict[str, Any],
    retrieval_context_response_example: dict[str, Any],
) -> None:
    invalid_response = deepcopy(retrieval_context_response_example)
    invalid_response["vectorize"]["status"] = "freeform"

    assert_invalid(
        schema_ref(retrieval_context_schema, "#/$defs/response"),
        invalid_response,
        "'freeform' is not one of",
    )
