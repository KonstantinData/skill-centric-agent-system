from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from skill_centric_agent_system.composition import ControlPlaneClient
from skill_centric_agent_system.runtime.artifacts import JsonArtifactStore
from skill_centric_agent_system.runtime.entrypoint import RuntimeEntryPoint
from skill_centric_agent_system.runtime.loop import MinimalRuntimeLoop
from skill_centric_agent_system.runtime.queue import (
    RuntimeQueueConfig,
    RuntimeQueueManager,
)
from skill_centric_agent_system.runtime.storage_protocol import RuntimeStore


class RuntimeApiError(RuntimeError):
    """Raised when a tenant-scoped runtime API operation is denied or invalid."""


@dataclass(frozen=True)
class RuntimeApiPrincipal:
    principal_id: str
    tenant_id: str
    area_id: str
    roles: tuple[str, ...] = ()


class RuntimeApiService:
    """Transport-neutral implementation of the Runtime API contract."""

    def __init__(
        self,
        *,
        store: RuntimeStore,
        artifacts: JsonArtifactStore,
        repository_root: str,
        control_plane_client: ControlPlaneClient | None = None,
        queue_config: RuntimeQueueConfig | None = None,
    ) -> None:
        self.store = store
        self.artifacts = artifacts
        self.repository_root = repository_root
        self.control_plane_client = control_plane_client
        self.queue_config = queue_config or RuntimeQueueConfig()

    def start_run(
        self,
        request: Mapping[str, Any],
        *,
        principal: RuntimeApiPrincipal,
    ) -> Mapping[str, Any]:
        task = request.get("task")
        if not isinstance(task, Mapping):
            raise RuntimeApiError("Runtime start request requires a task object.")
        self._assert_task_tenant(task, principal)
        execution = request.get("execution", {})
        run_immediately = bool(
            execution.get("run_immediately", False) if isinstance(execution, Mapping) else False
        )
        composition_context = request.get("composition_context_response")
        if composition_context is not None and not isinstance(composition_context, Mapping):
            raise RuntimeApiError("composition_context_response must be an object when provided.")

        if not run_immediately:
            queue_item = RuntimeQueueManager(
                store=self.store,
                artifacts=self.artifacts,
            ).enqueue(
                task,
                composition_context_response=composition_context,
                idempotency_key=str(request.get("idempotency_key") or f"{task['id']}:start"),
                environment=str(request.get("environment") or self.queue_config.environment),
                queue_name=self.queue_config.queue_name,
                tenant_queued_limits=self.queue_config.tenant_queued_limits,
                disabled_tenant_ids=self.queue_config.disabled_tenant_ids,
            )
            return {
                "contract_version": "0.1.0",
                "kind": "start_run_response",
                "response_mode": "queued",
                "status": queue_item["status"],
                "queue_item": self._queue_summary(queue_item),
                "run": None,
            }

        entrypoint = RuntimeEntryPoint(
            store=self.store,
            artifacts=self.artifacts,
            control_plane_client=self.control_plane_client,
            environment=str(request.get("environment") or "dev"),  # type: ignore[arg-type]
        )
        start_result = entrypoint.start(
            task,
            composition_context_response=composition_context,
        )
        loop_result = MinimalRuntimeLoop(
            store=self.store,
            artifacts=self.artifacts,
            repository_root=self.repository_root,
            control_plane_client=self.control_plane_client,
        ).run(start_result)
        return {
            "contract_version": "0.1.0",
            "kind": "start_run_response",
            "response_mode": "immediate",
            "status": loop_result.status,
            "queue_item": None,
            "run": self._run_summary(self.store.get_runtime_run(start_result.run_id) or {}),
        }

    def get_status(
        self,
        run_id: str,
        *,
        principal: RuntimeApiPrincipal,
    ) -> Mapping[str, Any]:
        run = self.store.get_runtime_run(run_id)
        if run is None:
            raise RuntimeApiError("Runtime run was not found.")
        self._assert_run_tenant(run_id, principal)
        return {
            "contract_version": "0.1.0",
            "kind": "run_status_response",
            "run": self._run_summary(run),
        }

    def get_result(
        self,
        run_id: str,
        *,
        principal: RuntimeApiPrincipal,
    ) -> Mapping[str, Any]:
        status = self.get_status(run_id, principal=principal)["run"]
        if status["status"] not in {"succeeded", "failed", "cancelled"}:
            raise RuntimeApiError("Runtime result is not available for a non-terminal run.")
        return {
            "contract_version": "0.1.0",
            "kind": "run_result_response",
            "run": status,
            "result": {
                "response": None,
                "validation_result_uris": [],
                "event_count": len(self.store.events_for_run(run_id)),
                "checkpoint_count": len(self.store.checkpoints_for_run(run_id)),
            },
        }

    def cancel_run(
        self,
        run_or_queue_id: str,
        *,
        principal: RuntimeApiPrincipal,
    ) -> Mapping[str, Any]:
        queue_item = self._queue_item_for_run_or_queue_id(run_or_queue_id)
        self._assert_queue_tenant(queue_item, principal)
        previous_status = str(queue_item["status"])
        cancelled = RuntimeQueueManager(store=self.store, artifacts=self.artifacts).mark_cancelled(
            str(queue_item["id"])
        )
        return {
            "contract_version": "0.1.0",
            "kind": "cancel_run_response",
            "run_id": cancelled.get("run_id") or run_or_queue_id,
            "previous_status": previous_status if previous_status != "claiming" else "running",
            "status": "cancelled",
            "stop_reason": "cancelled",
            "queue_item": self._queue_summary(cancelled),
        }

    def retry_run(
        self,
        run_or_queue_id: str,
        *,
        principal: RuntimeApiPrincipal,
    ) -> Mapping[str, Any]:
        queue_item = self._queue_item_for_run_or_queue_id(run_or_queue_id)
        self._assert_queue_tenant(queue_item, principal)
        retry = RuntimeQueueManager(store=self.store, artifacts=self.artifacts).retry(
            str(queue_item["id"])
        )
        return {
            "contract_version": "0.1.0",
            "kind": "start_run_response",
            "response_mode": "queued",
            "status": retry["status"],
            "queue_item": self._queue_summary(retry),
            "run": None,
        }

    @staticmethod
    def _queue_summary(queue_item: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": queue_item["id"],
            "task_id": queue_item["task_id"],
            "tenant_id": queue_item["tenant_id"],
            "area_id": queue_item["area_id"],
            "status": queue_item["status"],
            "scheduled_at": queue_item["scheduled_at"],
            "attempts": queue_item["attempts"],
            "max_attempts": queue_item["max_attempts"],
            "run_id": queue_item.get("run_id"),
        }

    @staticmethod
    def _run_summary(run: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": run["id"],
            "task_id": run["task_id"],
            "profile_id": run["profile_id"],
            "profile_version": run["profile_version"],
            "status": run["status"],
            "stop_reason": run["stop_reason"],
            "started_at": run["started_at"],
            "completed_at": run["completed_at"],
            "artifact_root_uri": run["artifact_root_uri"],
            "token_budget_total": run["token_budget_total"],
            "tokens_used_total": run["tokens_used_total"],
        }

    def _queue_item_for_run_or_queue_id(self, value: str) -> Mapping[str, Any]:
        item = self.store.get_runtime_queue_item(value)
        if item is not None:
            return item
        recordset = self.store.as_runtime_plane_recordset()
        queue_items = recordset.get("records", {}).get("runtime_queue_items", [])
        if isinstance(queue_items, list):
            for candidate in queue_items:
                if isinstance(candidate, Mapping) and candidate.get("run_id") == value:
                    return candidate
        raise RuntimeApiError("Runtime queue item was not found.")

    def _assert_task_tenant(
        self,
        task: Mapping[str, Any],
        principal: RuntimeApiPrincipal,
    ) -> None:
        auth = task.get("context", {})
        auth = auth.get("auth", {}) if isinstance(auth, Mapping) else {}
        tenant_id = auth.get("tenant_id") if isinstance(auth, Mapping) else None
        area_id = auth.get("area_id") if isinstance(auth, Mapping) else None
        if tenant_id != principal.tenant_id or area_id != principal.area_id:
            raise RuntimeApiError("Runtime API task tenant scope does not match principal.")

    def _assert_run_tenant(self, run_id: str, principal: RuntimeApiPrincipal) -> None:
        recordset = self.store.as_runtime_plane_recordset()
        queue_items = recordset.get("records", {}).get("runtime_queue_items", [])
        if isinstance(queue_items, list):
            for item in queue_items:
                if (
                    isinstance(item, Mapping)
                    and item.get("run_id") == run_id
                    and item.get("tenant_id") == principal.tenant_id
                    and item.get("area_id") == principal.area_id
                ):
                    return
        raise RuntimeApiError("Runtime API read was denied by tenant scope.")

    @staticmethod
    def _assert_queue_tenant(
        queue_item: Mapping[str, Any],
        principal: RuntimeApiPrincipal,
    ) -> None:
        if queue_item.get("tenant_id") != principal.tenant_id:
            raise RuntimeApiError("Runtime API queue access was denied by tenant scope.")
        if queue_item.get("area_id") != principal.area_id:
            raise RuntimeApiError("Runtime API queue access was denied by area scope.")
