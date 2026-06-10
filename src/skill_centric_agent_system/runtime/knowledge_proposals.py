from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from skill_centric_agent_system.runtime.artifacts import JsonArtifactStore
from skill_centric_agent_system.runtime.memory_candidates import SENSITIVITIES
from skill_centric_agent_system.runtime.models import iso_timestamp, slug_id, utc_now

SOURCE_TYPES = frozenset({"repo", "notion", "r2", "url", "manual"})
CONFIDENCE_TIERS = frozenset({"low", "medium", "high", "verified"})


class KnowledgeRecordProposalError(ValueError):
    """Raised when factual task-subject content cannot be proposed as Knowledge."""


@dataclass(frozen=True)
class KnowledgeRecordProposalValidationResult:
    proposal: Mapping[str, Any]
    validator_status: str
    validation_reason: str

    @property
    def approved(self) -> bool:
        return self.validator_status == "approved"


class KnowledgeRecordProposalBuilder:
    """Create scoped Knowledge Record proposals from completed runtime evidence."""

    def __init__(
        self,
        *,
        artifacts: JsonArtifactStore,
        clock: Callable[[], Any] = utc_now,
    ) -> None:
        self.artifacts = artifacts
        self.clock = clock

    def propose_from_step(
        self,
        *,
        run: Mapping[str, Any],
        source_step: Mapping[str, Any],
        source: Mapping[str, Any],
        document: Mapping[str, Any],
        evidence_uris: Iterable[str],
        freshness_review_days: int,
        confidence_tier: str,
        validation_rules: Iterable[str],
        retention_policy: str,
        proposal_id: str | None = None,
        redact_sensitive_data: bool = True,
    ) -> Mapping[str, Any]:
        _validate_completed_step(run, source_step)

        identifier = proposal_id or slug_id(
            f"{run['id']}-{source_step['id']}-{document.get('id', 'knowledge')}",
            prefix="krp",
        )
        proposal = {
            "contract_version": "0.1.0",
            "proposal_id": identifier,
            "source_run_id": str(run["id"]),
            "source_profile_id": str(run["profile_id"]),
            "source_step_id": str(source_step["id"]),
            "source": dict(source),
            "document": dict(document),
            "evidence_uris": list(evidence_uris),
            "freshness_review_days": freshness_review_days,
            "confidence_tier": confidence_tier,
            "validation_rules": list(validation_rules),
            "retention_policy": retention_policy,
            "candidate_class": "knowledge_record_proposal",
            "promotion_route": "knowledge_record_approval",
            "validator_status": "pending",
            "validation_reason": None,
            "created_at": iso_timestamp(self.clock()),
        }
        validation = KnowledgeRecordProposalValidator(
            allowed_knowledge_scope_ids={str(document.get("scope_id", ""))},
        ).validate(proposal)
        proposal = {
            **proposal,
            "validator_status": validation.validator_status,
            "validation_reason": validation.validation_reason,
        }
        proposal_uri = self.artifacts.write_json(
            ("artifacts", str(run["id"]), "knowledge-record-proposals", identifier),
            proposal,
            redact=redact_sensitive_data,
        )
        return {
            **proposal,
            "proposal_uri": proposal_uri,
        }


class KnowledgeRecordProposalValidator:
    """Fail closed unless a factual Knowledge proposal has quality metadata."""

    def __init__(self, *, allowed_knowledge_scope_ids: Iterable[str]) -> None:
        self.allowed_knowledge_scope_ids = frozenset(allowed_knowledge_scope_ids)

    def validate(
        self,
        proposal: Mapping[str, Any],
    ) -> KnowledgeRecordProposalValidationResult:
        errors = _proposal_errors(proposal, self.allowed_knowledge_scope_ids)
        return KnowledgeRecordProposalValidationResult(
            proposal=proposal,
            validator_status="rejected" if errors else "approved",
            validation_reason=(
                "; ".join(errors)
                if errors
                else "Knowledge proposal has source owner, source URI, scope, "
                "freshness, confidence, validation rules, retention, and evidence."
            ),
        )


def knowledge_ingest_request_from_proposal(
    proposal: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Convert an approved proposal into the Control API knowledge ingest body."""

    if proposal.get("validator_status") != "approved":
        raise KnowledgeRecordProposalError("Only approved knowledge proposals can be ingested.")
    source = proposal.get("source")
    document = proposal.get("document")
    if not isinstance(source, Mapping) or not isinstance(document, Mapping):
        raise KnowledgeRecordProposalError("Knowledge proposal source and document are required.")
    return {
        "contract_version": str(proposal.get("contract_version", "0.1.0")),
        "source": dict(source),
        "document": dict(document),
        "proposal": {
            "proposal_id": proposal["proposal_id"],
            "source_run_id": proposal["source_run_id"],
            "source_profile_id": proposal["source_profile_id"],
            "source_step_id": proposal["source_step_id"],
            "evidence_uris": list(proposal["evidence_uris"]),
            "freshness_review_days": proposal["freshness_review_days"],
            "confidence_tier": proposal["confidence_tier"],
            "validation_rules": list(proposal["validation_rules"]),
            "retention_policy": proposal["retention_policy"],
        },
    }


def _validate_completed_step(
    run: Mapping[str, Any],
    source_step: Mapping[str, Any],
) -> None:
    if source_step.get("run_id") != run.get("id"):
        raise KnowledgeRecordProposalError("Knowledge proposal source step must belong to the run.")
    if source_step.get("status") != "succeeded":
        raise KnowledgeRecordProposalError(
            "Knowledge proposals can only be created from completed steps."
        )


def _proposal_errors(
    proposal: Mapping[str, Any],
    allowed_knowledge_scope_ids: frozenset[str],
) -> list[str]:
    errors: list[str] = []
    source = proposal.get("source")
    document = proposal.get("document")
    if not isinstance(source, Mapping):
        errors.append("source metadata is required")
        source = {}
    if not isinstance(document, Mapping):
        errors.append("document metadata is required")
        document = {}

    if not _id(proposal.get("proposal_id")):
        errors.append("proposal_id is required")
    if proposal.get("candidate_class") != "knowledge_record_proposal":
        errors.append("candidate_class must be knowledge_record_proposal")
    if proposal.get("promotion_route") != "knowledge_record_approval":
        errors.append("promotion_route must be knowledge_record_approval")
    for field in ("source_run_id", "source_profile_id", "source_step_id"):
        if not _id(proposal.get(field)):
            errors.append(f"{field} is required")

    if not _id(source.get("id")):
        errors.append("source.id is required")
    if source.get("source_type") not in SOURCE_TYPES:
        errors.append("source.source_type is invalid")
    if not str(source.get("uri", "")).strip():
        errors.append("source.uri is required")
    if not str(source.get("owner", "")).strip():
        errors.append("source.owner is required")
    sensitivity = source.get("sensitivity")
    if sensitivity not in SENSITIVITIES:
        errors.append("source.sensitivity is invalid")
    elif sensitivity == "secret":
        errors.append("secret knowledge proposals must not be ingested")

    if not _id(document.get("id")):
        errors.append("document.id is required")
    if not str(document.get("content", "")).strip():
        errors.append("document.content is required")
    scope_id = str(document.get("scope_id", ""))
    if not _id(scope_id):
        errors.append("document.scope_id is required")
    elif scope_id not in allowed_knowledge_scope_ids:
        errors.append("document.scope_id is not allowed")

    evidence_uris = _string_list(proposal.get("evidence_uris"))
    if not evidence_uris or any(
        not uri.startswith("hetzner://runtime/") for uri in evidence_uris
    ):
        errors.append("evidence_uris must point to Hetzner runtime artifacts")
    freshness = proposal.get("freshness_review_days")
    if not isinstance(freshness, int) or freshness < 1:
        errors.append("freshness_review_days must be a positive integer")
    if proposal.get("confidence_tier") not in CONFIDENCE_TIERS:
        errors.append("confidence_tier is invalid")
    if not _string_list(proposal.get("validation_rules")):
        errors.append("validation_rules are required")
    if not _id(proposal.get("retention_policy")):
        errors.append("retention_policy is required")
    return errors


def _id(value: Any) -> bool:
    text = str(value)
    return bool(text) and text[0].isalpha() and all(
        character.islower() or character.isdigit() or character == "-"
        for character in text
    )


def _string_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item.strip())
