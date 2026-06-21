from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_centric_agent_system.control_plane import (
    TenantHostnameResolutionError,
    TenantHostnameResolver,
    build_seed_records,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TENANTS_DIR = REPO_ROOT / "examples" / "tenants"
MODULES_DIR = REPO_ROOT / "registry" / "modules"
CRM_SKILL_PACKS_DIR = REPO_ROOT / "examples" / "crm-skill-packs"
DKH_ACTION_AUDIT_MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0007_crm_action_audit_evidence.sql"
)


def tenant_paths() -> list[Path]:
    return sorted(TENANTS_DIR.glob("*.json"))


def module_paths() -> list[Path]:
    return sorted(MODULES_DIR.rglob("module.json"))


def load_tenant(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_tenant_hostnames_resolve_to_exactly_one_active_or_setup_tenant() -> None:
    resolver = TenantHostnameResolver.from_paths(tenant_paths())

    expected = {
        "demo-tenant.example.invalid": "demo-tenant",
        "liquisto.condata.io": "liquisto",
        "daskuechenhaus.condata.io": "daskuechenhaus",
    }
    for hostname, tenant_id in expected.items():
        authority = resolver.resolve(hostname)
        assert authority.tenant_id == tenant_id
        assert authority.hostname == hostname

    with pytest.raises(TenantHostnameResolutionError, match="not active"):
        resolver.resolve("inactive-demo-tenant.example.invalid")


def test_seed_memberships_do_not_cross_tenant_role_boundaries() -> None:
    seed = build_seed_records(module_paths(), tenant_paths=tenant_paths())
    role_tenant_by_id = {
        role["id"]: role["tenant_id"] for role in seed.tenant_role_bundles
    }

    for membership in seed.tenant_memberships:
        role_ids = json.loads(membership["role_ids_json"])
        for role_id in role_ids:
            assert role_tenant_by_id[role_id] == membership["tenant_id"]


def test_seed_data_source_grants_do_not_cross_tenant_boundaries() -> None:
    seed = build_seed_records(module_paths(), tenant_paths=tenant_paths())
    role_tenant_by_id = {
        role["id"]: role["tenant_id"] for role in seed.tenant_role_bundles
    }
    source_tenant_by_id = {
        source["id"]: source["tenant_id"] for source in seed.tenant_data_sources
    }

    for grant in seed.tenant_role_data_source_grants:
        assert role_tenant_by_id[grant["role_bundle_id"]] == grant["tenant_id"]
        assert source_tenant_by_id[grant["data_source_id"]] == grant["tenant_id"]


def test_seeded_tenant_scopes_are_disjoint() -> None:
    seed = build_seed_records(module_paths(), tenant_paths=tenant_paths())
    module_names = {module["name"] for module in seed.modules}

    assert "liquisto-website-read" in module_names
    assert "demo-tenant-website-read" in module_names
    assert "daskuechenhaus-website-read" in module_names
    assert "knowledge-liquisto-docs" in module_names
    assert "knowledge-demo-tenant-docs" in module_names
    assert "knowledge-daskuechenhaus-docs" in module_names
    assert "liquisto-website-read" != "demo-tenant-website-read"
    assert "liquisto-website-read" != "daskuechenhaus-website-read"
    assert "demo-tenant-website-read" != "daskuechenhaus-website-read"
    assert "knowledge-liquisto-docs" != "knowledge-demo-tenant-docs"
    assert "knowledge-liquisto-docs" != "knowledge-daskuechenhaus-docs"
    assert "knowledge-demo-tenant-docs" != "knowledge-daskuechenhaus-docs"


def test_tenant_ui_assets_do_not_fallback_across_tenant_directories() -> None:
    for path in tenant_paths():
        tenant = load_tenant(path)
        ui_profile = tenant.get("ui_profile")
        if not isinstance(ui_profile, dict):
            continue

        tenant_id = str(tenant["tenant_id"])
        brand_assets = ui_profile["brand_assets"]
        logo_path = str(brand_assets["logo_path"])
        assert brand_assets["asset_scope"] == "tenant-owned"
        assert logo_path == ui_profile["logo_path"]
        assert logo_path.startswith(f"assets/images/{tenant_id}/")
        assert (REPO_ROOT / logo_path).is_file()

        for optional_asset in ("favicon_path", "app_icon_path"):
            asset_path = brand_assets[optional_asset]
            if asset_path is not None:
                assert str(asset_path).startswith(f"assets/images/{tenant_id}/")


def test_tenant_crm_skill_pack_bindings_are_tenant_local() -> None:
    skill_packs = {
        load_json(path)["id"]: load_json(path)
        for path in sorted(CRM_SKILL_PACKS_DIR.glob("*.json"))
    }

    for path in tenant_paths():
        tenant = load_tenant(path)
        ui_profile = tenant.get("ui_profile")
        if not isinstance(ui_profile, dict):
            continue

        tenant_capabilities = {
            capability
            for role in tenant["role_bundles"]
            for capability in role["capability_grants"]
        }
        for binding in ui_profile["scas_skill_packs"]:
            skill_pack = skill_packs[binding["id"]]
            assert skill_pack["tenant_id"] == tenant["tenant_id"]
            assert skill_pack["task_types"] == binding["task_types"]
            assert skill_pack["required_capabilities"] == binding["required_capabilities"]
            assert set(skill_pack["required_capabilities"]).issubset(tenant_capabilities)
            assert skill_pack["ui_binding"]["grants_runtime_authority"] is False
            assert skill_pack["composition"]["selection_path"] == (
                "registry-scoring-policy-graph-profile"
            )


def test_daskuechenhaus_crm_audit_evidence_is_tenant_pinned() -> None:
    migration = DKH_ACTION_AUDIT_MIGRATION_PATH.read_text(encoding="utf-8")

    assert "tenant_id TEXT NOT NULL DEFAULT 'daskuechenhaus'" in migration
    assert "hetzner" not in migration.lower()
    assert "communication_events_skill_pack_idx" in migration
