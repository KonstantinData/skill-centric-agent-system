from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from skill_centric_agent_system.runtime.models import StopReason, selected_modules


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

    def record_tool_invocation(
        self,
        tool_name: str,
        *,
        required_data_scopes: Iterable[str] = (),
        tool_risk_level: str = "low",
    ) -> None:
        self.check_duration()
        self.require_tool(tool_name)
        self.require_tool_risk(tool_name, tool_risk_level)
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
