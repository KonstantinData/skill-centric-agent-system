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


def tenant_paths() -> list[Path]:
    return sorted(TENANTS_DIR.glob("*.json"))


def module_paths() -> list[Path]:
    return sorted(MODULES_DIR.rglob("module.json"))


def load_tenant(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_tenant_hostnames_resolve_to_exactly_one_active_or_setup_tenant() -> None:
    resolver = TenantHostnameResolver.from_paths(tenant_paths())

    expected = {
        "demo-tenant.example.invalid": "demo-tenant",
        "liquisto.condata.io": "liquisto",
        "schober-daskuechenhaus.de": "schober-daskuechenhaus",
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
    assert "schober-daskuechenhaus-website-read" in module_names
    assert "knowledge-liquisto-docs" in module_names
    assert "knowledge-demo-tenant-docs" in module_names
    assert "knowledge-schober-daskuechenhaus-docs" in module_names
    assert "liquisto-website-read" != "demo-tenant-website-read"
    assert "liquisto-website-read" != "schober-daskuechenhaus-website-read"
    assert "demo-tenant-website-read" != "schober-daskuechenhaus-website-read"
    assert "knowledge-liquisto-docs" != "knowledge-demo-tenant-docs"
    assert "knowledge-liquisto-docs" != "knowledge-schober-daskuechenhaus-docs"
    assert "knowledge-demo-tenant-docs" != "knowledge-schober-daskuechenhaus-docs"
