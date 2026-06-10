from __future__ import annotations

from collections.abc import Mapping
from typing import Any

CONTRACT_VERSION = "0.1.0"


class MemoryOperationsEvidenceError(ValueError):
    """Raised when memory operations evidence cannot be evaluated safely."""


def evaluate_memory_operations_evidence(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate aggregate memory-operations evidence without raw runtime traces."""

    gates = {
        "live_smoke": _live_smoke_gate(_required_mapping(snapshot, "live_smoke")),
        "taxonomy_metrics": _taxonomy_metrics_gate(
            _required_mapping(snapshot, "aggregate_metrics")
        ),
        "retention_separation": _retention_separation_gate(
            _required_mapping(snapshot, "retention_separation")
        ),
        "renderer_behavior": _renderer_behavior_gate(
            _required_mapping(snapshot, "renderer_behavior")
        ),
        "denial_ledger": _zero_count_gate(
            _required_mapping(snapshot, "denial_ledger"),
            field="authority_grant_count",
            gate_id="denial_ledger",
        ),
        "relationship_graph": _zero_count_gate(
            _required_mapping(snapshot, "relationship_graph"),
            field="authority_delta_count",
            gate_id="relationship_graph",
        ),
    }
    failed = [gate_id for gate_id, gate in gates.items() if gate["status"] != "passed"]
    return {
        "contract_version": CONTRACT_VERSION,
        "environment": _required_string(snapshot, "environment"),
        "evaluated_snapshot_id": _required_string(snapshot, "snapshot_id"),
        "status": "passed" if not failed else "failed",
        "failed_gates": failed,
        "gates": gates,
        "raw_data_policy": "aggregate_metadata_only",
    }


def _live_smoke_gate(smoke: Mapping[str, Any]) -> dict[str, Any]:
    passed = (
        smoke.get("status") == "passed"
        and smoke.get("procedural_lesson_created") is True
        and smoke.get("knowledge_proposal_created") is True
        and str(smoke.get("same_run_evidence_uri", "")).startswith("hetzner://runtime/")
    )
    return {
        "status": "passed" if passed else "failed",
        "message": (
            "Live smoke created one procedural lesson and one knowledge proposal "
            "from the same Hetzner run evidence."
            if passed
            else "Live smoke evidence is incomplete."
        ),
    }


def _taxonomy_metrics_gate(metrics: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    if _count(metrics, "contrastive_false_negative_count") != 0:
        failures.append("contrastive false negatives must be zero")
    if _count(metrics, "contrastive_false_positive_count") != 0:
        failures.append("contrastive false positives must be zero")
    if _float(metrics, "abstention_review_rate") > 0.25:
        failures.append("abstention/review rate exceeds threshold")
    if _count(metrics, "post_planning_invariant_violation_count") != 0:
        failures.append("post-planning invariant violations must be zero")
    if _float(metrics, "retrieval_cache_hit_rate") < 0.5:
        failures.append("retrieval cache hit rate is below threshold")
    if _float(metrics, "top_k_memory_load_p95") > 20:
        failures.append("Top-K memory load p95 exceeds threshold")
    candidate_class_counts = _required_mapping(metrics, "candidate_class_counts")
    if _count(candidate_class_counts, "procedural_lesson") < 1:
        failures.append("procedural lesson candidates must be observed")
    if _count(candidate_class_counts, "knowledge_record_proposal") < 1:
        failures.append("knowledge proposal candidates must be observed")
    return {
        "status": "passed" if not failures else "failed",
        "failures": failures,
    }


def _retention_separation_gate(retention: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    if retention.get("runtime_evidence_cleanup_status") != "passed":
        failures.append("runtime evidence cleanup did not pass")
    if retention.get("knowledge_memory_retention_independent") is not True:
        failures.append("knowledge/memory retention must be independent")
    if retention.get("cloudflare_memory_deleted_by_runtime_cleanup") is not False:
        failures.append("runtime cleanup must not delete Cloudflare memory")
    return {"status": "passed" if not failures else "failed", "failures": failures}


def _renderer_behavior_gate(renderer: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    if _count(renderer, "authoritative_record_count") != 0:
        failures.append("rendered memory must not be authoritative")
    if _count(renderer, "instruction_record_count") != 0:
        failures.append("rendered memory must not become instructions")
    if _count(renderer, "memory_context_record_count") < 1:
        failures.append("memory context records must be observed")
    return {"status": "passed" if not failures else "failed", "failures": failures}


def _zero_count_gate(data: Mapping[str, Any], *, field: str, gate_id: str) -> dict[str, Any]:
    value = _count(data, field)
    return {
        "status": "passed" if value == 0 else "failed",
        "failures": [] if value == 0 else [f"{gate_id}.{field} must be zero"],
    }


def _required_mapping(data: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    value = data.get(field)
    if not isinstance(value, Mapping):
        raise MemoryOperationsEvidenceError(f"Memory evidence requires object field: {field}")
    return value


def _required_string(data: Mapping[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value:
        raise MemoryOperationsEvidenceError(f"Memory evidence requires string field: {field}")
    return value


def _count(data: Mapping[str, Any], field: str) -> int:
    value = data.get(field)
    if not isinstance(value, int):
        raise MemoryOperationsEvidenceError(f"Memory evidence requires integer field: {field}")
    return value


def _float(data: Mapping[str, Any], field: str) -> float:
    value = data.get(field)
    if not isinstance(value, int | float):
        raise MemoryOperationsEvidenceError(f"Memory evidence requires numeric field: {field}")
    return float(value)
