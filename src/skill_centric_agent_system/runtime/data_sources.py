from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class TenantDataSourceError(ValueError):
    """Raised when a tenant data source is not available through role grants."""


@dataclass(frozen=True)
class TenantDataSourceHandle:
    data_source_id: str
    tenant_id: str
    access_mode: str
    status: str


class TenantDataSourceConnector:
    """Resolve tenant-owned data sources from the sealed runtime profile."""

    def __init__(self, profile: Mapping[str, Any]) -> None:
        self.profile = profile
        self.tenant_context = _mapping(profile.get("tenant_context"))
        self.tenant_authority = _mapping(profile.get("tenant_authority"))

    def connect(self, data_source_id: str, *, access_mode: str = "read") -> TenantDataSourceHandle:
        tenant_id = str(self.tenant_context.get("tenant_id", ""))
        if not tenant_id or tenant_id == "global":
            raise TenantDataSourceError("Tenant data sources require a tenant-scoped profile.")

        allowed_role_sources = _string_set(
            self.tenant_context.get("allowed_role_data_sources", [])
        )
        if data_source_id not in allowed_role_sources:
            raise TenantDataSourceError("Data source is not granted by the active tenant role.")

        source = self._data_source(data_source_id)
        if source.get("tenant_id") != tenant_id:
            raise TenantDataSourceError("Data source crosses tenant boundary.")
        if source.get("status") not in {"planned", "active"}:
            raise TenantDataSourceError("Data source is not available.")

        granted_modes = self._granted_access_modes(data_source_id)
        if access_mode not in granted_modes:
            raise TenantDataSourceError("Requested access mode is not granted by the tenant role.")

        return TenantDataSourceHandle(
            data_source_id=data_source_id,
            tenant_id=tenant_id,
            access_mode=access_mode,
            status=str(source["status"]),
        )

    def _data_source(self, data_source_id: str) -> Mapping[str, Any]:
        for source in _mappings(self.tenant_authority.get("data_sources", [])):
            if source.get("id") == data_source_id:
                return source
        raise TenantDataSourceError("Data source is not present in tenant authority.")

    def _granted_access_modes(self, data_source_id: str) -> set[str]:
        role_ids = _string_set(self.tenant_context.get("role_ids", []))
        modes: set[str] = set()
        for role in _mappings(self.tenant_authority.get("role_bundles", [])):
            if role.get("id") not in role_ids:
                continue
            for grant in _mappings(role.get("data_source_grants", [])):
                if grant.get("data_source_id") == data_source_id:
                    modes.update(_string_set(grant.get("access_modes", [])))
        if not modes:
            raise TenantDataSourceError("Data source is not granted by selected roles.")
        return modes


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mappings(values: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(values, list):
        return ()
    return tuple(value for value in values if isinstance(value, Mapping))


def _string_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values if str(value).strip()}
