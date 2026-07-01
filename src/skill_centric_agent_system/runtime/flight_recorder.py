from __future__ import annotations

from collections.abc import Callable
from typing import Any

from skill_centric_agent_system.runtime.artifacts import JsonArtifactStore
from skill_centric_agent_system.runtime.models import (
    RUNTIME_ACTOR_ROLES,
    RUNTIME_EVENT_TYPES,
    RUNTIME_PHASES,
    RUNTIME_STATUSES,
    RUNTIME_STEP_KINDS,
    STOP_REASONS,
    RuntimeActorRole,
    RuntimeEventType,
    RuntimePhase,
    RuntimeStatus,
    RuntimeStepKind,
    StopReason,
    iso_timestamp,
    require_choice,
    slug_id,
    utc_now,
)
from skill_centric_agent_system.runtime.storage_protocol import RuntimeStore


class FlightRecorder:
    """Append-only runtime event writer with artifact-backed payloads."""

    def __init__(
        self,
        store: RuntimeStore,
        artifacts: JsonArtifactStore,
        *,
        clock: Callable[[], Any] = utc_now,
    ) -> None:
        self.store = store
        self.artifacts = artifacts
        self.clock = clock

    def start_run(
        self,
        *,
        task_id: str,
        profile: dict[str, Any] | Any,
        run_id: str | None = None,
        status: RuntimeStatus = "running",
        profile_artifact_uri: str | None = None,
        profile_sha256: str | None = None,
        profile_generation: int | None = None,
        parent_profile_id: str | None = None,
    ) -> dict[str, Any] | Any:
        require_choice(status, RUNTIME_STATUSES, "status")
        run_identifier = run_id or slug_id(task_id.removeprefix("task-"), prefix="run")
        limits = profile.get("limits", {})
        token_budget_total = (
            limits.get("max_tokens") if isinstance(limits, dict) else None
        )
        record = {
            "id": run_identifier,
            "task_id": task_id,
            "profile_id": str(profile["id"]),
            "profile_version": str(profile["profile_version"]),
            "status": status,
            "started_at": iso_timestamp(self.clock()),
            "completed_at": None,
            "artifact_root_uri": self.artifacts.root_uri,
            "token_budget_total": token_budget_total,
            "tokens_used_total": 0,
            "stop_reason": None,
            "profile_artifact_uri": profile_artifact_uri,
            "profile_sha256": profile_sha256,
            "profile_generation": profile_generation,
            "parent_profile_id": parent_profile_id,
        }
        return self.store.insert_runtime_run(record)

    def start_step(
        self,
        *,
        run_id: str,
        step_index: int,
        kind: RuntimeStepKind,
        token_budget: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any] | Any:
        require_choice(kind, RUNTIME_STEP_KINDS, "kind")
        key = idempotency_key or f"{run_id}:step:{step_index}:{kind}"
        record = {
            "id": slug_id(f"{run_id}-{kind}-{step_index}", prefix="step"),
            "run_id": run_id,
            "step_index": step_index,
            "kind": kind,
            "status": "running",
            "started_at": iso_timestamp(self.clock()),
            "completed_at": None,
            "stop_reason": None,
            "token_budget": token_budget,
            "tokens_used": 0,
            "idempotency_key": key,
            "attempt": 1,
        }
        return self.store.insert_runtime_step(record)

    def complete_step(
        self,
        *,
        step_id: str,
        status: RuntimeStatus,
        stop_reason: StopReason | None,
        tokens_used: int = 0,
    ) -> dict[str, Any] | Any:
        require_choice(status, RUNTIME_STATUSES, "status")
        if stop_reason is not None:
            require_choice(stop_reason, STOP_REASONS, "stop_reason")
        return self.store.update_runtime_step(
            step_id,
            {
                "status": status,
                "completed_at": iso_timestamp(self.clock()),
                "stop_reason": stop_reason,
                "tokens_used": tokens_used,
            },
        )

    def record_event(
        self,
        *,
        run_id: str,
        event_type: RuntimeEventType,
        actor_role: RuntimeActorRole,
        step_id: str | None = None,
        planned_action: Any = None,
        execution: Any = None,
        result: Any = None,
        stop_reason: StopReason | None = None,
        idempotency_key: str | None = None,
        redact_sensitive_data: bool = True,
    ) -> dict[str, Any] | Any:
        require_choice(event_type, RUNTIME_EVENT_TYPES, "event_type")
        require_choice(actor_role, RUNTIME_ACTOR_ROLES, "actor_role")
        if stop_reason is not None:
            require_choice(stop_reason, STOP_REASONS, "stop_reason")

        event_index = self.store.allocate_runtime_event_index(run_id)
        key = idempotency_key or f"{run_id}:event:{event_type}:{event_index}"
        existing = self.store.insert_runtime_event(
            self._event_record(
                run_id=run_id,
                step_id=step_id,
                event_index=event_index,
                event_type=event_type,
                actor_role=actor_role,
                planned_action_uri=self._write_event_payload(
                    run_id,
                    event_index,
                    event_type,
                    "planned",
                    planned_action,
                    redact_sensitive_data,
                ),
                execution_uri=self._write_event_payload(
                    run_id,
                    event_index,
                    event_type,
                    "execution",
                    execution,
                    redact_sensitive_data,
                ),
                result_uri=self._write_event_payload(
                    run_id,
                    event_index,
                    event_type,
                    "result",
                    result,
                    redact_sensitive_data,
                ),
                stop_reason=stop_reason,
                idempotency_key=key,
            )
        )
        return existing

    def checkpoint(
        self,
        *,
        run_id: str,
        phase: RuntimePhase,
        state: Any,
        step_id: str | None = None,
        tokens_used_total: int = 0,
        redact_sensitive_data: bool = True,
    ) -> dict[str, Any] | Any:
        require_choice(phase, RUNTIME_PHASES, "phase")
        checkpoint_index = self.store.allocate_runtime_checkpoint_index(run_id)
        state_uri = self.artifacts.write_json(
            ("traces", run_id, "checkpoints", f"{checkpoint_index:03d}-{phase}"),
            state,
            redact=redact_sensitive_data,
        )
        record = {
            "id": slug_id(f"{run_id}-{phase}-{checkpoint_index}", prefix="checkpoint"),
            "run_id": run_id,
            "step_id": step_id,
            "checkpoint_index": checkpoint_index,
            "phase": phase,
            "state_uri": state_uri,
            "tokens_used_total": tokens_used_total,
            "created_at": iso_timestamp(self.clock()),
        }
        stored = self.store.insert_runtime_checkpoint(record)
        self.record_event(
            run_id=run_id,
            step_id=step_id,
            event_type="checkpoint_created",
            actor_role="composer" if phase in {"analysis", "composition"} else "executor",
            result={"checkpoint_id": stored["id"], "phase": phase},
            idempotency_key=f"{run_id}:checkpoint:{checkpoint_index}",
            redact_sensitive_data=redact_sensitive_data,
        )
        return stored

    def complete_run(
        self,
        *,
        run_id: str,
        status: RuntimeStatus,
        stop_reason: StopReason,
        tokens_used_total: int = 0,
    ) -> dict[str, Any] | Any:
        require_choice(status, RUNTIME_STATUSES, "status")
        require_choice(stop_reason, STOP_REASONS, "stop_reason")
        return self.store.update_runtime_run(
            run_id,
            {
                "status": status,
                "completed_at": iso_timestamp(self.clock()),
                "tokens_used_total": tokens_used_total,
                "stop_reason": stop_reason,
            },
        )

    def _event_record(
        self,
        *,
        run_id: str,
        step_id: str | None,
        event_index: int,
        event_type: RuntimeEventType,
        actor_role: RuntimeActorRole,
        planned_action_uri: str | None,
        execution_uri: str | None,
        result_uri: str | None,
        stop_reason: StopReason | None,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return {
            "id": slug_id(f"{run_id}-{event_type}-{event_index}", prefix="event"),
            "run_id": run_id,
            "step_id": step_id,
            "event_index": event_index,
            "event_type": event_type,
            "actor_role": actor_role,
            "planned_action_uri": planned_action_uri,
            "execution_uri": execution_uri,
            "result_uri": result_uri,
            "stop_reason": stop_reason,
            "idempotency_key": idempotency_key,
            "created_at": iso_timestamp(self.clock()),
        }

    def _write_event_payload(
        self,
        run_id: str,
        event_index: int,
        event_type: str,
        slot: str,
        payload: Any,
        redact_sensitive_data: bool,
    ) -> str | None:
        if payload is None:
            return None
        return self.artifacts.write_json(
            ("traces", run_id, "events", f"{event_index:03d}-{event_type}-{slot}"),
            payload,
            redact=redact_sensitive_data,
        )

