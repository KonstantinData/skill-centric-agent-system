from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from skill_centric_agent_system.composition.tenant_access import ALLOWED_TENANT_STATUSES


class RuntimeTenantStatusError(RuntimeError):
    """Raised when server-authoritative tenant state blocks runtime execution."""


def assert_runtime_tenant_is_startable(
    task: Mapping[str, Any],
    composition_context_response: Mapping[str, Any],
) -> None:
    auth = task.get("context", {})
    auth = auth.get("auth", {}) if isinstance(auth, Mapping) else {}
    tenant_id = auth.get("tenant_id") if isinstance(auth, Mapping) else None
    area_id = auth.get("area_id") if isinstance(auth, Mapping) else None
    if tenant_id in {None, "global"}:
        return

    authority = composition_context_response.get("tenant_authority")
    if not isinstance(authority, Mapping):
        if composition_context_response.get("composition_status") == "denied":
            return
        raise RuntimeTenantStatusError("Tenant authority is required for runtime execution.")
    if authority.get("tenant_id") != tenant_id:
        raise RuntimeTenantStatusError(
            "Tenant authority does not match the runtime task tenant."
        )
    if authority.get("area_id") != area_id:
        raise RuntimeTenantStatusError(
            "Tenant authority does not match the runtime task area."
        )
    if authority.get("status") not in ALLOWED_TENANT_STATUSES:
        raise RuntimeTenantStatusError("Tenant is not active for runtime execution.")
