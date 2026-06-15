from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from skill_centric_agent_system.composition.task_analyzer import AnalyzedTask

GLOBAL_TENANT_ID = "global"
ALLOWED_TENANT_STATUSES = frozenset(("setup", "active"))
ALLOWED_MEMBERSHIP_STATUSES = frozenset(("active",))
BASELINE_INSTRUCTIONS = frozenset(("base-agent-rules", "code-review-rules"))
BASELINE_VALIDATORS = frozenset(("runtime-profile-schema",))


class TenantAccessError(ValueError):
    """Raised when tenant authority cannot produce a safe runtime profile."""


class TenantAccessValidator:
    """Validate role-derived tenant authority before emitting a runtime profile."""

    def validate(
        self,
        analyzed_task: AnalyzedTask,
        context_response: Mapping[str, Any],
        *,
        selected_modules: Mapping[str, Iterable[str]],
    ) -> None:
        tenant_id = analyzed_task.auth_claims.tenant_id
        if tenant_id == GLOBAL_TENANT_ID:
            return

        authority = context_response.get("tenant_authority")
        if not isinstance(authority, Mapping):
            raise TenantAccessError("Tenant authority is required for tenant-scoped profiles.")

        self._validate_tenant_identity(analyzed_task, authority)
        role_ids = self._validate_membership(analyzed_task, authority)
        role_bundles = self._role_bundles(authority, role_ids)

        self._validate_role_grants(analyzed_task, authority, role_bundles)
        self._validate_selected_modules(authority, role_bundles, selected_modules)

    def _validate_tenant_identity(
        self,
        analyzed_task: AnalyzedTask,
        authority: Mapping[str, Any],
    ) -> None:
        expected_tenant_id = analyzed_task.auth_claims.tenant_id
        expected_area_id = analyzed_task.auth_claims.area_id

        if authority.get("tenant_id") != expected_tenant_id:
            raise TenantAccessError("Tenant authority does not match the analyzed tenant.")
        if authority.get("area_id") != expected_area_id:
            raise TenantAccessError("Tenant authority does not match the analyzed area.")
        hostname = authority.get("hostname")
        if not isinstance(hostname, Mapping):
            raise TenantAccessError("Tenant hostname authority is required.")
        if hostname.get("tenant_id") != expected_tenant_id:
            raise TenantAccessError("Tenant hostname authority crosses tenant boundary.")
        expected_hostname = analyzed_task.auth_claims.tenant_hostname
        if expected_hostname is None:
            raise TenantAccessError("Tenant hostname is required for tenant-scoped profiles.")
        if hostname.get("hostname") != expected_hostname:
            raise TenantAccessError("Tenant hostname authority does not match auth claims.")
        if authority.get("status") not in ALLOWED_TENANT_STATUSES:
            raise TenantAccessError("Tenant is not active for runtime composition.")
        if authority.get("direct_user_grants_allowed") is not False:
            raise TenantAccessError("Direct user grants are not allowed for tenant profiles.")

    def _validate_membership(
        self,
        analyzed_task: AnalyzedTask,
        authority: Mapping[str, Any],
    ) -> tuple[str, ...]:
        membership = authority.get("membership")
        if not isinstance(membership, Mapping):
            raise TenantAccessError("Tenant membership is required for tenant-scoped profiles.")

        expected_membership_id = analyzed_task.auth_claims.membership_id
        if expected_membership_id is None:
            raise TenantAccessError("Tenant membership id is required for tenant-scoped profiles.")
        if membership.get("id") != expected_membership_id:
            raise TenantAccessError("Tenant membership does not match the analyzed task.")
        if membership.get("tenant_id") != analyzed_task.auth_claims.tenant_id:
            raise TenantAccessError("Tenant membership crosses tenant boundary.")
        if membership.get("principal_id") != analyzed_task.auth_claims.principal_id:
            raise TenantAccessError("Tenant membership principal does not match auth claims.")
        if membership.get("status") not in ALLOWED_MEMBERSHIP_STATUSES:
            raise TenantAccessError("Tenant membership is not active.")

        membership_roles = _string_set(membership.get("role_ids", []))
        requested_roles = set(analyzed_task.auth_claims.roles)
        missing_roles = sorted(requested_roles - membership_roles)
        if missing_roles:
            raise TenantAccessError(
                "Tenant roles are not granted by the active membership: "
                + ", ".join(missing_roles)
            )
        return tuple(sorted(requested_roles))

    def _role_bundles(
        self,
        authority: Mapping[str, Any],
        role_ids: Sequence[str],
    ) -> tuple[Mapping[str, Any], ...]:
        role_bundles = authority.get("role_bundles", [])
        if not isinstance(role_bundles, list):
            raise TenantAccessError("Tenant role bundles must be a list.")

        by_id = {
            role["id"]: role
            for role in role_bundles
            if isinstance(role, Mapping) and isinstance(role.get("id"), str)
        }
        missing_roles = sorted(set(role_ids) - set(by_id))
        if missing_roles:
            raise TenantAccessError(
                "Tenant roles are not present in tenant authority: " + ", ".join(missing_roles)
            )

        tenant_id = str(authority["tenant_id"])
        selected_roles = tuple(by_id[role_id] for role_id in role_ids)
        for role in selected_roles:
            if role.get("tenant_id") != tenant_id:
                raise TenantAccessError("Tenant role bundle crosses tenant boundary.")
        return selected_roles

    def _validate_role_grants(
        self,
        analyzed_task: AnalyzedTask,
        authority: Mapping[str, Any],
        role_bundles: Sequence[Mapping[str, Any]],
    ) -> None:
        tenant_id = analyzed_task.auth_claims.tenant_id
        data_sources = authority.get("data_sources", [])
        if not isinstance(data_sources, list):
            raise TenantAccessError("Tenant data sources must be a list.")
        data_source_tenant_by_id = {
            source["id"]: source.get("tenant_id")
            for source in data_sources
            if isinstance(source, Mapping) and isinstance(source.get("id"), str)
        }

        granted_capabilities: set[str] = set()
        granted_data_sources: set[str] = set()
        for role in role_bundles:
            granted_capabilities.update(_string_set(role.get("capability_grants", [])))
            for grant in _mappings(role.get("data_source_grants", [])):
                data_source_id = grant.get("data_source_id")
                if not isinstance(data_source_id, str):
                    continue
                if data_source_tenant_by_id.get(data_source_id) != tenant_id:
                    raise TenantAccessError(
                        "Tenant role data-source grant crosses tenant boundary."
                    )
                granted_data_sources.add(data_source_id)

        requested_capabilities = set(analyzed_task.auth_claims.role_capabilities)
        missing_capabilities = sorted(requested_capabilities - granted_capabilities)
        if missing_capabilities:
            raise TenantAccessError(
                "Requested capabilities are not derived from tenant roles: "
                + ", ".join(missing_capabilities)
            )

        requested_data_sources = set(analyzed_task.auth_claims.role_data_sources)
        missing_sources = sorted(requested_data_sources - granted_data_sources)
        if missing_sources:
            raise TenantAccessError(
                "Requested data sources are not derived from tenant roles: "
                + ", ".join(missing_sources)
            )

    def _validate_selected_modules(
        self,
        authority: Mapping[str, Any],
        role_bundles: Sequence[Mapping[str, Any]],
        selected_modules: Mapping[str, Iterable[str]],
    ) -> None:
        allowed_runtime_modules: dict[str, set[str]] = {
            "skills": set(),
            "tools": set(),
            "policies": set(),
            "validators": set(),
        }
        for role in role_bundles:
            derived = role.get("derived_runtime_modules", {})
            if not isinstance(derived, Mapping):
                raise TenantAccessError("Tenant role bundle is missing runtime module derivation.")
            for field in allowed_runtime_modules:
                allowed_runtime_modules[field].update(_string_set(derived.get(field, [])))

        checks = (
            ("skills", allowed_runtime_modules["skills"]),
            ("tools", allowed_runtime_modules["tools"]),
            ("policies", allowed_runtime_modules["policies"]),
            ("validators", allowed_runtime_modules["validators"] | BASELINE_VALIDATORS),
            ("knowledge_scopes", _string_set(authority.get("allowed_knowledge_scopes", []))),
            ("data_scopes", _string_set(authority.get("allowed_data_scopes", []))),
            ("memory_scopes", _string_set(authority.get("allowed_memory_scopes", []))),
        )
        for field, allowed in checks:
            selected = set(selected_modules.get(field, ()))
            denied = sorted(selected - allowed)
            if denied:
                raise TenantAccessError(
                    f"Selected {field} are not allowed by tenant roles: " + ", ".join(denied)
                )

        instruction_denied = sorted(
            set(selected_modules.get("instructions", ())) - BASELINE_INSTRUCTIONS
        )
        if instruction_denied:
            raise TenantAccessError(
                "Selected instructions are not allowed by tenant runtime baseline: "
                + ", ".join(instruction_denied)
            )


def _string_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values if str(value).strip()}


def _mappings(values: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(values, list):
        return ()
    return tuple(value for value in values if isinstance(value, Mapping))
