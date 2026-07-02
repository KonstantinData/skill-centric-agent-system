from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from skill_centric_agent_system.control_plane import (
    TenantHostnameResolutionError,
    TenantHostnameResolver,
    normalize_hostname,
)
from tests.tenant_authority_support import LEGACY_TENANTS_DIR, tenant_authority_paths

REPO_ROOT = Path(__file__).resolve().parents[1]


def tenant_paths() -> list[Path]:
    return tenant_authority_paths()


def load_tenant(name: str) -> dict[str, Any]:
    return json.loads((LEGACY_TENANTS_DIR / name).read_text(encoding="utf-8"))


def test_tenant_hostname_resolver_returns_single_configured_authority() -> None:
    resolver = TenantHostnameResolver.from_paths(tenant_paths())

    authority = resolver.resolve("Tenant-Under-Test.Example.Invalid.")

    assert authority.tenant_id == "tenant-under-test"
    assert authority.area_id == "tenant-under-test"
    assert authority.hostname == "tenant-under-test.example.invalid"
    assert authority.purpose == "primary-ui"
    assert authority.status == "setup"
    assert authority.expected_origin == "192.0.2.10"
    assert authority.cloudflare_proxy_expected is True


def test_tenant_hostname_resolver_returns_liquisto_authority() -> None:
    resolver = TenantHostnameResolver.from_paths(tenant_paths())

    authority = resolver.resolve("liquisto.cloud")

    assert authority.tenant_id == "liquisto"
    assert authority.area_id == "liquisto"
    assert authority.hostname == "liquisto.cloud"
    assert authority.purpose == "primary-ui"
    assert authority.status == "setup"
    assert authority.expected_origin == "145.239.222.45"
    assert authority.cloudflare_proxy_expected is True


def test_tenant_hostname_resolver_returns_daskuechenhaus_setup_authority() -> None:
    resolver = TenantHostnameResolver.from_paths(tenant_paths())

    authority = resolver.resolve("daskuechenhaus.condata.io")

    assert authority.tenant_id == "daskuechenhaus"
    assert authority.area_id == "daskuechenhaus"
    assert authority.hostname == "daskuechenhaus.condata.io"
    assert authority.purpose == "primary-ui"
    assert authority.status == "setup"
    assert authority.expected_origin == "178.105.62.169"
    assert authority.cloudflare_proxy_expected is True


def test_tenant_hostname_resolver_returns_kinderhaus_setup_authority() -> None:
    resolver = TenantHostnameResolver.from_paths(tenant_paths())

    authority = resolver.resolve("kinderhaus-heuschrecken.cloud")

    assert authority.tenant_id == "tenant_kinderhaus"
    assert authority.area_id == "kinderhaus-heuschrecken"
    assert authority.hostname == "kinderhaus-heuschrecken.cloud"
    assert authority.purpose == "primary-ui"
    assert authority.status == "setup"
    assert authority.expected_origin is None
    assert authority.cloudflare_proxy_expected is True


def test_tenant_hostname_resolver_rejects_unknown_hostname() -> None:
    resolver = TenantHostnameResolver.from_paths(tenant_paths())

    with pytest.raises(TenantHostnameResolutionError, match="Unknown tenant hostname"):
        resolver.resolve("unknown.example.invalid")


def test_tenant_hostname_resolver_rejects_inactive_tenant_hostname() -> None:
    tenant = load_tenant("tenant-under-test.json")
    tenant["status"] = "disabled"
    resolver = TenantHostnameResolver([tenant])

    with pytest.raises(TenantHostnameResolutionError, match="not active"):
        resolver.resolve("tenant-under-test.example.invalid")


def test_tenant_hostname_resolver_rejects_duplicate_hostname_configuration() -> None:
    tenant = load_tenant("tenant-under-test.json")
    duplicate = deepcopy(tenant)
    duplicate["tenant_id"] = "duplicate-tenant-under-test"
    duplicate["area_id"] = "duplicate-tenant-under-test"

    with pytest.raises(TenantHostnameResolutionError, match="Duplicate tenant hostname"):
        TenantHostnameResolver([tenant, duplicate])


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("TENANT-UNDER-TEST.EXAMPLE.INVALID", "tenant-under-test.example.invalid"),
        ("tenant-under-test.example.invalid.", "tenant-under-test.example.invalid"),
        ("tenant-under-test.example.invalid:443", "tenant-under-test.example.invalid"),
    ],
)
def test_normalize_hostname_accepts_hostname_variants(raw: str, expected: str) -> None:
    assert normalize_hostname(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "https://tenant-under-test.example.invalid",
        "tenant-under-test.example.invalid/path",
        "",
        "tenant-under-test.example.invalid:http",
    ],
)
def test_normalize_hostname_rejects_non_hostname_inputs(raw: str) -> None:
    with pytest.raises(TenantHostnameResolutionError):
        normalize_hostname(raw)
