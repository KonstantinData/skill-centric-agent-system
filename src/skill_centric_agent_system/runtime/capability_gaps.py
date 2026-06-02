from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from skill_centric_agent_system.runtime.artifacts import JsonArtifactStore
from skill_centric_agent_system.runtime.enforcement import ProfileEnforcementError
from skill_centric_agent_system.runtime.models import StopReason, slug_id

CapabilityKind = Literal[
    "tool",
    "policy",
    "data_scope",
    "knowledge_scope",
    "memory_scope",
    "budget",
    "validator",
    "module_version",
]

ELIGIBLE_BLOCKING_PREDICATES = frozenset(
    {
        "tool_not_in_runtime_profile",
        "tool_risk_exceeds_profile",
        "policy_not_in_runtime_profile",
        "data_scope_not_in_runtime_profile",
        "knowledge_scope_not_in_runtime_profile",
        "memory_scope_not_in_runtime_profile",
        "max_tool_calls_exceeded",
        "max_tokens_exceeded",
        "max_data_reads_exceeded",
        "max_memory_ops_exceeded",
        "max_recompositions_exceeded",
        "validator_failed",
        "selected_module_version_missing",
        "module_version_mismatch",
    }
)
EXCLUDED_BLOCKING_PREDICATES = frozenset(
    {
        "secret_candidate",
        "secret_scope_requested",
        "unknown_tool",
    }
)
STOP_REASONS = frozenset(
    {
        "policy_denied",
        "max_tokens",
        "max_tool_calls",
        "max_data_reads",
        "max_memory_ops",
        "max_recompositions",
        "validator_failed",
    }
)


class CapabilityGapCandidateError(ValueError):
    """Raised when a capability-gap candidate cannot be captured safely."""


@dataclass(frozen=True)
class CapabilityGapCaptureResult:
    candidate: Mapping[str, Any] | None
    artifact_uri: str | None
    skipped_reason: str | None = None

    @property
    def captured(self) -> bool:
        return self.candidate is not None and self.artifact_uri is not None


def capture_capability_gap_candidate(
    *,
    artifacts: JsonArtifactStore,
    run_id: str,
    profile_id: str,
    source_step_id: str,
    blocking_predicate: str,
    requested_capability_kind: CapabilityKind,
    requested_capability_id: str,
    stop_reason: StopReason,
    evidence_uris: Iterable[str],
    known_capability_ids: Iterable[str] = (),
    sensitivity: str = "internal",
) -> CapabilityGapCaptureResult:
    candidate = build_capability_gap_candidate(
        run_id=run_id,
        profile_id=profile_id,
        source_step_id=source_step_id,
        blocking_predicate=blocking_predicate,
        requested_capability_kind=requested_capability_kind,
        requested_capability_id=requested_capability_id,
        stop_reason=stop_reason,
        evidence_uris=evidence_uris,
        known_capability_ids=known_capability_ids,
        sensitivity=sensitivity,
    )
    if candidate is None:
        return CapabilityGapCaptureResult(
            candidate=None,
            artifact_uri=None,
            skipped_reason="denial is not eligible for capability-gap learning",
        )

    artifact_uri = artifacts.write_json(
        ("artifacts", run_id, "capability-gap-candidates", str(candidate["id"])),
        candidate,
        redact=True,
    )
    return CapabilityGapCaptureResult(candidate=candidate, artifact_uri=artifact_uri)


def build_capability_gap_candidate(
    *,
    run_id: str,
    profile_id: str,
    source_step_id: str,
    blocking_predicate: str,
    requested_capability_kind: CapabilityKind,
    requested_capability_id: str,
    stop_reason: StopReason,
    evidence_uris: Iterable[str],
    known_capability_ids: Iterable[str] = (),
    sensitivity: str = "internal",
) -> dict[str, Any] | None:
    normalized_capability_id = slug_id(requested_capability_id)
    if not _is_eligible_denial(
        blocking_predicate=blocking_predicate,
        requested_capability_kind=requested_capability_kind,
        requested_capability_id=normalized_capability_id,
        known_capability_ids=known_capability_ids,
        sensitivity=sensitivity,
    ):
        return None

    candidate = {
        "contract_version": "0.1.0",
        "candidate_kind": "capability_gap_candidate",
        "id": slug_id(
            f"{run_id}-{source_step_id}-{blocking_predicate}-{normalized_capability_id}",
            prefix="cgc",
        ),
        "source_run_id": slug_id(run_id),
        "source_profile_id": slug_id(profile_id),
        "source_step_id": slug_id(source_step_id),
        "blocking_predicate": blocking_predicate,
        "requested_capability": {
            "kind": requested_capability_kind,
            "id": normalized_capability_id,
        },
        "stop_reason": stop_reason,
        "evidence_uris": sorted({uri for uri in evidence_uris if uri}),
        "learning_status": "review_required",
        "executable": False,
    }
    validate_capability_gap_candidate(candidate)
    return candidate


def capability_gap_from_enforcement_error(
    *,
    artifacts: JsonArtifactStore,
    run_id: str,
    profile: Mapping[str, Any],
    source_step_id: str,
    requested_tool: str,
    error: ProfileEnforcementError,
    evidence_uris: Iterable[str],
    known_tool_ids: Iterable[str],
) -> CapabilityGapCaptureResult:
    return capture_capability_gap_candidate(
        artifacts=artifacts,
        run_id=run_id,
        profile_id=str(profile.get("id", "unknown-profile")),
        source_step_id=source_step_id,
        blocking_predicate=error.code,
        requested_capability_kind=_capability_kind_for_predicate(error.code),
        requested_capability_id=_capability_id_for_predicate(error.code, requested_tool),
        stop_reason=error.stop_reason,
        evidence_uris=evidence_uris,
        known_capability_ids=known_tool_ids,
    )


def validate_capability_gap_candidate(candidate: Mapping[str, Any]) -> None:
    required_fields = {
        "contract_version",
        "candidate_kind",
        "id",
        "source_run_id",
        "source_profile_id",
        "source_step_id",
        "blocking_predicate",
        "requested_capability",
        "stop_reason",
        "evidence_uris",
        "learning_status",
        "executable",
    }
    missing = sorted(field for field in required_fields if field not in candidate)
    if missing:
        raise CapabilityGapCandidateError("missing fields: " + ", ".join(missing))
    if candidate["contract_version"] != "0.1.0":
        raise CapabilityGapCandidateError("contract_version must be 0.1.0")
    if candidate["candidate_kind"] != "capability_gap_candidate":
        raise CapabilityGapCandidateError("candidate_kind must be capability_gap_candidate")
    if candidate["blocking_predicate"] not in ELIGIBLE_BLOCKING_PREDICATES:
        raise CapabilityGapCandidateError("blocking_predicate is not eligible")
    if candidate["stop_reason"] not in STOP_REASONS:
        raise CapabilityGapCandidateError("stop_reason is not eligible")
    requested_capability = candidate["requested_capability"]
    if not isinstance(requested_capability, Mapping):
        raise CapabilityGapCandidateError("requested_capability must be an object")
    if not requested_capability.get("kind") or not requested_capability.get("id"):
        raise CapabilityGapCandidateError("requested_capability requires kind and id")
    if candidate["learning_status"] != "review_required":
        raise CapabilityGapCandidateError("learning_status must be review_required")
    if candidate["executable"] is not False:
        raise CapabilityGapCandidateError("capability gap candidates must be non-executable")
    evidence_uris = candidate["evidence_uris"]
    if not isinstance(evidence_uris, tuple | list) or not evidence_uris:
        raise CapabilityGapCandidateError("evidence_uris must be non-empty")


def _is_eligible_denial(
    *,
    blocking_predicate: str,
    requested_capability_kind: CapabilityKind,
    requested_capability_id: str,
    known_capability_ids: Iterable[str],
    sensitivity: str,
) -> bool:
    if sensitivity == "secret":
        return False
    if blocking_predicate in EXCLUDED_BLOCKING_PREDICATES:
        return False
    if blocking_predicate not in ELIGIBLE_BLOCKING_PREDICATES:
        return False
    if requested_capability_kind == "tool":
        known = {slug_id(capability_id) for capability_id in known_capability_ids}
        return requested_capability_id in known
    return True


def _capability_kind_for_predicate(predicate: str) -> CapabilityKind:
    if predicate.startswith("max_"):
        return "budget"
    if predicate.startswith("policy_"):
        return "policy"
    if predicate.startswith("data_scope_"):
        return "data_scope"
    if predicate.startswith("knowledge_scope_"):
        return "knowledge_scope"
    if predicate.startswith("memory_scope_"):
        return "memory_scope"
    if "validator" in predicate:
        return "validator"
    if "module_version" in predicate or predicate == "selected_module_version_missing":
        return "module_version"
    return "tool"


def _capability_id_for_predicate(predicate: str, requested_tool: str) -> str:
    if predicate.startswith("max_"):
        return predicate.removesuffix("_exceeded")
    return requested_tool
