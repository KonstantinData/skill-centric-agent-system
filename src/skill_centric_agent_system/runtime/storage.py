from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping
from typing import Any, Protocol

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
    selected_modules,
    slug_id,
    utc_now,
)


class RuntimeStore(Protocol):
    def insert_runtime_run(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def update_runtime_run(self, run_id: str, fields: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def insert_runtime_step(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def update_runtime_step(self, step_id: str, fields: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def insert_runtime_event(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def insert_runtime_checkpoint(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def events_for_run(self, run_id: str) -> tuple[Mapping[str, Any], ...]: ...

    def checkpoints_for_run(self, run_id: str) -> tuple[Mapping[str, Any], ...]: ...


class InMemoryRuntimeStore:
    """Runtime store used by tests and local entrypoint dry-runs."""

    def __init__(self) -> None:
        self.runtime_runs: dict[str, dict[str, Any]] = {}
        self.runtime_steps: dict[str, dict[str, Any]] = {}
        self.runtime_events: list[dict[str, Any]] = []
        self.runtime_checkpoints: list[dict[str, Any]] = []
        self.tool_invocations: list[dict[str, Any]] = []
        self.validation_results: list[dict[str, Any]] = []
        self.memory_candidates: list[dict[str, Any]] = []

    def insert_runtime_run(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = dict(record)
        self.runtime_runs[stored["id"]] = stored
        return stored

    def update_runtime_run(self, run_id: str, fields: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = self.runtime_runs[run_id]
        stored.update(fields)
        return stored

    def insert_runtime_step(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        idempotency_key = record.get("idempotency_key")
        if idempotency_key is not None:
            existing = self._find_by_run_idempotency(
                self.runtime_steps.values(),
                str(record["run_id"]),
                str(idempotency_key),
            )
            if existing is not None:
                return existing

        stored = dict(record)
        self.runtime_steps[stored["id"]] = stored
        return stored

    def update_runtime_step(self, step_id: str, fields: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = self.runtime_steps[step_id]
        stored.update(fields)
        return stored

    def insert_runtime_event(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        existing = self._find_by_run_idempotency(
            self.runtime_events,
            str(record["run_id"]),
            str(record["idempotency_key"]),
        )
        if existing is not None:
            return existing

        stored = dict(record)
        self.runtime_events.append(stored)
        return stored

    def insert_runtime_checkpoint(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        existing = self._find_by_run_index(
            self.runtime_checkpoints,
            str(record["run_id"]),
            int(record["checkpoint_index"]),
            "checkpoint_index",
        )
        if existing is not None:
            return existing

        stored = dict(record)
        self.runtime_checkpoints.append(stored)
        return stored

    def events_for_run(self, run_id: str) -> tuple[Mapping[str, Any], ...]:
        return tuple(event for event in self.runtime_events if event["run_id"] == run_id)

    def checkpoints_for_run(self, run_id: str) -> tuple[Mapping[str, Any], ...]:
        return tuple(
            checkpoint
            for checkpoint in self.runtime_checkpoints
            if checkpoint["run_id"] == run_id
        )

    def as_runtime_plane_recordset(
        self,
        *,
        contract_version: str = "0.2.0",
        environment: str = "dev",
    ) -> dict[str, Any]:
        return {
            "contract_version": contract_version,
            "environment": environment,
            "records": {
                "runtime_runs": list(self.runtime_runs.values()),
                "runtime_steps": list(self.runtime_steps.values()),
                "runtime_events": list(self.runtime_events),
                "runtime_checkpoints": list(self.runtime_checkpoints),
                "tool_invocations": list(self.tool_invocations),
                "validation_results": list(self.validation_results),
                "memory_candidates": list(self.memory_candidates),
            },
        }

    @staticmethod
    def _find_by_run_idempotency(
        records: Any,
        run_id: str,
        idempotency_key: str,
    ) -> Mapping[str, Any] | None:
        for record in records:
            if record["run_id"] == run_id and record.get("idempotency_key") == idempotency_key:
                return record
        return None

    @staticmethod
    def _find_by_run_index(
        records: Any,
        run_id: str,
        index: int,
        index_field: str,
    ) -> Mapping[str, Any] | None:
        for record in records:
            if record["run_id"] == run_id and record[index_field] == index:
                return record
        return None


class PostgresRuntimeStore:
    """Postgres adapter for the Hetzner runtime tables.

    The adapter accepts a DB-API/psycopg style connection and keeps transaction
    ownership with the caller. Tests can pass a fake connection without importing
    psycopg.
    """

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def insert_runtime_run(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.runtime_runs (
                id, task_id, profile_id, profile_version, status, started_at,
                completed_at, artifact_root_uri, token_budget_total,
                tokens_used_total, stop_reason
            )
            VALUES (
                %(id)s, %(task_id)s, %(profile_id)s, %(profile_version)s,
                %(status)s, %(started_at)s, %(completed_at)s,
                %(artifact_root_uri)s, %(token_budget_total)s,
                %(tokens_used_total)s, %(stop_reason)s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            dict(record),
        )
        return record

    def update_runtime_run(self, run_id: str, fields: Mapping[str, Any]) -> Mapping[str, Any]:
        assignments = ", ".join(f"{field} = %({field})s" for field in fields)
        params = {"id": run_id, **dict(fields)}
        self.connection.execute(
            f"UPDATE runtime.runtime_runs SET {assignments} WHERE id = %(id)s",
            params,
        )
        return params

    def insert_runtime_step(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.runtime_steps (
                id, run_id, step_index, kind, status, started_at, completed_at,
                stop_reason, token_budget, tokens_used, idempotency_key, attempt
            )
            VALUES (
                %(id)s, %(run_id)s, %(step_index)s, %(kind)s, %(status)s,
                %(started_at)s, %(completed_at)s, %(stop_reason)s,
                %(token_budget)s, %(tokens_used)s, %(idempotency_key)s,
                %(attempt)s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            dict(record),
        )
        return record

    def update_runtime_step(self, step_id: str, fields: Mapping[str, Any]) -> Mapping[str, Any]:
        assignments = ", ".join(f"{field} = %({field})s" for field in fields)
        params = {"id": step_id, **dict(fields)}
        self.connection.execute(
            f"UPDATE runtime.runtime_steps SET {assignments} WHERE id = %(id)s",
            params,
        )
        return params

    def insert_runtime_event(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.runtime_events (
                id, run_id, step_id, event_index, event_type, actor_role,
                planned_action_uri, execution_uri, result_uri, stop_reason,
                idempotency_key, created_at
            )
            VALUES (
                %(id)s, %(run_id)s, %(step_id)s, %(event_index)s,
                %(event_type)s, %(actor_role)s, %(planned_action_uri)s,
                %(execution_uri)s, %(result_uri)s, %(stop_reason)s,
                %(idempotency_key)s, %(created_at)s
            )
            ON CONFLICT (run_id, idempotency_key) DO NOTHING
            """,
            dict(record),
        )
        return record

    def insert_runtime_checkpoint(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.runtime_checkpoints (
                id, run_id, step_id, checkpoint_index, phase, state_uri,
                tokens_used_total, created_at
            )
            VALUES (
                %(id)s, %(run_id)s, %(step_id)s, %(checkpoint_index)s,
                %(phase)s, %(state_uri)s, %(tokens_used_total)s, %(created_at)s
            )
            ON CONFLICT (run_id, checkpoint_index) DO NOTHING
            """,
            dict(record),
        )
        return record

    def events_for_run(self, run_id: str) -> tuple[Mapping[str, Any], ...]:
        raise NotImplementedError("PostgresRuntimeStore does not read event streams yet.")

    def checkpoints_for_run(self, run_id: str) -> tuple[Mapping[str, Any], ...]:
        raise NotImplementedError("PostgresRuntimeStore does not read checkpoints yet.")


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
        profile: Mapping[str, Any],
        run_id: str | None = None,
        status: RuntimeStatus = "running",
    ) -> Mapping[str, Any]:
        require_choice(status, RUNTIME_STATUSES, "status")
        run_identifier = run_id or slug_id(task_id.removeprefix("task-"), prefix="run")
        limits = profile.get("limits", {})
        token_budget_total = (
            limits.get("max_tokens") if isinstance(limits, MutableMapping | Mapping) else None
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
    ) -> Mapping[str, Any]:
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
    ) -> Mapping[str, Any]:
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
    ) -> Mapping[str, Any]:
        require_choice(event_type, RUNTIME_EVENT_TYPES, "event_type")
        require_choice(actor_role, RUNTIME_ACTOR_ROLES, "actor_role")
        if stop_reason is not None:
            require_choice(stop_reason, STOP_REASONS, "stop_reason")

        event_index = len(self.store.events_for_run(run_id))
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
    ) -> Mapping[str, Any]:
        require_choice(phase, RUNTIME_PHASES, "phase")
        checkpoint_index = len(self.store.checkpoints_for_run(run_id))
        state_uri = self.artifacts.write_json(
            ("traces", run_id, "checkpoints", f"{checkpoint_index:03d}-{phase}"),
            state,
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
        )
        return stored

    def complete_run(
        self,
        *,
        run_id: str,
        status: RuntimeStatus,
        stop_reason: StopReason,
        tokens_used_total: int = 0,
    ) -> Mapping[str, Any]:
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


def profile_summary(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "profile_id": profile["id"],
        "profile_version": profile["profile_version"],
        "selected_modules": selected_modules(profile),
        "limits": profile["limits"],
        "observability": profile["observability"],
    }
