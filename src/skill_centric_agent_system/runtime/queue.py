from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from random import Random
from time import sleep
from typing import Any

from skill_centric_agent_system.composition import ControlPlaneClient, TaskAnalyzer
from skill_centric_agent_system.composition.profile_composer import CompositionError
from skill_centric_agent_system.runtime.artifacts import JsonArtifactStore
from skill_centric_agent_system.runtime.entrypoint import RuntimeEntryPoint
from skill_centric_agent_system.runtime.loop import MinimalRuntimeLoop, RuntimeLoopError
from skill_centric_agent_system.runtime.models import (
    RUNTIME_QUEUE_STATUSES,
    RuntimeQueueStatus,
    iso_timestamp,
    require_choice,
    slug_id,
    utc_now,
)
from skill_centric_agent_system.runtime.quotas import (
    RuntimeQuotaConfig,
    RuntimeQuotaError,
    RuntimeQuotaManager,
)
from skill_centric_agent_system.runtime.storage_protocol import RuntimeStore
from skill_centric_agent_system.runtime.tenant_status import (
    RuntimeTenantStatusError,
    assert_runtime_tenant_is_startable,
)


class RuntimeQueueError(RuntimeError):
    """Raised when runtime queue state cannot be changed safely."""


@dataclass(frozen=True)
class RuntimeQueueConfig:
    lease_seconds: int = 300
    heartbeat_seconds: int = 30
    max_attempts: int = 3
    retry_delay_seconds: int = 30
    retry_backoff_multiplier: float = 2.0
    retry_jitter_seconds: int = 0
    global_running_limit: int | None = None
    tenant_running_limits: Mapping[str, int] = field(default_factory=dict)
    tenant_queued_limits: Mapping[str, int] = field(default_factory=dict)
    tenant_token_limits_per_minute: Mapping[str, int] = field(default_factory=dict)
    tenant_tool_call_limits_per_minute: Mapping[str, int] = field(default_factory=dict)
    allowed_tenant_ids: tuple[str, ...] = ()
    disabled_tenant_ids: tuple[str, ...] = ()
    environment: str = "dev"
    queue_name: str = "default"
    worker_pool_size: int = 1


@dataclass(frozen=True)
class RuntimeQueueProcessResult:
    queue_id: str
    status: RuntimeQueueStatus
    run_id: str | None
    stop_reason: str | None
    attempt_id: str | None = None


class RuntimeQueueManager:
    """Manage runtime task queue records and payload artifacts."""

    def __init__(
        self,
        *,
        store: RuntimeStore,
        artifacts: JsonArtifactStore,
        clock: Callable[[], Any] = utc_now,
    ) -> None:
        self.store = store
        self.artifacts = artifacts
        self.clock = clock
        self.analyzer = TaskAnalyzer()

    def enqueue(
        self,
        task: Mapping[str, Any],
        *,
        composition_context_response: Mapping[str, Any] | None = None,
        priority: int = 0,
        scheduled_at: str | None = None,
        max_attempts: int = 3,
        idempotency_key: str | None = None,
        environment: str = "dev",
        queue_name: str = "default",
        tenant_queued_limits: Mapping[str, int] | None = None,
        disabled_tenant_ids: tuple[str, ...] = (),
    ) -> Mapping[str, Any]:
        analyzed = self.analyzer.analyze(task)
        if analyzed.auth_claims.tenant_id == "global":
            raise RuntimeQueueError("Runtime queue items require an explicit tenant_id.")
        if analyzed.auth_claims.tenant_id in disabled_tenant_ids:
            raise RuntimeQueueError("Disabled or archived tenants cannot enqueue runtime work.")
        if (
            composition_context_response is not None
            and composition_context_response.get("tenant_authority") is not None
        ):
            assert_runtime_tenant_is_startable(task, composition_context_response)
        queued_limit = dict(tenant_queued_limits or {}).get(analyzed.auth_claims.tenant_id)
        if (
            queued_limit is not None
            and self._tenant_queued_count(analyzed.auth_claims.tenant_id) >= queued_limit
        ):
            raise RuntimeQueueError("Tenant queued backlog limit exceeded.")
        now = iso_timestamp(self.clock())
        key = idempotency_key or f"{analyzed.task_id}:initial"
        queue_id = slug_id(key, prefix="queue")
        task_payload_uri = self.artifacts.write_json(
            ("queue", queue_id, "task-payload"),
            dict(task),
            redact=False,
        )
        composition_context_uri = (
            self.artifacts.write_json(
                ("queue", queue_id, "composition-context-response"),
                dict(composition_context_response),
                redact=False,
            )
            if composition_context_response is not None
            else None
        )
        return self.store.insert_runtime_queue_item(
            {
                "id": queue_id,
                "task_id": analyzed.task_id,
                "tenant_id": analyzed.auth_claims.tenant_id,
                "area_id": analyzed.auth_claims.area_id,
                "environment": environment,
                "queue_name": queue_name,
                "status": "queued",
                "priority": priority,
                "scheduled_at": scheduled_at or now,
                "attempts": 0,
                "max_attempts": max_attempts,
                "claimed_by": None,
                "claimed_at": None,
                "claimed_until": None,
                "lease_expires_at": None,
                "heartbeat_at": None,
                "attempt_id": None,
                "task_payload_uri": task_payload_uri,
                "composition_context_uri": composition_context_uri,
                "run_id": None,
                "last_error": None,
                "idempotency_key": key,
                "created_at": now,
                "updated_at": now,
            }
        )

    def claim_next(
        self,
        *,
        worker_id: str,
        config: RuntimeQueueConfig,
    ) -> Mapping[str, Any] | None:
        claimed_at = self.clock()
        lease_until = claimed_at + timedelta(seconds=config.lease_seconds)
        return self.store.claim_next_runtime_queue_item(
            worker_id=worker_id,
            claimed_at=iso_timestamp(claimed_at),
            lease_expires_at=iso_timestamp(lease_until),
            tenant_running_limits=config.tenant_running_limits,
            global_running_limit=config.global_running_limit,
            allowed_tenant_ids=config.allowed_tenant_ids,
            disabled_tenant_ids=config.disabled_tenant_ids,
            environment=config.environment,
            queue_name=config.queue_name,
        )

    def claim_next_attempt(
        self,
        *,
        worker_id: str,
        config: RuntimeQueueConfig,
    ) -> Mapping[str, Any] | None:
        claimed_at = self.clock()
        lease_until = claimed_at + timedelta(seconds=config.lease_seconds)
        return self.store.claim_next_runtime_queue_attempt(
            worker_id=worker_id,
            claimed_at=iso_timestamp(claimed_at),
            lease_expires_at=iso_timestamp(lease_until),
            tenant_running_limits=config.tenant_running_limits,
            global_running_limit=config.global_running_limit,
            allowed_tenant_ids=config.allowed_tenant_ids,
            disabled_tenant_ids=config.disabled_tenant_ids,
            environment=config.environment,
            queue_name=config.queue_name,
        )

    def heartbeat(self, queue_id: str, *, config: RuntimeQueueConfig) -> Mapping[str, Any]:
        now = self.clock()
        claimed_until = now + timedelta(seconds=config.lease_seconds)
        return self.store.heartbeat_runtime_queue_item(
            queue_id,
            {
                "heartbeat_at": iso_timestamp(now),
                "claimed_until": iso_timestamp(claimed_until),
                "lease_expires_at": iso_timestamp(claimed_until),
                "updated_at": iso_timestamp(now),
            },
        )

    def recover_stale_claims(self) -> tuple[Mapping[str, Any], ...]:
        return self.store.recover_stale_runtime_queue_items(now=iso_timestamp(self.clock()))

    def mark_running(
        self,
        queue_id: str,
        *,
        run_id: str,
        attempt_id: str | None = None,
    ) -> Mapping[str, Any]:
        return self._update_status(queue_id, "running", run_id=run_id, attempt_id=attempt_id)

    def mark_succeeded(self, queue_id: str, *, run_id: str) -> Mapping[str, Any]:
        return self._update_status(queue_id, "succeeded", run_id=run_id, last_error=None)

    def mark_cancelled(self, queue_id: str, *, run_id: str | None = None) -> Mapping[str, Any]:
        item = self.store.get_runtime_queue_item(queue_id)
        if item is None:
            raise RuntimeQueueError(f"Runtime queue item not found: {queue_id}")
        if item["status"] == "cancelled":
            return item
        if item["status"] in {"succeeded", "failed", "dead_lettered"}:
            raise RuntimeQueueError("Terminal runtime queue items cannot be cancelled.")
        completed_at = iso_timestamp(self.clock())
        stored = self._update_status(queue_id, "cancelled", run_id=run_id, clear_claim=True)
        self.store.release_runtime_queue_claims(
            queue_id,
            released_at=completed_at,
            release_reason="cancelled",
        )
        effective_run_id = run_id or item.get("run_id")
        if effective_run_id is not None:
            run = self.store.get_runtime_run(str(effective_run_id))
            if run is not None and run.get("status") not in {
                "succeeded",
                "failed",
                "cancelled",
            }:
                self.store.update_runtime_run(
                    str(effective_run_id),
                    {
                        "status": "cancelled",
                        "stop_reason": "cancelled",
                        "completed_at": completed_at,
                    },
                )
        return stored

    def retry(
        self,
        queue_id: str,
        *,
        scheduled_at: str | None = None,
        idempotency_key: str | None = None,
        max_attempts: int | None = None,
    ) -> Mapping[str, Any]:
        item = self.store.get_runtime_queue_item(queue_id)
        if item is None:
            raise RuntimeQueueError(f"Runtime queue item not found: {queue_id}")
        if item["status"] not in {"failed", "cancelled", "dead_lettered"}:
            raise RuntimeQueueError(
                "Only failed, cancelled, or dead-lettered runtime queue items can be retried."
            )

        retry_key = idempotency_key or (
            f"{item.get('idempotency_key') or queue_id}:manual-retry:"
            f"{int(item['attempts']) + 1}"
        )
        return self.enqueue(
            self.load_task(item),
            composition_context_response=self.load_composition_context(item),
            priority=int(item["priority"]),
            scheduled_at=scheduled_at,
            max_attempts=max_attempts or int(item["max_attempts"]),
            idempotency_key=retry_key,
            environment=str(item.get("environment") or "dev"),
            queue_name=str(item.get("queue_name") or "default"),
        )

    def mark_failed_or_retry(
        self,
        queue_item: Mapping[str, Any],
        *,
        error: Exception,
        config: RuntimeQueueConfig,
        run_id: str | None,
    ) -> Mapping[str, Any]:
        attempts = int(queue_item["attempts"])
        status: RuntimeQueueStatus = (
            "retry_scheduled"
            if attempts < int(queue_item["max_attempts"])
            else "dead_lettered"
        )
        delay = config.retry_delay_seconds * (
            config.retry_backoff_multiplier ** max(attempts - 1, 0)
        )
        if config.retry_jitter_seconds > 0:
            delay += Random(str(queue_item["id"])).randint(0, config.retry_jitter_seconds)
        scheduled_at = self.clock() + timedelta(seconds=delay)
        stored = self._update_status(
            str(queue_item["id"]),
            status,
            run_id=run_id,
            scheduled_at=iso_timestamp(scheduled_at),
            last_error=f"{type(error).__name__}: {error}",
            clear_claim=True,
        )
        if status == "dead_lettered":
            self.store.insert_runtime_dead_letter(
                {
                    "id": slug_id(f"{queue_item['id']}-{queue_item['attempts']}", prefix="dlq"),
                    "queue_id": str(queue_item["id"]),
                    "run_id": run_id,
                    "attempt_id": queue_item.get("attempt_id"),
                    "tenant_id": str(queue_item["tenant_id"]),
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "created_at": iso_timestamp(self.clock()),
                }
            )
        return stored

    def load_task(self, queue_item: Mapping[str, Any]) -> Mapping[str, Any]:
        task = self.artifacts.read_json(str(queue_item["task_payload_uri"]))
        if not isinstance(task, Mapping):
            raise RuntimeQueueError("Runtime queue task artifact must be a JSON object.")
        return task

    def load_composition_context(
        self,
        queue_item: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        uri = queue_item.get("composition_context_uri")
        if uri is None:
            return None
        context = self.artifacts.read_json(str(uri))
        if not isinstance(context, Mapping):
            raise RuntimeQueueError(
                "Runtime queue composition context artifact must be a JSON object."
            )
        return context

    def _update_status(
        self,
        queue_id: str,
        status: RuntimeQueueStatus,
        *,
        run_id: str | None = None,
        attempt_id: str | None = None,
        scheduled_at: str | None = None,
        last_error: str | None = None,
        clear_claim: bool = False,
    ) -> Mapping[str, Any]:
        require_choice(status, RUNTIME_QUEUE_STATUSES, "runtime_queue_status")
        fields: dict[str, Any] = {
            "status": status,
            "updated_at": iso_timestamp(self.clock()),
        }
        if run_id is not None:
            fields["run_id"] = run_id
        if attempt_id is not None:
            fields["attempt_id"] = attempt_id
        if scheduled_at is not None:
            fields["scheduled_at"] = scheduled_at
        if last_error is not None or status == "succeeded":
            fields["last_error"] = last_error
        if clear_claim:
            fields.update(
                {
                    "claimed_by": None,
                    "claimed_at": None,
                    "claimed_until": None,
                    "lease_expires_at": None,
                    "heartbeat_at": None,
                }
            )
        return self.store.update_runtime_queue_item(queue_id, fields)

    def _tenant_queued_count(self, tenant_id: str) -> int:
        recordset = self.store.as_runtime_plane_recordset()
        queue_items = recordset.get("records", {}).get("runtime_queue_items", [])
        if not isinstance(queue_items, list):
            return 0
        return sum(
            1
            for item in queue_items
            if isinstance(item, Mapping)
            and item.get("tenant_id") == tenant_id
            and item.get("status") in {"queued", "retry_scheduled"}
        )


class RuntimeQueueWorker:
    """Claim and execute queued runtime tasks through the single-agent runtime."""

    def __init__(
        self,
        *,
        worker_id: str,
        store: RuntimeStore,
        artifacts: JsonArtifactStore,
        repository_root: str,
        control_plane_client: ControlPlaneClient | None = None,
        config: RuntimeQueueConfig | None = None,
        clock: Callable[[], Any] = utc_now,
    ) -> None:
        self.worker_id = worker_id
        self.store = store
        self.artifacts = artifacts
        self.repository_root = repository_root
        self.control_plane_client = control_plane_client
        self.config = config or RuntimeQueueConfig()
        self.manager = RuntimeQueueManager(store=store, artifacts=artifacts, clock=clock)

    def process_one(self) -> RuntimeQueueProcessResult | None:
        claim_bundle = self.manager.claim_next_attempt(
            worker_id=self.worker_id,
            config=self.config,
        )
        if claim_bundle is None:
            return None

        queue_item = claim_bundle["queue_item"]
        attempt = claim_bundle["attempt"]
        claim = claim_bundle["claim"]
        run_id = str(attempt["run_id"])
        attempt_id = str(attempt["id"])
        claim_id = str(claim["id"])
        try:
            task = self.manager.load_task(queue_item)
            composition_context = self.manager.load_composition_context(queue_item)
            entrypoint = RuntimeEntryPoint(
                store=self.store,
                artifacts=self.artifacts,
                control_plane_client=self.control_plane_client,
            )
            start_result = entrypoint.start(
                task,
                composition_context_response=composition_context,
                run_id=run_id,
            )
            self.manager.mark_running(
                str(queue_item["id"]),
                run_id=start_result.run_id,
                attempt_id=attempt_id,
            )
            self.store.update_runtime_run_attempt(
                attempt_id,
                {
                    "run_id": start_result.run_id,
                    "profile_id": start_result.profile["id"],
                    "profile_sha256": start_result.profile_sha256,
                },
            )
            quota = RuntimeQuotaManager(
                store=self.store,
                artifacts=self.artifacts,
                clock=self.manager.clock,
            )
            quota_reservation = quota.reserve(
                queue_id=str(queue_item["id"]),
                run_id=start_result.run_id,
                tenant_id=str(queue_item["tenant_id"]),
                profile=start_result.profile,
                config=RuntimeQuotaConfig(
                    tenant_token_limits_per_minute=self.config.tenant_token_limits_per_minute,
                    tenant_tool_call_limits_per_minute=(
                        self.config.tenant_tool_call_limits_per_minute
                    ),
                ),
            )
            self.manager.heartbeat(str(queue_item["id"]), config=self.config)
            result = MinimalRuntimeLoop(
                store=self.store,
                artifacts=self.artifacts,
                repository_root=self.repository_root,
                control_plane_client=self.control_plane_client,
                cancellation_checker=lambda _run_id: self._queue_item_is_cancelled(
                    str(queue_item["id"])
                ),
            ).run(start_result)
        except (
            CompositionError,
            RuntimeLoopError,
            RuntimeQueueError,
            RuntimeQuotaError,
            RuntimeTenantStatusError,
        ) as error:
            run = self.store.get_runtime_run(run_id)
            if run is not None and run.get("status") not in {"failed", "cancelled", "succeeded"}:
                self.store.update_runtime_run(
                    run_id,
                    {
                        "status": "failed",
                        "completed_at": iso_timestamp(self.manager.clock()),
                        "stop_reason": getattr(error, "stop_reason", "runtime_error"),
                    },
                )
            stored = self.manager.mark_failed_or_retry(
                queue_item,
                error=error,
                config=self.config,
                run_id=run_id,
            )
            self.store.update_runtime_run_attempt(
                attempt_id,
                {
                    "status": stored["status"],
                    "completed_at": iso_timestamp(self.manager.clock()),
                    "stop_reason": getattr(error, "stop_reason", "runtime_error"),
                },
            )
            self.store.update_runtime_run_claim(
                claim_id,
                {
                    "released_at": iso_timestamp(self.manager.clock()),
                    "release_reason": stored["status"],
                },
            )
            if "quota_reservation" in locals():
                RuntimeQuotaManager(
                    store=self.store,
                    artifacts=self.artifacts,
                    clock=self.manager.clock,
                ).refund(str(quota_reservation["id"]))
            return RuntimeQueueProcessResult(
                queue_id=str(queue_item["id"]),
                status=stored["status"],
                run_id=run_id,
                stop_reason=getattr(error, "stop_reason", "runtime_error"),
                attempt_id=attempt_id,
            )

        if result.status == "cancelled":
            stored = self.manager.mark_cancelled(str(queue_item["id"]), run_id=result.run_id)
            self.store.update_runtime_run_attempt(
                attempt_id,
                {
                    "status": stored["status"],
                    "completed_at": iso_timestamp(self.manager.clock()),
                    "stop_reason": result.stop_reason,
                },
            )
            self.store.update_runtime_run_claim(
                claim_id,
                {
                    "released_at": iso_timestamp(self.manager.clock()),
                    "release_reason": stored["status"],
                },
            )
            if "quota_reservation" in locals():
                RuntimeQuotaManager(
                    store=self.store,
                    artifacts=self.artifacts,
                    clock=self.manager.clock,
                ).refund(str(quota_reservation["id"]))
            return RuntimeQueueProcessResult(
                queue_id=str(queue_item["id"]),
                status=stored["status"],
                run_id=result.run_id,
                stop_reason=result.stop_reason,
                attempt_id=attempt_id,
            )

        stored = self.manager.mark_succeeded(str(queue_item["id"]), run_id=result.run_id)
        if "quota_reservation" in locals():
            RuntimeQuotaManager(
                store=self.store,
                artifacts=self.artifacts,
                clock=self.manager.clock,
            ).finalize(str(quota_reservation["id"]))
        self.store.update_runtime_run_attempt(
            attempt_id,
            {
                "status": stored["status"],
                "completed_at": iso_timestamp(self.manager.clock()),
                "stop_reason": result.stop_reason,
            },
        )
        self.store.update_runtime_run_claim(
            claim_id,
            {
                "released_at": iso_timestamp(self.manager.clock()),
                "release_reason": stored["status"],
            },
        )
        return RuntimeQueueProcessResult(
            queue_id=str(queue_item["id"]),
            status=stored["status"],
            run_id=result.run_id,
            stop_reason=result.stop_reason,
            attempt_id=attempt_id,
        )

    def run_forever(
        self,
        *,
        poll_interval_seconds: float = 1.0,
        stop_requested: Callable[[], bool] | None = None,
        after_iteration: Callable[[BaseException | None], None] | None = None,
    ) -> None:
        should_stop = stop_requested or (lambda: False)
        while not should_stop():
            try:
                result = self.process_one()
            except BaseException as error:
                if after_iteration is not None:
                    after_iteration(error)
                raise
            if after_iteration is not None:
                after_iteration(None)
            if result is None:
                if should_stop():
                    break
                sleep(poll_interval_seconds)

    def _queue_item_is_cancelled(self, queue_id: str) -> bool:
        stored = self.store.get_runtime_queue_item(queue_id)
        return stored is not None and stored.get("status") == "cancelled"
