from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

NON_AUTHORITATIVE_MEMORY_EFFECTS = frozenset(
    {
        "planner_hint",
        "retrieval_ranking",
        "composer_candidate_bias",
    }
)
AUTHORITY_PLAN_FIELDS = {
    "tool_grants": "tool grants",
    "granted_tools": "tool grants",
    "added_tools": "tool grants",
    "scope_grants": "scope grants",
    "knowledge_scope_grants": "scope grants",
    "memory_scope_grants": "scope grants",
    "data_scope_grants": "scope grants",
    "policy_overrides": "policy overrides",
    "validator_overrides": "validator overrides",
    "budget_changes": "budget changes",
    "failure_policy_changes": "failure policy changes",
    "runtime_profile_patch": "runtime profile mutation",
}
PROFILE_AUTHORITY_FIELDS = (
    "tools",
    "knowledge_scopes",
    "memory_scopes",
    "data_scopes",
    "policies",
    "validators",
    "limits",
    "failure_policy",
)


@dataclass(frozen=True)
class PostPlanningMemoryInvariantResult:
    status: str
    reason: str
    violations: tuple[str, ...]

    @property
    def approved(self) -> bool:
        return self.status == "approved"


class PostPlanningMemoryInvariantValidator:
    """Validate that memory-influenced plans do not gain runtime authority."""

    def validate(
        self,
        plan: Mapping[str, Any],
        *,
        runtime_profile: Mapping[str, Any],
        planned_runtime_profile: Mapping[str, Any] | None = None,
    ) -> PostPlanningMemoryInvariantResult:
        used_memory_ids = _string_tuple(plan.get("used_memory_ids"))
        if not used_memory_ids:
            return PostPlanningMemoryInvariantResult(
                status="approved",
                reason="Plan does not use procedural memory.",
                violations=(),
            )

        violations: list[str] = []
        violations.extend(_memory_effect_violations(plan))
        violations.extend(_authority_field_violations(plan))
        violations.extend(_memory_authority_justification_violations(plan))
        if planned_runtime_profile is not None:
            violations.extend(
                _runtime_profile_delta_violations(
                    runtime_profile=runtime_profile,
                    planned_runtime_profile=planned_runtime_profile,
                )
            )

        if violations:
            return PostPlanningMemoryInvariantResult(
                status="rejected",
                reason="Memory-influenced plan violates non-authority invariants.",
                violations=tuple(violations),
            )
        return PostPlanningMemoryInvariantResult(
            status="approved",
            reason="Memory-influenced plan preserves runtime authority boundaries.",
            violations=(),
        )


def _memory_effect_violations(plan: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    effect = plan.get("effect")
    effects = _string_tuple(effect) if isinstance(effect, list) else (str(effect),)
    if not effects or any(item not in NON_AUTHORITATIVE_MEMORY_EFFECTS for item in effects):
        violations.append("memory effect must be non-authoritative")
    if not str(plan.get("selection_reason", "")).strip():
        violations.append("memory-influenced plans require selection_reason")
    authority_delta = _string_tuple(plan.get("authority_delta"))
    if authority_delta:
        violations.append("memory-influenced plans must not carry authority_delta")
    return violations


def _authority_field_violations(plan: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    for field, label in AUTHORITY_PLAN_FIELDS.items():
        value = plan.get(field)
        if _has_value(value):
            violations.append(f"memory-influenced plans must not include {label}")
    return violations


def _memory_authority_justification_violations(plan: Mapping[str, Any]) -> list[str]:
    authority_source = str(plan.get("authority_source", "")).lower()
    if authority_source in {"memory", "procedural_memory", "agent_memory"}:
        return ["memory IDs must not be used as authority justification"]

    authority_justification = plan.get("authority_justification")
    if isinstance(authority_justification, Mapping) and _has_value(
        authority_justification.get("memory_ids")
    ):
        return ["memory IDs must not be used as authority justification"]
    return []


def _runtime_profile_delta_violations(
    *,
    runtime_profile: Mapping[str, Any],
    planned_runtime_profile: Mapping[str, Any],
) -> list[str]:
    violations: list[str] = []
    for field in PROFILE_AUTHORITY_FIELDS:
        if runtime_profile.get(field) != planned_runtime_profile.get(field):
            violations.append(
                "memory-influenced plans must not mutate runtime_profile "
                f"{field}"
            )
    return violations


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item.strip())


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Sequence):
        return bool(value)
    if isinstance(value, Mapping):
        return bool(value)
    return True
