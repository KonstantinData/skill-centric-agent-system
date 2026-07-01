from __future__ import annotations

from collections.abc import Mapping
from threading import Lock
from typing import Any, cast

from skill_centric_agent_system.runtime.models import slug_id


class InMemoryRuntimeStore:
    """Runtime store used by tests and local entrypoint dry-runs."""

    def __init__(self) -> None:
        self.runtime_runs: dict[str, dict[str, Any]] = {}
        self.runtime_queue_items: dict[str, dict[str, Any]] = {}
        self.runtime_run_attempts: dict[str, dict[str, Any]] = {}
        self.runtime_run_claims: dict[str, dict[str, Any]] = {}
        self.runtime_dead_letters: dict[str, dict[str, Any]] = {}
        self.runtime_quota_reservations: dict[str, dict[str, Any]] = {}
        self.runtime_steps: dict[str, dict[str, Any]] = {}
        self.runtime_events: list[dict[str, Any]] = []
        self.runtime_checkpoints: list[dict[str, Any]] = []
        self.tool_invocations: list[dict[str, Any]] = []
        self.validation_results: list[dict[str, Any]] = []
        self.memory_candidates: list[dict[str, Any]] = []
        self._lock = Lock()
        self._event_indices: dict[str, int] = {}
        self._checkpoint_indices: dict[str, int] = {}

    def insert_runtime_queue_item(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        with self._lock:
            idempotency_key = record.get("idempotency_key")
            if idempotency_key is not None:
                for existing in self.runtime_queue_items.values():
                    if existing.get("idempotency_key") == idempotency_key:
                        return existing

            stored = dict(record)
            self.runtime_queue_items[stored["id"]] = stored
            return stored

    def get_runtime_queue_item(self, queue_id: str) -> Mapping[str, Any] | None:
        return self.runtime_queue_items.get(queue_id)

    def update_runtime_queue_item(
        self,
        queue_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        with self._lock:
            stored = self.runtime_queue_items[queue_id]
            stored.update(fields)
            return stored

    def heartbeat_runtime_queue_item(
        self,
        queue_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        with self._lock:
            stored = self.runtime_queue_items[queue_id]
            stored.update(fields)
            claim = self._active_claim_for_queue(queue_id)
            if claim is not None:
                claim.update(
                    {
                        "heartbeat_at": fields.get("heartbeat_at", claim.get("heartbeat_at")),
                        "claimed_until": fields.get("claimed_until", claim.get("claimed_until")),
                    }
                )
            return stored

    def claim_next_runtime_queue_attempt(
        self,
        *,
        worker_id: str,
        claimed_at: str,
        lease_expires_at: str,
        tenant_running_limits: Mapping[str, int] | None = None,
        global_running_limit: int | None = None,
        allowed_tenant_ids: tuple[str, ...] = (),
        disabled_tenant_ids: tuple[str, ...] = (),
        environment: str | None = None,
        queue_name: str | None = None,
    ) -> Mapping[str, Any] | None:
        limits = dict(tenant_running_limits or {})
        allowed = set(allowed_tenant_ids)
        disabled = set(disabled_tenant_ids)
        with self._lock:
            if (
                global_running_limit is not None
                and self._global_running_count() >= global_running_limit
            ):
                return None
            candidates = sorted(
                (
                    item
                    for item in self.runtime_queue_items.values()
                    if item["status"] in {"queued", "retry_scheduled"}
                    and str(item["scheduled_at"]) <= claimed_at
                    and (not allowed or item["tenant_id"] in allowed)
                    and item["tenant_id"] not in disabled
                    and (environment is None or item.get("environment") == environment)
                    and (queue_name is None or item.get("queue_name") == queue_name)
                ),
                key=lambda item: (
                    -int(item["priority"]),
                    str(item["scheduled_at"]),
                    str(item["created_at"]),
                    str(item["id"]),
                ),
            )
            for item in candidates:
                tenant_id = str(item["tenant_id"])
                limit = limits.get(tenant_id)
                if limit is not None and self._tenant_running_count(tenant_id) >= limit:
                    continue

                attempts = int(item["attempts"]) + 1
                run_id = slug_id(f"{item['task_id']}-attempt-{attempts}", prefix="run")
                attempt_id = slug_id(f"{item['id']}-attempt-{attempts}", prefix="attempt")
                claim_id = slug_id(f"{item['id']}-{worker_id}-{attempts}", prefix="claim")
                item.update(
                    {
                        "status": "claiming",
                        "attempts": attempts,
                        "claimed_by": worker_id,
                        "claimed_at": claimed_at,
                        "lease_expires_at": lease_expires_at,
                        "claimed_until": lease_expires_at,
                        "heartbeat_at": claimed_at,
                        "attempt_id": attempt_id,
                        "run_id": run_id,
                        "updated_at": claimed_at,
                    }
                )
                attempt = {
                    "id": attempt_id,
                    "queue_id": str(item["id"]),
                    "run_id": run_id,
                    "tenant_id": tenant_id,
                    "attempt_number": attempts,
                    "status": "running",
                    "started_at": claimed_at,
                    "completed_at": None,
                    "stop_reason": None,
                    "profile_id": None,
                    "profile_sha256": None,
                }
                claim = {
                    "id": claim_id,
                    "queue_id": str(item["id"]),
                    "worker_id": worker_id,
                    "tenant_id": tenant_id,
                    "claimed_at": claimed_at,
                    "claimed_until": lease_expires_at,
                    "heartbeat_at": claimed_at,
                    "released_at": None,
                    "release_reason": None,
                }
                self.runtime_run_attempts[attempt_id] = attempt
                self.runtime_run_claims[claim_id] = claim
                return {"queue_item": dict(item), "attempt": dict(attempt), "claim": dict(claim)}
        return None

    def claim_next_runtime_queue_item(
        self,
        *,
        worker_id: str,
        claimed_at: str,
        lease_expires_at: str,
        tenant_running_limits: Mapping[str, int] | None = None,
        global_running_limit: int | None = None,
        allowed_tenant_ids: tuple[str, ...] = (),
        disabled_tenant_ids: tuple[str, ...] = (),
        environment: str | None = None,
        queue_name: str | None = None,
    ) -> Mapping[str, Any] | None:
        claim = self.claim_next_runtime_queue_attempt(
            worker_id=worker_id,
            claimed_at=claimed_at,
            lease_expires_at=lease_expires_at,
            tenant_running_limits=tenant_running_limits,
            global_running_limit=global_running_limit,
            allowed_tenant_ids=allowed_tenant_ids,
            disabled_tenant_ids=disabled_tenant_ids,
            environment=environment,
            queue_name=queue_name,
        )
        if claim is None:
            return None
        return cast(Mapping[str, Any], claim["queue_item"])

    def recover_stale_runtime_queue_items(self, *, now: str) -> tuple[Mapping[str, Any], ...]:
        recovered: list[Mapping[str, Any]] = []
        with self._lock:
            for item in self.runtime_queue_items.values():
                claimed_until = item.get("claimed_until") or item.get("lease_expires_at")
                if item["status"] not in {"claiming", "running"} or claimed_until is None:
                    continue
                if str(claimed_until) > now:
                    continue
                item.update(
                    {
                        "status": "retry_scheduled",
                        "claimed_by": None,
                        "claimed_at": None,
                        "claimed_until": None,
                        "lease_expires_at": None,
                        "heartbeat_at": None,
                        "updated_at": now,
                        "last_error": "Stale runtime queue claim recovered.",
                    }
                )
                claim = self._active_claim_for_queue(str(item["id"]))
                if claim is not None:
                    claim.update(
                        {
                            "released_at": now,
                            "release_reason": "stale_recovered",
                        }
                    )
                recovered.append(dict(item))
        return tuple(recovered)

    def insert_runtime_run_attempt(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = dict(record)
        self.runtime_run_attempts[stored["id"]] = stored
        return stored

    def update_runtime_run_attempt(
        self,
        attempt_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        stored = self.runtime_run_attempts[attempt_id]
        stored.update(fields)
        return stored

    def insert_runtime_run_claim(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = dict(record)
        self.runtime_run_claims[stored["id"]] = stored
        return stored

    def update_runtime_run_claim(
        self,
        claim_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        stored = self.runtime_run_claims[claim_id]
        stored.update(fields)
        return stored

    def release_runtime_queue_claims(
        self,
        queue_id: str,
        *,
        released_at: str,
        release_reason: str,
    ) -> tuple[Mapping[str, Any], ...]:
        released: list[Mapping[str, Any]] = []
        with self._lock:
            for claim in self.runtime_run_claims.values():
                if claim.get("queue_id") != queue_id or claim.get("released_at") is not None:
                    continue
                claim.update(
                    {
                        "released_at": released_at,
                        "release_reason": release_reason,
                    }
                )
                released.append(dict(claim))
        return tuple(released)

    def insert_runtime_dead_letter(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = dict(record)
        self.runtime_dead_letters[stored["id"]] = stored
        return stored

    def insert_runtime_quota_reservation(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = dict(record)
        self.runtime_quota_reservations[stored["id"]] = stored
        return stored

    def update_runtime_quota_reservation(
        self,
        reservation_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        stored = self.runtime_quota_reservations[reservation_id]
        stored.update(fields)
        return stored

    def insert_runtime_run(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = dict(record)
        self.runtime_runs[stored["id"]] = stored
        return stored

    def update_runtime_run(self, run_id: str, fields: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = self.runtime_runs[run_id]
        stored.update(fields)
        return stored

    def get_runtime_run(self, run_id: str) -> Mapping[str, Any] | None:
        return self.runtime_runs.get(run_id)

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

    def allocate_runtime_event_index(self, run_id: str) -> int:
        with self._lock:
            next_index = self._event_indices.get(run_id)
            if next_index is None:
                existing_indices = [
                    int(event["event_index"])
                    for event in self.runtime_events
                    if event["run_id"] == run_id
                ]
                next_index = max(existing_indices, default=-1) + 1
            self._event_indices[run_id] = next_index + 1
            return next_index

    def insert_runtime_event(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        with self._lock:
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

    def allocate_runtime_checkpoint_index(self, run_id: str) -> int:
        with self._lock:
            next_index = self._checkpoint_indices.get(run_id)
            if next_index is None:
                existing_indices = [
                    int(checkpoint["checkpoint_index"])
                    for checkpoint in self.runtime_checkpoints
                    if checkpoint["run_id"] == run_id
                ]
                next_index = max(existing_indices, default=-1) + 1
            self._checkpoint_indices[run_id] = next_index + 1
            return next_index

    def insert_runtime_checkpoint(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        with self._lock:
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

    def insert_tool_invocation(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = dict(record)
        self.tool_invocations.append(stored)
        return stored

    def insert_validation_result(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = dict(record)
        self.validation_results.append(stored)
        return stored

    def insert_memory_candidate(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = dict(record)
        self.memory_candidates.append(stored)
        return stored

    def update_memory_candidate(
        self,
        candidate_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        for candidate in self.memory_candidates:
            if candidate["id"] == candidate_id:
                candidate.update(fields)
                return candidate
        raise KeyError(candidate_id)

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
                "runtime_queue_items": list(self.runtime_queue_items.values()),
                "runtime_run_attempts": list(self.runtime_run_attempts.values()),
                "runtime_run_claims": list(self.runtime_run_claims.values()),
                "runtime_dead_letters": list(self.runtime_dead_letters.values()),
                "runtime_quota_reservations": list(self.runtime_quota_reservations.values()),
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
                return cast(Mapping[str, Any], record)
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
                return cast(Mapping[str, Any], record)
        return None

    def _active_claim_for_queue(self, queue_id: str) -> dict[str, Any] | None:
        for claim in self.runtime_run_claims.values():
            if claim.get("queue_id") == queue_id and claim.get("released_at") is None:
                return claim
        return None

    def _tenant_running_count(self, tenant_id: str) -> int:
        return sum(
            1
            for item in self.runtime_queue_items.values()
            if item["tenant_id"] == tenant_id and item["status"] in {"claiming", "running"}
        )

    def _global_running_count(self) -> int:
        return sum(
            1
            for item in self.runtime_queue_items.values()
            if item["status"] in {"claiming", "running"}
        )

