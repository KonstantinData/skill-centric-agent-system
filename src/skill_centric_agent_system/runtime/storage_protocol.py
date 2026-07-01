from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class RuntimeStore(Protocol):
    def insert_runtime_queue_item(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def get_runtime_queue_item(self, queue_id: str) -> Mapping[str, Any] | None: ...

    def update_runtime_queue_item(
        self,
        queue_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    def heartbeat_runtime_queue_item(
        self,
        queue_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

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
    ) -> Mapping[str, Any] | None: ...

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
    ) -> Mapping[str, Any] | None: ...

    def recover_stale_runtime_queue_items(self, *, now: str) -> tuple[Mapping[str, Any], ...]: ...

    def insert_runtime_run_attempt(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def update_runtime_run_attempt(
        self,
        attempt_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    def insert_runtime_run_claim(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def update_runtime_run_claim(
        self,
        claim_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    def release_runtime_queue_claims(
        self,
        queue_id: str,
        *,
        released_at: str,
        release_reason: str,
    ) -> tuple[Mapping[str, Any], ...]: ...

    def insert_runtime_dead_letter(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def insert_runtime_quota_reservation(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def update_runtime_quota_reservation(
        self,
        reservation_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    def insert_runtime_run(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def update_runtime_run(self, run_id: str, fields: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def get_runtime_run(self, run_id: str) -> Mapping[str, Any] | None: ...

    def insert_runtime_step(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def update_runtime_step(self, step_id: str, fields: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def allocate_runtime_event_index(self, run_id: str) -> int: ...

    def insert_runtime_event(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def allocate_runtime_checkpoint_index(self, run_id: str) -> int: ...

    def insert_runtime_checkpoint(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def insert_tool_invocation(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def insert_validation_result(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def insert_memory_candidate(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def update_memory_candidate(
        self,
        candidate_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    def events_for_run(self, run_id: str) -> tuple[Mapping[str, Any], ...]: ...

    def checkpoints_for_run(self, run_id: str) -> tuple[Mapping[str, Any], ...]: ...

    def as_runtime_plane_recordset(
        self,
        *,
        contract_version: str = "0.2.0",
        environment: str = "dev",
    ) -> Mapping[str, Any]: ...

