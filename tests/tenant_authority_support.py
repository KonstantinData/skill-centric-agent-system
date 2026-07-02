from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_TENANTS_DIR = REPO_ROOT / "examples" / "tenants"
TENANT_REGISTRY_DIR = REPO_ROOT / "registry" / "tenants"
LEGACY_CRM_SKILL_PACKS_DIR = REPO_ROOT / "examples" / "crm-skill-packs"
TENANT_MODULES_DIR = REPO_ROOT / "registry" / "modules" / "tenants"


def tenant_authority_paths() -> list[Path]:
    legacy_paths = sorted(LEGACY_TENANTS_DIR.glob("*.json"))
    registry_paths = sorted(TENANT_REGISTRY_DIR.glob("*/tenant.json"))
    return sorted([*legacy_paths, *registry_paths], key=lambda path: path.as_posix())


def tenant_authority_path(tenant_id: str) -> Path:
    expected_name = f"{tenant_id}.json"
    for path in tenant_authority_paths():
        if path.name == expected_name or path.parent.name == tenant_id:
            return path
    raise FileNotFoundError(f"Missing tenant authority path for {tenant_id}")


def crm_skill_pack_paths() -> list[Path]:
    legacy_paths = sorted(LEGACY_CRM_SKILL_PACKS_DIR.glob("*.json"))
    tenant_module_paths = sorted(TENANT_MODULES_DIR.glob("*/skills/*/skill-pack.json"))
    return sorted([*legacy_paths, *tenant_module_paths], key=lambda path: path.as_posix())


def crm_skill_pack_path(skill_pack_id: str) -> Path:
    expected_name = f"{skill_pack_id}.json"
    for path in crm_skill_pack_paths():
        if path.name == expected_name:
            return path
        if path.name == "skill-pack.json" and path.parent.name == skill_pack_id:
            return path
    raise FileNotFoundError(f"Missing CRM skill pack authority path for {skill_pack_id}")
