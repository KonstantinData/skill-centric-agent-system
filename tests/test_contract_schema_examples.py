from __future__ import annotations

# ruff: noqa: F403,F405,I001

from tests.contract_schema_support import *  # noqa: F403


def test_module_example_matches_schema(
    module_schema: dict[str, Any],
    module_example: dict[str, Any],
) -> None:
    assert_valid(module_schema, module_example)


def test_crm_skill_pack_example_matches_schema(
    crm_skill_pack_schema: dict[str, Any],
    crm_skill_pack_example: dict[str, Any],
) -> None:
    assert_valid(crm_skill_pack_schema, crm_skill_pack_example)
    assert crm_skill_pack_example["ui_binding"]["confirmation_required"] is True
    assert crm_skill_pack_example["ui_binding"]["grants_runtime_authority"] is False
    assert crm_skill_pack_example["composition"]["requires_immutable_runtime_profile"] is True
    assert crm_skill_pack_example["audit_evidence"]["retention_plane"] == (
        "hetzner-runtime-plane"
    )


def test_all_crm_skill_pack_examples_match_schema(
    crm_skill_pack_schema: dict[str, Any],
) -> None:
    for skill_pack_path in sorted((REPO_ROOT / "examples" / "crm-skill-packs").glob("*.json")):
        assert_valid(crm_skill_pack_schema, load_json(skill_pack_path))


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


def test_liquisto_tenant_registry_example_matches_ui_profile_contract(
    tenant_registry_schema: dict[str, Any],
) -> None:
    liquisto = load_json(REPO_ROOT / "examples" / "tenants" / "liquisto.json")

    assert_valid(tenant_registry_schema, liquisto)
    assert_tenant_registry_references_are_valid(liquisto)
    assert liquisto["legal_profile"]["legal_name"] == "Liquisto Technologies GmbH"
    assert "Pending legal bootstrap" not in json.dumps(liquisto)
    assert liquisto["ui_profile"]["landing"] == {
        "type": "internal-operations-dashboard",
        "area_presentation": "tiles",
    }
    assert liquisto["ui_profile"]["experience_standard"] == "sota-2026-tenant-crm"
    assert (REPO_ROOT / liquisto["ui_profile"]["logo_path"]).is_file()
    assert liquisto["ui_profile"]["brand_assets"] == {
        "logo_path": "assets/images/liquisto/liquisto_logo.png",
        "favicon_path": None,
        "app_icon_path": None,
        "asset_scope": "tenant-owned",
    }
    assert liquisto["ui_profile"]["navigation"] == {
        "primary_area_ids": ["research"],
        "admin_area_ids": ["tenant-admin"],
    }
    assert "scas-actions" in liquisto["ui_profile"]["command_center"]["surfaces"]
    assert liquisto["ui_profile"]["scas_skill_packs"][0]["id"] == (
        "liquisto-research-assistance"
    )
    assert [area["id"] for area in liquisto["ui_profile"]["workspace_areas"]] == [
        "research",
        "tenant-admin",
    ]


def test_daskuechenhaus_tenant_registry_example_matches_schema_and_public_identity(
    tenant_registry_schema: dict[str, Any],
    crm_skill_pack_schema: dict[str, Any],
) -> None:
    daskuechenhaus = load_json(
        REPO_ROOT / "examples" / "tenants" / "daskuechenhaus.json"
    )

    assert_valid(tenant_registry_schema, daskuechenhaus)
    assert_tenant_registry_references_are_valid(daskuechenhaus)
    assert daskuechenhaus["tenant_id"] == "daskuechenhaus"
    assert daskuechenhaus["area_id"] == "daskuechenhaus"
    assert daskuechenhaus["status"] == "setup"
    assert daskuechenhaus["legal_profile"]["legal_name"] == (
        "das küchenhaus ralph schober GmbH"
    )
    assert daskuechenhaus["legal_profile"]["commercial_register"] == {
        "register_court": "Amtsgericht Stuttgart",
        "registration_number": "HR 730338",
    }
    assert daskuechenhaus["legal_profile"]["tax"]["vat_id"] == "DE265715198"
    assert (
        daskuechenhaus["contact_profile"]["email"]
        == "info@schober-daskuechenhaus.de"
    )
    assert (
        daskuechenhaus["ui_profile"]["logo_path"]
        == "assets/images/daskuechenhaus/logo_daskuechenhaus.png"
    )
    assert daskuechenhaus["ui_profile"]["experience_standard"] == (
        "sota-2026-tenant-crm"
    )
    assert (REPO_ROOT / daskuechenhaus["ui_profile"]["logo_path"]).is_file()
    assert daskuechenhaus["ui_profile"]["brand_assets"] == {
        "logo_path": "assets/images/daskuechenhaus/logo_daskuechenhaus.png",
        "favicon_path": None,
        "app_icon_path": None,
        "asset_scope": "tenant-owned",
    }
    assert daskuechenhaus["ui_profile"]["theme"] == {
        "background": "#fff",
        "surface": "#fff",
        "text": "#111",
        "secondary_text": "#333",
        "accent": "#76b726",
        "border": "#76b726",
    }
    assert daskuechenhaus["ui_profile"]["navigation"] == {
        "primary_area_ids": ["customer-cases", "research"],
        "admin_area_ids": ["tenant-admin"],
    }
    assert daskuechenhaus["ui_profile"]["command_center"] == {
        "enabled": True,
        "surfaces": [
            "global-search",
            "quick-actions",
            "notifications",
            "saved-views",
            "scas-actions",
        ],
        "default_route": "/",
    }
    assert [pack["id"] for pack in daskuechenhaus["ui_profile"]["scas_skill_packs"]] == [
        "daskuechenhaus-email-assignment",
        "daskuechenhaus-next-step-planning",
    ]
    daskuechenhaus_skill_pack_paths = sorted(
        (REPO_ROOT / "examples" / "crm-skill-packs").glob("daskuechenhaus-*.json")
    )
    daskuechenhaus_skill_packs = {}
    for path in daskuechenhaus_skill_pack_paths:
        skill_pack = load_json(path)
        daskuechenhaus_skill_packs[skill_pack["id"]] = skill_pack
    assert set(daskuechenhaus_skill_packs) == {
        "daskuechenhaus-email-assignment",
        "daskuechenhaus-next-step-planning",
    }
    for tenant_skill_pack in daskuechenhaus["ui_profile"]["scas_skill_packs"]:
        skill_pack = daskuechenhaus_skill_packs[tenant_skill_pack["id"]]
        assert_valid(crm_skill_pack_schema, skill_pack)
        assert skill_pack["tenant_id"] == daskuechenhaus["tenant_id"]
        assert skill_pack["task_types"] == tenant_skill_pack["task_types"]
        assert skill_pack["required_capabilities"] == tenant_skill_pack[
            "required_capabilities"
        ]
        assert skill_pack["ui_binding"]["grants_runtime_authority"] is False
        assert skill_pack["composition"]["requires_immutable_runtime_profile"] is True
    assert daskuechenhaus["ui_profile"]["terminology"]["case"] == "Vorgang"
    assert daskuechenhaus["admin_model"]["initial_owner"] is None
    assert daskuechenhaus["memory"]["shared_promotion_allowed"] is False
    admin_role = next(
        role for role in daskuechenhaus["role_bundles"] if role["id"] == "daskuechenhaus-admin"
    )
    assert admin_role["capability_grants"] == ["tenant-admin", "customer-cases"]
    assert admin_role["data_source_grants"] == []
    assert admin_role["derived_runtime_modules"]["tools"] == []
    assert [area["id"] for area in daskuechenhaus["ui_profile"]["workspace_areas"]] == [
        "customer-cases",
        "research",
        "tenant-admin",
    ]


def test_kinderhaus_tenant_registry_example_matches_schema_and_privacy_boundary(
    tenant_registry_schema: dict[str, Any],
    crm_skill_pack_schema: dict[str, Any],
) -> None:
    kinderhaus = load_json(REPO_ROOT / "examples" / "tenants" / "kinderhaus.json")

    assert_valid(tenant_registry_schema, kinderhaus)
    assert_tenant_registry_references_are_valid(kinderhaus)
    assert kinderhaus["tenant_id"] == "tenant_kinderhaus"
    assert kinderhaus["area_id"] == "kinderhaus-heuschrecken"
    assert kinderhaus["hostnames"] == [
        {
            "hostname": "kinderhaus-heuschrecken.cloud",
            "purpose": "primary-ui",
            "expected_origin": None,
            "cloudflare_proxy_expected": True,
        }
    ]
    assert kinderhaus["memory"]["shared_promotion_allowed"] is False
    assert kinderhaus["ui_profile"]["brand_assets"] == {
        "logo_path": "assets/images/tenant_kinderhaus/khh-workbench-logo.png",
        "favicon_path": None,
        "app_icon_path": None,
        "asset_scope": "tenant-owned",
    }
    assert (REPO_ROOT / kinderhaus["ui_profile"]["logo_path"]).is_file()
    assert kinderhaus["ui_profile"]["navigation"] == {
        "primary_area_ids": [
            "leadership-cockpit",
            "deadline-review",
            "development-planning",
        ],
        "admin_area_ids": ["tenant-admin"],
    }
    assert [pack["id"] for pack in kinderhaus["ui_profile"]["scas_skill_packs"]] == [
        "khh-deadline-assistance",
        "khh-development-planning",
    ]
    serialized = json.dumps(kinderhaus, sort_keys=True).lower()
    for forbidden in (
        "nachname",
        "adresse",
        "geburtsdatum",
        "diagnose",
        "personalakte",
        "liquisto",
        "daskuechenhaus",
    ):
        assert forbidden not in serialized

    for pack_ref in kinderhaus["ui_profile"]["scas_skill_packs"]:
        skill_pack = load_json(
            REPO_ROOT / "examples" / "crm-skill-packs" / f"{pack_ref['id']}.json"
        )
        assert_valid(crm_skill_pack_schema, skill_pack)
        assert skill_pack["tenant_id"] == kinderhaus["tenant_id"]
        assert skill_pack["task_types"] == pack_ref["task_types"]
        assert skill_pack["required_capabilities"] == pack_ref["required_capabilities"]
        assert skill_pack["ui_binding"]["grants_runtime_authority"] is False


def test_tenant_ui_profile_rejects_unknown_navigation_area(
    tenant_registry_schema: dict[str, Any],
) -> None:
    daskuechenhaus = load_json(
        REPO_ROOT / "examples" / "tenants" / "daskuechenhaus.json"
    )
    daskuechenhaus["ui_profile"]["navigation"]["primary_area_ids"].append(
        "foreign-area"
    )

    assert_valid(tenant_registry_schema, daskuechenhaus)
    with pytest.raises(AssertionError, match="missing workspace areas"):
        assert_tenant_registry_references_are_valid(daskuechenhaus)


def test_tenant_ui_profile_rejects_ungranted_skill_pack_capability(
    tenant_registry_schema: dict[str, Any],
) -> None:
    daskuechenhaus = load_json(
        REPO_ROOT / "examples" / "tenants" / "daskuechenhaus.json"
    )
    daskuechenhaus["ui_profile"]["scas_skill_packs"][0][
        "required_capabilities"
    ].append("foreign-capability")

    assert_valid(tenant_registry_schema, daskuechenhaus)
    with pytest.raises(AssertionError, match="ungranted capabilities"):
        assert_tenant_registry_references_are_valid(daskuechenhaus)
