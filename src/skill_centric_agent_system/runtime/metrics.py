from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import Any


def runtime_queue_metrics(recordset: Mapping[str, Any]) -> dict[str, Any]:
    records = recordset.get("records", {})
    records = records if isinstance(records, Mapping) else {}
    queue_items = _records(records, "runtime_queue_items")
    run_claims = _records(records, "runtime_run_claims")
    dead_letters = _records(records, "runtime_dead_letters")
    events = _records(records, "runtime_events")

    queue_depth_by_tenant_status: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    claim_latency_seconds: list[float] = []
    run_duration_seconds: list[float] = []
    retry_scheduled = 0
    for item in queue_items:
        tenant_id = str(item.get("tenant_id") or "unknown")
        status = str(item.get("status") or "unknown")
        queue_depth_by_tenant_status[tenant_id][status] += 1
        if status == "retry_scheduled":
            retry_scheduled += 1
        claim_latency = _seconds_between(item.get("created_at"), item.get("claimed_at"))
        if claim_latency is not None:
            claim_latency_seconds.append(claim_latency)
        duration = _seconds_between(item.get("claimed_at"), item.get("updated_at"))
        if duration is not None and status in {"succeeded", "failed", "cancelled", "dead_lettered"}:
            run_duration_seconds.append(duration)

    active_claims_by_tenant: dict[str, int] = defaultdict(int)
    for claim in run_claims:
        if claim.get("released_at") is None:
            active_claims_by_tenant[str(claim.get("tenant_id") or "unknown")] += 1

    dead_letters_by_tenant: dict[str, int] = defaultdict(int)
    for dead_letter in dead_letters:
        dead_letters_by_tenant[str(dead_letter.get("tenant_id") or "unknown")] += 1

    event_counts = _event_counts(events)
    return {
        "queue_depth_by_tenant_status": _plain_nested_counts(queue_depth_by_tenant_status),
        "active_claims_by_tenant": dict(sorted(active_claims_by_tenant.items())),
        "dead_letters_by_tenant": dict(sorted(dead_letters_by_tenant.items())),
        "retry_scheduled_count": retry_scheduled,
        "quota_exhaustion_count": event_counts.get("quota_exhausted", 0),
        "policy_denial_count": event_counts.get("policy_denied", 0),
        "claim_latency_seconds": _distribution(claim_latency_seconds),
        "run_duration_seconds": _distribution(run_duration_seconds),
    }


def _records(records: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    values = records.get(key, [])
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, Mapping)]


def _event_counts(events: list[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for event in events:
        counts[str(event.get("event_type") or "unknown")] += 1
    return dict(counts)


def _distribution(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "max": None, "avg": None}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values),
    }


def _seconds_between(start: Any, end: Any) -> float | None:
    if not isinstance(start, str) or not isinstance(end, str):
        return None
    from datetime import datetime

    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max((end_dt - start_dt).total_seconds(), 0.0)


def _plain_nested_counts(values: Mapping[str, Mapping[str, int]]) -> dict[str, dict[str, int]]:
    return {
        key: dict(sorted(nested.items()))
        for key, nested in sorted(values.items())
    }
