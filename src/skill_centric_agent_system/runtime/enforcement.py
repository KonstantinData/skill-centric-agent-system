from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from skill_centric_agent_system.runtime.models import StopReason, selected_modules

GLOBAL_TENANT_ID = "global"
ALLOWED_TENANT_STATUSES = frozenset(("setup", "active"))
ALLOWED_MEMBERSHIP_STATUSES = frozenset(("active",))
BASELINE_TENANT_INSTRUCTIONS = frozenset(("base-agent-rules", "code-review-rules"))
BASELINE_TENANT_VALIDATORS = frozenset(("runtime-profile-schema",))


class ProfileEnforcementError(RuntimeError):
    """Raised when runtime execution would exceed the active profile."""

    def __init__(
        self,
        message: str,
        *,
        stop_reason: StopReason = "policy_denied",
        code: str = "profile_enforcement_denied",
    ) -> None:
        super().__init__(message)
        self.stop_reason = stop_reason
        self.code = code


class RuntimeProfileEnforcer:
    """Hard limits and access checks for a single immutable Runtime Agent Profile."""

    def __init__(
        self,
        profile: Mapping[str, Any],
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.profile = profile
        self.clock = clock
        self.started_at = clock()
        self.tool_calls = 0
        self.tokens_used = 0
        self.data_reads = 0
        self.memory_ops = 0
        self.recomposition_requests = max(0, int(profile.get("profile_generation", 1)) - 1)

    def validate_profile_for_runtime(self) -> None:
        missing_versions = [
            module_id
            for module_id in selected_modules(self.profile)
            if module_id not in self.profile.get("module_versions", {})
        ]
        if missing_versions:
            modules = ", ".join(sorted(missing_versions))
            raise ProfileEnforcementError(
                f"Selected modules are not version-pinned: {modules}.",
                stop_reason="policy_denied",
                code="selected_module_version_missing",
            )

        profile_generation = int(self.profile.get("profile_generation", 1))
        recompositions_used = max(0, profile_generation - 1)
        max_recompositions = self._limit("max_recompositions")
        if recompositions_used > max_recompositions:
            raise ProfileEnforcementError(
                "Profile generation exceeds the recomposition budget.",
                stop_reason="max_recompositions",
                code="max_recompositions_exceeded",
            )
        self._validate_tenant_authority()

    def record_tool_invocation(
        self,
        tool_name: str,
        *,
        required_data_scopes: Iterable[str] = (),
        required_policies: Iterable[str] = (),
        tool_risk_level: str = "low",
    ) -> None:
        self.check_duration()
        self.require_tool(tool_name)
        self.require_tool_risk(tool_name, tool_risk_level)
        for policy_id in required_policies:
            self.require_policy(policy_id)
        self._increment_limit("tool_calls", "max_tool_calls", 1)

        required_scopes = tuple(required_data_scopes)
        if required_scopes:
            self.require_data_scopes(required_scopes)
            self.record_data_read()

    def consume_tokens(self, tokens: int) -> None:
        if tokens < 0:
            raise ValueError("tokens must be non-negative.")
        self.check_duration()
        self._increment_limit("tokens_used", "max_tokens", tokens)

    def record_data_read(self, count: int = 1) -> None:
        self._increment_limit("data_reads", "max_data_reads", count)

    def record_memory_op(self, count: int = 1) -> None:
        self._increment_limit("memory_ops", "max_memory_ops", count)

    def record_recomposition_request(self) -> None:
        self._increment_limit(
            "recomposition_requests",
            "max_recompositions",
            1,
            stop_reason="max_recompositions",
        )

    def require_tool(self, tool_name: str) -> None:
        if tool_name not in self.profile.get("tools", []):
            raise ProfileEnforcementError(
                f"Tool is not allowed by runtime profile: {tool_name}",
                stop_reason="policy_denied",
                code="tool_not_in_runtime_profile",
            )

    def require_skill(self, skill_name: str) -> None:
        if skill_name not in self.profile.get("skills", []):
            raise ProfileEnforcementError(
                f"Skill is not allowed by runtime profile: {skill_name}",
                stop_reason="policy_denied",
                code="skill_not_in_runtime_profile",
            )

    def require_policy(self, policy_id: str) -> None:
        if policy_id not in self.profile.get("policies", []):
            raise ProfileEnforcementError(
                f"Policy is not allowed by runtime profile: {policy_id}",
                stop_reason="policy_denied",
                code="policy_not_in_runtime_profile",
            )

    def require_module_version(self, module_name: str, expected_version: str) -> None:
        module_versions = self.profile.get("module_versions", {})
        actual_version = (
            module_versions.get(module_name) if isinstance(module_versions, Mapping) else None
        )
        if actual_version != expected_version:
            raise ProfileEnforcementError(
                (
                    f"Module version mismatch for {module_name}: "
                    f"expected {expected_version}, got {actual_version}."
                ),
                stop_reason="policy_denied",
                code="module_version_mismatch",
            )

    def require_tool_risk(self, tool_name: str, tool_risk_level: str) -> None:
        profile_risk_level = str(self.profile.get("risk_level", "low"))
        if _risk_rank(tool_risk_level) > _risk_rank(profile_risk_level):
            raise ProfileEnforcementError(
                f"Tool risk exceeds profile risk level: {tool_name}.",
                stop_reason="policy_denied",
                code="tool_risk_exceeds_profile",
            )

    def require_knowledge_scopes(self, scope_ids: Iterable[str]) -> None:
        self._require_scopes(
            requested=scope_ids,
            allowed=self.profile.get("knowledge_scopes", []),
            scope_kind="knowledge",
        )

    def require_data_scopes(self, scope_ids: Iterable[str]) -> None:
        self._require_scopes(
            requested=scope_ids,
            allowed=self.profile.get("data_scopes", []),
            scope_kind="data",
        )

    def require_memory_scopes(self, scope_ids: Iterable[str]) -> None:
        self._require_scopes(
            requested=scope_ids,
            allowed=self.profile.get("memory_scopes", []),
            scope_kind="memory",
        )

    def check_duration(self) -> None:
        max_duration = self._limit("max_duration_seconds")
        if self.clock() - self.started_at > max_duration:
            raise ProfileEnforcementError(
                "Runtime duration exceeded the active profile budget.",
                stop_reason="max_duration",
                code="max_duration_exceeded",
            )

    def _increment_limit(
        self,
        counter_name: str,
        limit_name: str,
        amount: int,
        *,
        stop_reason: StopReason | None = None,
    ) -> None:
        if amount < 0:
            raise ValueError(f"{counter_name} increment must be non-negative.")
        current = int(getattr(self, counter_name))
        next_value = current + amount
        limit = self._limit(limit_name)
        if next_value > limit:
            reason = stop_reason or _limit_stop_reason(limit_name)
            raise ProfileEnforcementError(
                f"Runtime profile limit exceeded: {limit_name}.",
                stop_reason=reason,
                code=f"{limit_name}_exceeded",
            )
        setattr(self, counter_name, next_value)

    def _limit(self, limit_name: str) -> int:
        limits = self.profile.get("limits", {})
        raw_limit = limits.get(limit_name, 0) if isinstance(limits, Mapping) else 0
        return int(raw_limit)

    def _require_scopes(
        self,
        *,
        requested: Iterable[str],
        allowed: Iterable[str],
        scope_kind: str,
    ) -> None:
        allowed_set = {str(scope_id) for scope_id in allowed}
        denied = sorted({str(scope_id) for scope_id in requested} - allowed_set)
        if denied:
            scopes = ", ".join(denied)
            raise ProfileEnforcementError(
                f"Requested {scope_kind} scopes are not allowed: {scopes}.",
                stop_reason="policy_denied",
                code=f"{scope_kind}_scope_not_in_runtime_profile",
            )

    def _validate_tenant_authority(self) -> None:
        tenant_context = self.profile.get("tenant_context")
        if not isinstance(tenant_context, Mapping):
            raise ProfileEnforcementError(
                "Runtime profile is missing tenant_context.",
                code="tenant_context_missing",
            )

        tenant_id = str(tenant_context.get("tenant_id", ""))
        if tenant_id == GLOBAL_TENANT_ID:
            if self.profile.get("tenant_authority") is not None:
                raise ProfileEnforcementError(
                    "Global runtime profiles must not include tenant authority.",
                    code="global_tenant_authority_present",
                )
            return

        authority = self.profile.get("tenant_authority")
        if not isinstance(authority, Mapping):
            raise ProfileEnforcementError(
                "Tenant-scoped runtime profiles require tenant authority.",
                code="tenant_authority_missing",
            )

        self._validate_tenant_identity(tenant_context, authority)
        role_ids = self._validate_tenant_membership(tenant_context, authority)
        role_bundles = self._tenant_role_bundles(authority, role_ids)
        self._validate_tenant_role_grants(tenant_context, authority, role_bundles)
        self._validate_tenant_selected_modules(authority, role_bundles)

    def _validate_tenant_identity(
        self,
        tenant_context: Mapping[str, Any],
        authority: Mapping[str, Any],
    ) -> None:
        if authority.get("tenant_id") != tenant_context.get("tenant_id"):
            raise ProfileEnforcementError(
                "Tenant authority does not match runtime profile tenant.",
                code="tenant_authority_tenant_mismatch",
            )
        if authority.get("area_id") != tenant_context.get("area_id"):
            raise ProfileEnforcementError(
                "Tenant authority does not match runtime profile area.",
                code="tenant_authority_area_mismatch",
            )
        hostname = authority.get("hostname")
        if not isinstance(hostname, Mapping):
            raise ProfileEnforcementError(
                "Tenant authority is missing hostname proof.",
                code="tenant_hostname_authority_missing",
            )
        if hostname.get("tenant_id") != tenant_context.get("tenant_id"):
            raise ProfileEnforcementError(
                "Tenant hostname authority crosses tenant boundary.",
                code="tenant_hostname_authority_tenant_mismatch",
            )
        if hostname.get("hostname") != tenant_context.get("hostname"):
            raise ProfileEnforcementError(
                "Tenant hostname authority does not match runtime profile host.",
                code="tenant_hostname_authority_mismatch",
            )
        if authority.get("status") not in ALLOWED_TENANT_STATUSES:
            raise ProfileEnforcementError(
                "Tenant is not active for runtime execution.",
                code="tenant_not_active",
            )
        role_derivation = tenant_context.get("role_derivation")
        if not isinstance(role_derivation, Mapping):
            raise ProfileEnforcementError(
                "Tenant role derivation is missing from runtime profile.",
                code="tenant_role_derivation_missing",
            )
        if role_derivation.get("direct_user_grants_allowed") is not False:
            raise ProfileEnforcementError(
                "Direct user grants are not allowed for tenant runtime profiles.",
                code="tenant_direct_user_grants_enabled",
            )
        if role_derivation.get("capabilities_derive_from_roles") is not True:
            raise ProfileEnforcementError(
                "Tenant runtime capabilities must derive from roles.",
                code="tenant_capability_derivation_invalid",
            )
        if role_derivation.get("data_sources_derive_from_roles") is not True:
            raise ProfileEnforcementError(
                "Tenant runtime data sources must derive from roles.",
                code="tenant_data_source_derivation_invalid",
            )
        if authority.get("direct_user_grants_allowed") is not False:
            raise ProfileEnforcementError(
                "Tenant authority cannot permit direct user grants.",
                code="tenant_authority_direct_user_grants_enabled",
            )

    def _validate_tenant_membership(
        self,
        tenant_context: Mapping[str, Any],
        authority: Mapping[str, Any],
    ) -> tuple[str, ...]:
        membership = authority.get("membership")
        if not isinstance(membership, Mapping):
            raise ProfileEnforcementError(
                "Tenant authority is missing membership proof.",
                code="tenant_membership_missing",
            )

        if membership.get("id") != tenant_context.get("membership_id"):
            raise ProfileEnforcementError(
                "Tenant authority membership does not match runtime profile.",
                code="tenant_membership_mismatch",
            )
        if membership.get("tenant_id") != tenant_context.get("tenant_id"):
            raise ProfileEnforcementError(
                "Tenant membership crosses tenant boundary.",
                code="tenant_membership_crosses_tenant",
            )

        auth_context = self.profile.get("auth_context", {})
        principal = auth_context.get("principal", {}) if isinstance(auth_context, Mapping) else {}
        principal_id = principal.get("id") if isinstance(principal, Mapping) else None
        if membership.get("principal_id") != principal_id:
            raise ProfileEnforcementError(
                "Tenant membership principal does not match runtime profile.",
                code="tenant_membership_principal_mismatch",
            )
        if membership.get("status") not in ALLOWED_MEMBERSHIP_STATUSES:
            raise ProfileEnforcementError(
                "Tenant membership is not active.",
                code="tenant_membership_not_active",
            )

        membership_roles = _string_set(membership.get("role_ids", []))
        profile_roles = _string_set(tenant_context.get("role_ids", []))
        missing_roles = sorted(profile_roles - membership_roles)
        if missing_roles:
            raise ProfileEnforcementError(
                "Tenant runtime profile selected roles outside membership: "
                + ", ".join(missing_roles),
                code="tenant_role_not_in_membership",
            )
        return tuple(sorted(profile_roles))

    def _tenant_role_bundles(
        self,
        authority: Mapping[str, Any],
        role_ids: Iterable[str],
    ) -> tuple[Mapping[str, Any], ...]:
        role_bundles = authority.get("role_bundles", [])
        if not isinstance(role_bundles, list):
            raise ProfileEnforcementError(
                "Tenant authority role bundles must be a list.",
                code="tenant_role_bundles_invalid",
            )

        by_id = {
            role["id"]: role
            for role in role_bundles
            if isinstance(role, Mapping) and isinstance(role.get("id"), str)
        }
        missing_roles = sorted(set(role_ids) - set(by_id))
        if missing_roles:
            raise ProfileEnforcementError(
                "Tenant runtime profile selected unknown roles: " + ", ".join(missing_roles),
                code="tenant_role_bundle_missing",
            )

        tenant_id = str(authority.get("tenant_id", ""))
        selected_roles = tuple(by_id[role_id] for role_id in role_ids)
        for role in selected_roles:
            if role.get("tenant_id") != tenant_id:
                raise ProfileEnforcementError(
                    "Tenant role bundle crosses tenant boundary.",
                    code="tenant_role_bundle_crosses_tenant",
                )
        return selected_roles

    def _validate_tenant_role_grants(
        self,
        tenant_context: Mapping[str, Any],
        authority: Mapping[str, Any],
        role_bundles: Iterable[Mapping[str, Any]],
    ) -> None:
        data_sources = authority.get("data_sources", [])
        if not isinstance(data_sources, list):
            raise ProfileEnforcementError(
                "Tenant authority data sources must be a list.",
                code="tenant_data_sources_invalid",
            )

        tenant_id = str(tenant_context.get("tenant_id", ""))
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
                    raise ProfileEnforcementError(
                        "Tenant data-source grant is missing a data source id.",
                        code="tenant_data_source_grant_invalid",
                    )
                if data_source_tenant_by_id.get(data_source_id) != tenant_id:
                    raise ProfileEnforcementError(
                        "Tenant data-source grant crosses tenant boundary.",
                        code="tenant_data_source_grant_crosses_tenant",
                    )
                granted_data_sources.add(data_source_id)

        requested_capabilities = _string_set(
            tenant_context.get("allowed_role_capabilities", [])
        )
        missing_capabilities = sorted(requested_capabilities - granted_capabilities)
        if missing_capabilities:
            raise ProfileEnforcementError(
                "Tenant runtime capabilities are not role-derived: "
                + ", ".join(missing_capabilities),
                code="tenant_capability_not_role_derived",
            )

        requested_data_sources = _string_set(
            tenant_context.get("allowed_role_data_sources", [])
        )
        missing_data_sources = sorted(requested_data_sources - granted_data_sources)
        if missing_data_sources:
            raise ProfileEnforcementError(
                "Tenant runtime data sources are not role-derived: "
                + ", ".join(missing_data_sources),
                code="tenant_data_source_not_role_derived",
            )

    def _validate_tenant_selected_modules(
        self,
        authority: Mapping[str, Any],
        role_bundles: Iterable[Mapping[str, Any]],
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
                raise ProfileEnforcementError(
                    "Tenant role bundle is missing runtime module derivation.",
                    code="tenant_runtime_derivation_missing",
                )
            for field in allowed_runtime_modules:
                allowed_runtime_modules[field].update(_string_set(derived.get(field, [])))

        checks = (
            ("skills", allowed_runtime_modules["skills"], "tenant_skill_denied"),
            ("tools", allowed_runtime_modules["tools"], "tenant_tool_denied"),
            ("policies", allowed_runtime_modules["policies"], "tenant_policy_denied"),
            (
                "validators",
                allowed_runtime_modules["validators"] | BASELINE_TENANT_VALIDATORS,
                "tenant_validator_denied",
            ),
            (
                "knowledge_scopes",
                _string_set(authority.get("allowed_knowledge_scopes", [])),
                "tenant_knowledge_scope_denied",
            ),
            (
                "data_scopes",
                _string_set(authority.get("allowed_data_scopes", [])),
                "tenant_data_scope_denied",
            ),
            (
                "memory_scopes",
                _string_set(authority.get("allowed_memory_scopes", [])),
                "tenant_memory_scope_denied",
            ),
        )
        for field, allowed, code in checks:
            selected = _string_set(self.profile.get(field, []))
            denied = sorted(selected - allowed)
            if denied:
                raise ProfileEnforcementError(
                    f"Tenant runtime profile selected unauthorized {field}: "
                    + ", ".join(denied),
                    code=code,
                )

        selected_instructions = _string_set(self.profile.get("instructions", []))
        denied_instructions = sorted(selected_instructions - BASELINE_TENANT_INSTRUCTIONS)
        if denied_instructions:
            raise ProfileEnforcementError(
                "Tenant runtime profile selected unauthorized instructions: "
                + ", ".join(denied_instructions),
                code="tenant_instruction_denied",
            )


def _limit_stop_reason(limit_name: str) -> StopReason:
    mapping: dict[str, StopReason] = {
        "max_tool_calls": "max_tool_calls",
        "max_tokens": "max_tokens",
        "max_data_reads": "max_data_reads",
        "max_memory_ops": "max_memory_ops",
        "max_recompositions": "max_recompositions",
    }
    return mapping.get(limit_name, "runtime_error")


def _risk_rank(risk_level: str) -> int:
    order = {
        "low": 0,
        "medium": 1,
        "high": 2,
        "critical": 3,
    }
    return order.get(risk_level, 3)


def _string_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values if str(value).strip()}


def _mappings(values: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(values, list):
        return ()
    return tuple(value for value in values if isinstance(value, Mapping))
