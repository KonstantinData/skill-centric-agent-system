from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal

RuntimeStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
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
    "step_started",
    "step_completed",
    "tool_invocation_started",
    "tool_invocation_completed",
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

RUNTIME_STATUSES = frozenset(RuntimeStatus.__args__)  # type: ignore[attr-defined]
RUNTIME_STEP_KINDS = frozenset(RuntimeStepKind.__args__)  # type: ignore[attr-defined]
STOP_REASONS = frozenset(StopReason.__args__)  # type: ignore[attr-defined]
RUNTIME_EVENT_TYPES = frozenset(RuntimeEventType.__args__)  # type: ignore[attr-defined]
RUNTIME_ACTOR_ROLES = frozenset(RuntimeActorRole.__args__)  # type: ignore[attr-defined]
RUNTIME_PHASES = frozenset(RuntimePhase.__args__)  # type: ignore[attr-defined]


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
