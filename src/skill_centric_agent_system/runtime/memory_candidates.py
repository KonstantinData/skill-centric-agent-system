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
REFLECTION_REJECTION_KEYS = frozenset(
    {
        "raw_tool_output",
        "raw_tool_outputs",
        "source_extract",
        "source_extracts",
        "customer_data",
        "private_data",
        "secret_value",
        "credential",
    }
)
SECRET_LIKE_TERMS = (
    "api key",
    "apikey",
    "password",
    "private key",
    "secret",
    "token",
)
PROCEDURAL_ALLOWED_EFFECTS = frozenset(
    {
        "planner_hint",
        "retrieval_ranking",
        "composer_candidate_bias",
    }
)
PROCEDURAL_REQUIRED_FORBIDDEN_EFFECTS = frozenset(
    {
        "tool_grant",
        "scope_grant",
        "policy_override",
        "validator_override",
        "profile_mutation",
        "runtime_authority",
    }
)
TASK_SUBJECT_CONTENT_KEYS = frozenset(
    {
        "task_subject_fact",
        "task_subject_facts",
        "factual_claim",
        "factual_claims",
        "subject_data",
        "subject_facts",
        "customer_record",
        "customer_records",
    }
)
AUTHORITY_LANGUAGE_TERMS = (
    "grant tool",
    "grant tools",
    "allow tool",
    "allow tools",
    "increase budget",
    "raise budget",
    "override policy",
    "override validator",
    "disable validator",
    "remove validator",
    "relax policy",
    "ignore policy",
    "expand scope",
    "widen scope",
    "profile mutation",
    "runtime authority",
)
TASK_SUBJECT_LANGUAGE_TERMS = (
    "customer record",
    "customer-specific",
    "client record",
    "private data",
    "source extract",
    "raw tool output",
)


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


class PostRunReflectionExtractor:
    """Emit classified post-run memory envelopes without direct memory admission."""

    def __init__(
        self,
        *,
        artifacts: JsonArtifactStore,
        clock: Callable[[], Any] = utc_now,
    ) -> None:
        self.artifacts = artifacts
        self.clock = clock

    def emit_candidate_envelope(
        self,
        *,
        run: Mapping[str, Any],
        source_step: Mapping[str, Any],
        target_memory_scope_id: str,
        content: Mapping[str, Any],
        sensitivity: str,
        retention_policy: str,
        policy_id: str,
        candidate_class: str,
        classification_reason: str,
        validator_id: str = "memory-candidate-contract",
        candidate_id: str | None = None,
        redact_sensitive_data: bool = True,
    ) -> Mapping[str, Any]:
        MemoryCandidateExtractor._validate_extractable_step(run, source_step)
        self._validate_reflection_request(
            content=content,
            sensitivity=sensitivity,
            candidate_class=candidate_class,
            classification_reason=classification_reason,
        )

        resolved_class = self._resolved_candidate_class(
            requested_class=candidate_class,
            content=content,
            sensitivity=sensitivity,
        )
        resolved_reason = classification_reason
        if resolved_class == "rejected" and candidate_class != "rejected":
            resolved_reason = (
                f"{classification_reason} Rejected by post-run reflection safety precheck."
            )
        identifier = candidate_id or slug_id(
            f"{run['id']}-{source_step['id']}-{target_memory_scope_id}-reflection",
            prefix="mce",
        )
        envelope = {
            "contract_version": "0.1.0",
            **dict(content),
            "source_run_id": run["id"],
            "source_profile_id": run["profile_id"],
            "source_step_id": source_step["id"],
            "target_memory_scope_id": target_memory_scope_id,
            "candidate_class": resolved_class,
            "classification_reason": resolved_reason,
            "promotion_route": PROMOTION_ROUTES[resolved_class],
            "sensitivity": sensitivity,
            "retention_policy": retention_policy,
            "policy_id": policy_id,
            "validator_id": validator_id,
            "created_at": iso_timestamp(self.clock()),
        }
        envelope_uri = self.artifacts.write_json(
            ("artifacts", str(run["id"]), "memory-reflection-candidates", identifier),
            envelope,
            redact=redact_sensitive_data,
        )
        return {
            "id": identifier,
            "run_id": str(run["id"]),
            "profile_id": str(run["profile_id"]),
            "source_step_id": str(source_step["id"]),
            "target_memory_scope_id": target_memory_scope_id,
            "candidate_class": resolved_class,
            "classification_reason": resolved_reason,
            "promotion_route": PROMOTION_ROUTES[resolved_class],
            "envelope_uri": envelope_uri,
            "created_at": envelope["created_at"],
        }

    @staticmethod
    def _validate_reflection_request(
        *,
        content: Mapping[str, Any],
        sensitivity: str,
        candidate_class: str,
        classification_reason: str,
    ) -> None:
        if not isinstance(content.get("summary"), str) or not content["summary"]:
            raise MemoryCandidateError("Reflection envelope requires a non-empty summary.")
        evidence_uris = content.get("evidence_uris")
        if not isinstance(evidence_uris, list) or not evidence_uris:
            raise MemoryCandidateError("Reflection envelope requires evidence_uris.")
        if any(not str(uri).startswith("hetzner://runtime/") for uri in evidence_uris):
            raise MemoryCandidateError(
                "Reflection envelope evidence_uris must point to Hetzner runtime artifacts."
            )
        if sensitivity not in SENSITIVITIES:
            raise MemoryCandidateError("Reflection envelope sensitivity is invalid.")
        if candidate_class not in CANDIDATE_CLASSES:
            raise MemoryCandidateError("Reflection envelope candidate_class is invalid.")
        if not classification_reason.strip():
            raise MemoryCandidateError("Reflection envelope classification_reason is required.")

    @staticmethod
    def _resolved_candidate_class(
        *,
        requested_class: str,
        content: Mapping[str, Any],
        sensitivity: str,
    ) -> str:
        if requested_class == "rejected" or sensitivity == "secret":
            return "rejected"
        if REFLECTION_REJECTION_KEYS.intersection(content):
            return "rejected"
        summary = str(content.get("summary", "")).lower()
        if any(term in summary for term in SECRET_LIKE_TERMS):
            return "rejected"
        return requested_class


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
        if (
            candidate_class == PROMOTABLE_CANDIDATE_CLASS
            and content is not None
        ):
            errors.extend(_procedural_content_errors(content))
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


def _procedural_content_errors(content: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = str(content.get("summary", "")).strip()
    summary_lower = summary.lower()

    if not _non_empty_string_list(content.get("applicability")):
        errors.append("procedural lessons require applicability metadata")
    evidence_uris = _non_empty_string_list(content.get("evidence_uris"))
    if not evidence_uris or any(
        not uri.startswith("hetzner://runtime/") for uri in evidence_uris
    ):
        errors.append("procedural lessons require Hetzner evidence_uris")
    if content.get("authoritative") is not False:
        errors.append("procedural lessons must set authoritative=false")

    influence_class = content.get("influence_class")
    if influence_class not in PROCEDURAL_ALLOWED_EFFECTS:
        errors.append("procedural lesson influence_class is invalid")

    allowed_effects = _string_set(content.get("allowed_effects"))
    if not allowed_effects:
        errors.append("procedural lessons require allowed_effects")
    elif not allowed_effects <= PROCEDURAL_ALLOWED_EFFECTS:
        errors.append("procedural lesson allowed_effects include authority effects")

    forbidden_effects = _string_set(content.get("forbidden_effects"))
    missing_forbidden = PROCEDURAL_REQUIRED_FORBIDDEN_EFFECTS - forbidden_effects
    if missing_forbidden:
        errors.append(
            "procedural lessons must forbid authority effects: "
            + ", ".join(sorted(missing_forbidden))
        )

    blocked_keys = (
        REFLECTION_REJECTION_KEYS
        | TASK_SUBJECT_CONTENT_KEYS
    ).intersection(content)
    if blocked_keys:
        errors.append(
            "procedural lessons must not contain raw, source, customer, private, "
            "secret, or task-subject fields: "
            + ", ".join(sorted(blocked_keys))
        )
    if any(term in summary_lower for term in SECRET_LIKE_TERMS):
        errors.append("procedural lessons must not contain secret-like values")
    if any(term in summary_lower for term in TASK_SUBJECT_LANGUAGE_TERMS):
        errors.append("procedural lessons must not contain task-subject content")
    if any(term in summary_lower for term in AUTHORITY_LANGUAGE_TERMS):
        errors.append("procedural lessons must not contain authority-changing language")
    if content.get("applies_to_all_tasks") is True:
        errors.append("procedural lessons must not generalize to all tasks")
    if str(content.get("generalization_scope", "")).lower() in {"global", "all"}:
        errors.append("procedural lessons must not use unsafe generalization scope")
    return errors


def _non_empty_string_list(value: Any) -> tuple[str, ...]:
    items = _string_list(value)
    return tuple(item for item in items if item.strip())


def _string_set(value: Any) -> frozenset[str]:
    return frozenset(_non_empty_string_list(value))


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
