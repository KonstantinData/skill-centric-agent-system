from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from skill_centric_agent_system.runtime.artifacts import JsonArtifactStore
from skill_centric_agent_system.runtime.flight_recorder import FlightRecorder
from skill_centric_agent_system.runtime.models import iso_timestamp, slug_id, utc_now
from skill_centric_agent_system.runtime.storage_protocol import RuntimeStore


class RuntimeQuotaError(RuntimeError):
    """Raised when a run cannot reserve tenant quota."""

    def __init__(self, message: str, *, stop_reason: str) -> None:
        super().__init__(message)
        self.stop_reason = stop_reason


@dataclass(frozen=True)
class RuntimeQuotaConfig:
    tenant_token_limits_per_minute: Mapping[str, int] = field(default_factory=dict)
    tenant_tool_call_limits_per_minute: Mapping[str, int] = field(default_factory=dict)


class RuntimeQuotaManager:
    """Reserve and finalize tenant-scoped runtime quota."""

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

    def reserve(
        self,
        *,
        queue_id: str,
        run_id: str,
        tenant_id: str,
        profile: Mapping[str, Any],
        config: RuntimeQuotaConfig,
    ) -> Mapping[str, Any]:
        limits = profile.get("limits", {})
        reserved_tokens = int(limits.get("max_tokens", 0)) if isinstance(limits, Mapping) else 0
        reserved_tool_calls = (
            int(limits.get("max_tool_calls", 0)) if isinstance(limits, Mapping) else 0
        )
        quota_window = iso_timestamp(self.clock())[:16]
        self._assert_within_limit(
            tenant_id=tenant_id,
            quota_window=quota_window,
            field="reserved_tokens",
            requested=reserved_tokens,
            limit=config.tenant_token_limits_per_minute.get(tenant_id),
            run_id=run_id,
            stop_reason="max_tokens",
        )
        self._assert_within_limit(
            tenant_id=tenant_id,
            quota_window=quota_window,
            field="reserved_tool_calls",
            requested=reserved_tool_calls,
            limit=config.tenant_tool_call_limits_per_minute.get(tenant_id),
            run_id=run_id,
            stop_reason="max_tool_calls",
        )
        reservation_id = slug_id(f"{queue_id}-{run_id}-{quota_window}", prefix="quota")
        return self.store.insert_runtime_quota_reservation(
            {
                "id": reservation_id,
                "queue_id": queue_id,
                "run_id": run_id,
                "tenant_id": tenant_id,
                "quota_window": quota_window,
                "reserved_tokens": reserved_tokens,
                "reserved_tool_calls": reserved_tool_calls,
                "status": "reserved",
                "created_at": iso_timestamp(self.clock()),
                "finalized_at": None,
            }
        )

    def finalize(self, reservation_id: str) -> Mapping[str, Any]:
        return self.store.update_runtime_quota_reservation(
            reservation_id,
            {
                "status": "finalized",
                "finalized_at": iso_timestamp(self.clock()),
            },
        )

    def refund(self, reservation_id: str) -> Mapping[str, Any]:
        return self.store.update_runtime_quota_reservation(
            reservation_id,
            {
                "status": "refunded",
                "finalized_at": iso_timestamp(self.clock()),
            },
        )

    def _assert_within_limit(
        self,
        *,
        tenant_id: str,
        quota_window: str,
        field: str,
        requested: int,
        limit: int | None,
        run_id: str,
        stop_reason: str,
    ) -> None:
        if limit is None:
            return
        used = 0
        recordset = self.store.as_runtime_plane_recordset()
        reservations = recordset.get("records", {}).get("runtime_quota_reservations", [])
        if isinstance(reservations, list):
            used = sum(
                int(reservation.get(field, 0))
                for reservation in reservations
                if isinstance(reservation, Mapping)
                and reservation.get("tenant_id") == tenant_id
                and reservation.get("quota_window") == quota_window
                and reservation.get("status") == "reserved"
            )
        if used + requested <= limit:
            return

        FlightRecorder(self.store, self.artifacts, clock=self.clock).record_event(
            run_id=run_id,
            event_type="quota_exhausted",
            actor_role="quota_manager",
            result={
                "tenant_id": tenant_id,
                "quota_window": quota_window,
                "field": field,
                "requested": requested,
                "used": used,
                "limit": limit,
            },
            stop_reason=stop_reason,  # type: ignore[arg-type]
        )
        raise RuntimeQuotaError("Tenant runtime quota exceeded.", stop_reason=stop_reason)
