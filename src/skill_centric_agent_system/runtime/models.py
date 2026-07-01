from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

RuntimeStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
RuntimeQueueStatus = Literal[
    "queued",
    "claiming",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    "retry_scheduled",
    "dead_lettered",
]
RuntimeStepKind = Literal["context", "planner", "executor", "validator"]
StopReason = Literal[
    "completed",
    "max_tokens",
    "max_duration",
    "max_tool_calls",
    "max_data_reads",
    "max_memory_ops",
    "max_recompositions",
    "policy_denied",
    "validator_failed",
    "tool_error",
    "cancelled",
    "needs_recomposition",
    "composer_failure",
    "runtime_error",
]
RuntimeEventType = Literal[
    "task_intake_normalized",
    "task_analyzed",
    "candidates_discovered",
    "candidates_scored",
    "policies_evaluated",
    "graph_validated",
    "profile_emitted",
    "profile_validated",
    "runtime_started",
    "access_attempted",
    "validator_executed",
    "runtime_completed",
    "runtime_failed",
    "runtime_cancelled",
    "tenant_throttled",
    "quota_reserved",
    "quota_exhausted",
    "step_started",
    "step_completed",
    "tool_invocation_started",
    "tool_invocation_completed",
    "runtime_after_tool_hook_evaluated",
    "budget_exhausted",
    "checkpoint_created",
    "recomposition_requested",
]
RuntimeActorRole = Literal[
    "context_manager",
    "planner",
    "executor",
    "validator",
    "policy_engine",
    "quota_manager",
    "runtime",
    "composer",
]
RuntimePhase = Literal[
    "task_intake",
    "analysis",
    "composition",
    "context",
    "planner",
    "executor",
    "validator",
    "finalization",
]
RecompositionReason = Literal[
    "task_reclassified",
    "missing_capability",
    "policy_change",
    "budget_exhausted",
    "validator_failure",
]

RUNTIME_STATUSES = frozenset(RuntimeStatus.__args__)  # type: ignore[attr-defined]
RUNTIME_QUEUE_STATUSES = frozenset(RuntimeQueueStatus.__args__)  # type: ignore[attr-defined]
RUNTIME_STEP_KINDS = frozenset(RuntimeStepKind.__args__)  # type: ignore[attr-defined]
STOP_REASONS = frozenset(StopReason.__args__)  # type: ignore[attr-defined]
RUNTIME_EVENT_TYPES = frozenset(RuntimeEventType.__args__)  # type: ignore[attr-defined]
RUNTIME_ACTOR_ROLES = frozenset(RuntimeActorRole.__args__)  # type: ignore[attr-defined]
RUNTIME_PHASES = frozenset(RuntimePhase.__args__)  # type: ignore[attr-defined]
RECOMPOSITION_REASONS = frozenset(RecompositionReason.__args__)  # type: ignore[attr-defined]


@dataclass(frozen=True)
class RecompositionRequest:
    source_run_id: str
    task_id: str
    parent_profile_id: str
    requested_profile_generation: int
    recomposition_reason: RecompositionReason

    def as_event_result(self) -> dict[str, Any]:
        return {
            "source_run_id": self.source_run_id,
            "task_id": self.task_id,
            "parent_profile_id": self.parent_profile_id,
            "requested_profile_generation": self.requested_profile_generation,
            "recomposition_reason": self.recomposition_reason,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> RecompositionRequest:
        reason = str(value["recomposition_reason"])
        require_choice(reason, RECOMPOSITION_REASONS, "recomposition_reason")
        return cls(
            source_run_id=str(value["source_run_id"]),
            task_id=str(value["task_id"]),
            parent_profile_id=str(value["parent_profile_id"]),
            requested_profile_generation=int(value["requested_profile_generation"]),
            recomposition_reason=reason,  # type: ignore[arg-type]
        )


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_timestamp(value: datetime | None = None) -> str:
    timestamp = value or utc_now()
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")


def slug_id(value: str, *, prefix: str | None = None, max_length: int = 96) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    if not slug:
        slug = "item"
    if not slug[0].isalpha():
        slug = "id-" + slug
    if prefix and not slug.startswith(prefix + "-"):
        slug = f"{prefix}-{slug}"
    return slug[:max_length].strip("-")


def require_choice(value: str, allowed: frozenset[str], field: str) -> None:
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValueError(f"{field} must be one of: {choices}. Got: {value}.")


def selected_modules(profile: Mapping[str, Any]) -> list[str]:
    selected: list[str] = []
    for field in (
        "instructions",
        "skills",
        "tools",
        "knowledge_scopes",
        "data_scopes",
        "memory_scopes",
        "policies",
        "validators",
    ):
        values = profile.get(field, [])
        if isinstance(values, list):
            selected.extend(str(value) for value in values)
    return selected
