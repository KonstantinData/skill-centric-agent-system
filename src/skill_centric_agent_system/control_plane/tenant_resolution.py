from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ACTIVE_TENANT_STATUSES = frozenset(("setup", "active"))


class TenantHostnameResolutionError(ValueError):
    """Raised when hostname-based tenant resolution must fail closed."""


@dataclass(frozen=True)
class TenantHostnameAuthority:
    tenant_id: str
    area_id: str
    hostname: str
    purpose: str
    status: str
    expected_origin: str | None
    cloudflare_proxy_expected: bool


class TenantHostnameResolver:
    """Resolve one configured hostname to one tenant authority."""

    def __init__(self, tenants: Iterable[Mapping[str, Any]]) -> None:
        self._by_hostname: dict[str, TenantHostnameAuthority] = {}
        for tenant in tenants:
            self._add_tenant(tenant)

    @classmethod
    def from_paths(cls, tenant_paths: Iterable[Path]) -> TenantHostnameResolver:
        tenants = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(tenant_paths)
        ]
        return cls(tenants)

    def resolve(self, hostname: str) -> TenantHostnameAuthority:
        normalized = normalize_hostname(hostname)
        authority = self._by_hostname.get(normalized)
        if authority is None:
            raise TenantHostnameResolutionError(f"Unknown tenant hostname: {normalized}")
        if authority.status not in ACTIVE_TENANT_STATUSES:
            raise TenantHostnameResolutionError(
                f"Tenant hostname is not active: {normalized}"
            )
        return authority

    def _add_tenant(self, tenant: Mapping[str, Any]) -> None:
        tenant_id = _required_string(tenant, "tenant_id")
        area_id = _required_string(tenant, "area_id")
        status = _required_string(tenant, "status")
        hostnames = tenant.get("hostnames")
        if not isinstance(hostnames, list):
            raise TenantHostnameResolutionError(
                f"{tenant_id} tenant hostnames must be a list."
            )

        for hostname_record in hostnames:
            if not isinstance(hostname_record, Mapping):
                raise TenantHostnameResolutionError(
                    f"{tenant_id} tenant hostname record must be an object."
                )
            hostname = normalize_hostname(_required_string(hostname_record, "hostname"))
            existing = self._by_hostname.get(hostname)
            if existing is not None:
                raise TenantHostnameResolutionError(
                    f"Duplicate tenant hostname {hostname!r} for "
                    f"{existing.tenant_id!r} and {tenant_id!r}."
                )
            expected_origin = hostname_record.get("expected_origin")
            if expected_origin is not None and not isinstance(expected_origin, str):
                raise TenantHostnameResolutionError(
                    f"{tenant_id} hostname {hostname} expected_origin must be null or string."
                )
            cloudflare_proxy_expected = hostname_record.get("cloudflare_proxy_expected")
            if not isinstance(cloudflare_proxy_expected, bool):
                raise TenantHostnameResolutionError(
                    f"{tenant_id} hostname {hostname} cloudflare_proxy_expected must be bool."
                )
            self._by_hostname[hostname] = TenantHostnameAuthority(
                tenant_id=tenant_id,
                area_id=area_id,
                hostname=hostname,
                purpose=_required_string(hostname_record, "purpose"),
                status=status,
                expected_origin=expected_origin,
                cloudflare_proxy_expected=cloudflare_proxy_expected,
            )


def normalize_hostname(hostname: str) -> str:
    value = hostname.strip().casefold()
    if value.startswith("http://") or value.startswith("https://"):
        raise TenantHostnameResolutionError("Hostname must not include a URL scheme.")
    if "/" in value:
        raise TenantHostnameResolutionError("Hostname must not include a path.")
    if ":" in value:
        host, _, port = value.rpartition(":")
        if not host or not port.isdigit():
            raise TenantHostnameResolutionError("Hostname port suffix is invalid.")
        value = host
    value = value.rstrip(".")
    if not value:
        raise TenantHostnameResolutionError("Hostname is required.")
    return value


def _required_string(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TenantHostnameResolutionError(f"{key} is required.")
    return value.strip()
