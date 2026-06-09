from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from skill_centric_agent_system.runtime.artifacts import JsonArtifactStore
from skill_centric_agent_system.runtime.models import iso_timestamp, slug_id, utc_now
from skill_centric_agent_system.runtime.safety_compiler import SafetyCompiler
from skill_centric_agent_system.runtime.storage import RuntimeStore

SENSITIVITIES = frozenset({"public", "internal", "confidential", "secret"})
CANDIDATE_CLASSES = frozenset(
    {
        "procedural_lesson",
        "task_subject_fact",
        "runtime_evidence",
        "knowledge_record_proposal",
        "rejected",
    }
)
PROMOTABLE_CANDIDATE_CLASS = "procedural_lesson"
PROMOTION_ROUTES = {
    "procedural_lesson": "agent_memory",
    "task_subject_fact": "scoped_knowledge_record",
    "runtime_evidence": "runtime_plane_evidence",
    "knowledge_record_proposal": "knowledge_record_approval",
    "rejected": "none",
}


class MemoryCandidateError(ValueError):
    """Raised when a memory candidate cannot be extracted or checked."""


@dataclass(frozen=True)
class MemoryCandidateValidationResult:
    candidate: Mapping[str, Any]
    validator_status: str
    policy_status: str
    validation_reason: str
    policy_reason: str

    @property
    def approved(self) -> bool:
        return self.validator_status == "approved" and self.policy_status == "approved"


class MemoryCandidateExtractor:
    """Extract durable memory candidates from completed runtime steps."""

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

    def extract_from_step(
        self,
        *,
        run: Mapping[str, Any],
        source_step: Mapping[str, Any],
        target_memory_scope_id: str,
        content: Mapping[str, Any],
        sensitivity: str,
        retention_policy: str,
        policy_id: str,
        candidate_class: str = PROMOTABLE_CANDIDATE_CLASS,
        classification_reason: str | None = None,
        validator_id: str = "memory-candidate-contract",
        candidate_id: str | None = None,
        redact_sensitive_data: bool = True,
    ) -> Mapping[str, Any]:
        self._validate_extractable_step(run, source_step)
        if not isinstance(content.get("summary"), str) or not content["summary"]:
            raise MemoryCandidateError("Memory candidate content requires a non-empty summary.")
        if sensitivity not in SENSITIVITIES:
            raise MemoryCandidateError("Memory candidate sensitivity is invalid.")
        if candidate_class not in CANDIDATE_CLASSES:
            raise MemoryCandidateError("Memory candidate class is invalid.")
        resolved_classification_reason = (
            classification_reason
            or f"Candidate classified as {candidate_class} by extraction contract."
        )
        if not resolved_classification_reason.strip():
            raise MemoryCandidateError("Memory candidate classification reason is required.")

        identifier = candidate_id or slug_id(
            f"{run['id']}-{source_step['id']}-{target_memory_scope_id}",
            prefix="mc",
        )
        content_uri = self.artifacts.write_json(
            ("artifacts", str(run["id"]), "memory-candidates", identifier),
            {
                "contract_version": "0.1.0",
                **dict(content),
                "source_run_id": run["id"],
                "source_profile_id": run["profile_id"],
                "source_step_id": source_step["id"],
                "target_memory_scope_id": target_memory_scope_id,
                "candidate_class": candidate_class,
                "classification_reason": resolved_classification_reason,
                "promotion_route": PROMOTION_ROUTES[candidate_class],
                "sensitivity": sensitivity,
                "retention_policy": retention_policy,
                "policy_id": policy_id,
                "validator_id": validator_id,
            },
            redact=redact_sensitive_data,
        )
        record = {
            "id": identifier,
            "run_id": str(run["id"]),
            "profile_id": str(run["profile_id"]),
            "source_step_id": str(source_step["id"]),
            "target_memory_scope_id": target_memory_scope_id,
            "candidate_class": candidate_class,
            "classification_reason": resolved_classification_reason,
            "content_uri": content_uri,
            "sensitivity": sensitivity,
            "retention_policy": retention_policy,
            "validator_status": "pending",
            "validator_id": validator_id,
            "validation_reason": None,
            "policy_status": "pending",
            "policy_id": policy_id,
            "policy_reason": None,
            "created_at": iso_timestamp(self.clock()),
        }
        return self.store.insert_memory_candidate(record)

    @staticmethod
    def _validate_extractable_step(
        run: Mapping[str, Any],
        source_step: Mapping[str, Any],
    ) -> None:
        if source_step.get("run_id") != run.get("id"):
            raise MemoryCandidateError("Memory candidate source step must belong to the run.")
        if source_step.get("status") != "succeeded":
            raise MemoryCandidateError(
                "Memory candidates can only be extracted from completed steps."
            )


class MemoryCandidateValidator:
    """Approve or reject memory candidates before Cloudflare ingestion."""

    def __init__(
        self,
        *,
        store: RuntimeStore,
        allowed_memory_scope_ids: Iterable[str],
        allowed_policy_ids: Iterable[str],
        safety_compiler: SafetyCompiler | None = None,
    ) -> None:
        self.store = store
        self.allowed_memory_scope_ids = frozenset(allowed_memory_scope_ids)
        self.allowed_policy_ids = frozenset(allowed_policy_ids)
        self.safety_compiler = safety_compiler

    def validate(
        self,
        candidate: Mapping[str, Any],
        *,
        content: Mapping[str, Any] | None = None,
    ) -> MemoryCandidateValidationResult:
        validation_errors = self._validation_errors(candidate, content)
        policy_errors = self._policy_errors(candidate, content)

        validator_status = "rejected" if validation_errors else "approved"
        policy_status = "rejected" if policy_errors or validation_errors else "approved"
        validation_reason = (
            "; ".join(validation_errors)
            if validation_errors
            else "Candidate has provenance, scoped memory target, and acceptable sensitivity."
        )
        policy_reason = (
            "; ".join(policy_errors)
            if policy_errors
            else "Policy allows the target memory scope for this candidate."
        )
        updated = self.store.update_memory_candidate(
            str(candidate["id"]),
            {
                "validator_status": validator_status,
                "validation_reason": validation_reason,
                "policy_status": policy_status,
                "policy_reason": policy_reason,
            },
        )
        return MemoryCandidateValidationResult(
            candidate=updated,
            validator_status=validator_status,
            policy_status=policy_status,
            validation_reason=validation_reason,
            policy_reason=policy_reason,
        )

    def _validation_errors(
        self,
        candidate: Mapping[str, Any],
        content: Mapping[str, Any] | None,
    ) -> list[str]:
        required_fields = {
            "id",
            "run_id",
            "profile_id",
            "source_step_id",
            "target_memory_scope_id",
            "candidate_class",
            "classification_reason",
            "content_uri",
            "sensitivity",
            "retention_policy",
            "validator_id",
            "policy_id",
        }
        errors = sorted(field for field in required_fields if field not in candidate)
        if candidate.get("sensitivity") == "secret":
            errors.append("secret candidates must not be promoted to Cloudflare memory")
        if candidate.get("sensitivity") not in SENSITIVITIES:
            errors.append("sensitivity is invalid")
        candidate_class = candidate.get("candidate_class")
        if candidate_class not in CANDIDATE_CLASSES:
            errors.append("candidate_class is invalid")
        elif candidate_class != PROMOTABLE_CANDIDATE_CLASS:
            errors.append(_non_promotable_candidate_reason(str(candidate_class)))
        if not str(candidate.get("classification_reason", "")).strip():
            errors.append("classification_reason is required")
        if not str(candidate.get("content_uri", "")).startswith("hetzner://runtime/"):
            errors.append("content_uri must point to a Hetzner runtime artifact")
        if content is not None and not str(content.get("summary", "")).strip():
            errors.append("content summary is required")
        return errors

    def _policy_errors(
        self,
        candidate: Mapping[str, Any],
        content: Mapping[str, Any] | None,
    ) -> list[str]:
        errors: list[str] = []
        if candidate.get("target_memory_scope_id") not in self.allowed_memory_scope_ids:
            errors.append("target memory scope is not allowed")
        if candidate.get("policy_id") not in self.allowed_policy_ids:
            errors.append("policy is not allowed")
        if content is None or self.safety_compiler is None:
            return errors

        learned_prior = content.get("learned_context_authority_prior")
        if not isinstance(learned_prior, Mapping):
            return errors
        reviewed_artifacts = _string_list(content.get("reviewed_policy_artifacts"))
        decision = self.safety_compiler.compile_learned_authority_prior(
            learned_prior,
            reviewed_policy_artifacts=reviewed_artifacts,
        )
        if not decision.automatic_promotion_allowed:
            pair_text = ", ".join(decision.matched_pair_ids) or "none"
            errors.append(
                "semantic drift guard blocked learned authority "
                f"({decision.decision}; matched_pairs={pair_text})"
            )
        return errors


def _string_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _non_promotable_candidate_reason(candidate_class: str) -> str:
    reasons = {
        "task_subject_fact": (
            "task-subject facts must be proposed through scoped knowledge records, "
            "not promoted to Agent Memory"
        ),
        "runtime_evidence": (
            "runtime evidence must remain in the Hetzner Runtime Plane, "
            "not promoted to Agent Memory"
        ),
        "knowledge_record_proposal": (
            "knowledge record proposals require the knowledge approval path, "
            "not Agent Memory promotion"
        ),
        "rejected": "rejected candidates cannot be promoted to Agent Memory",
    }
    return reasons.get(candidate_class, "candidate_class is not promotable to Agent Memory")
