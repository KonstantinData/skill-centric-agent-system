from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

COMPOSITION_CONTEXT_CONTRACT_VERSION = "0.1.0"
DEFAULT_CONTROL_PLANE_PRINCIPAL_ID = "repository-maintainer"
DEFAULT_PRINCIPAL_ID = "user-local"

RiskLevel = Literal["low", "medium", "high", "critical"]
ClassificationConfidence = Literal["high", "medium", "low"]
PrincipalType = Literal["user", "service", "system"]
ControlPlanePrincipalKind = Literal["role", "user", "service"]


@dataclass(frozen=True)
class AuthClaims:
    principal_id: str = DEFAULT_PRINCIPAL_ID
    principal_type: PrincipalType = "user"
    roles: tuple[str, ...] = (DEFAULT_CONTROL_PLANE_PRINCIPAL_ID,)
    authorization_policies: tuple[str, ...] = ("submitter-can-request-code-review",)
    control_plane_principal_kind: ControlPlanePrincipalKind = "role"
    control_plane_principal_id: str = DEFAULT_CONTROL_PLANE_PRINCIPAL_ID
    display_name: str | None = None


@dataclass(frozen=True)
class TaskClassification:
    task_type: str
    confidence: ClassificationConfidence
    reasons: tuple[str, ...]
    ambiguous_task_types: tuple[str, ...] = ()
    requires_human_review: bool = False


@dataclass(frozen=True)
class AnalyzedTask:
    task_id: str
    task_type: str
    objective: str
    risk_level: RiskLevel
    domains: tuple[str, ...]
    required_inputs: tuple[str, ...]
    available_inputs: tuple[str, ...]
    capability_hints: tuple[str, ...]
    constraints: tuple[str, ...]
    missing_information: tuple[str, ...]
    auth_claims: AuthClaims
    classification_confidence: ClassificationConfidence
    classification_reasons: tuple[str, ...]
    ambiguous_task_types: tuple[str, ...]
    requires_human_review: bool

    def to_composition_context_request(
        self,
        *,
        environment: Literal["dev", "staging", "prod"] = "dev",
        generation_mode: Literal["initial", "recomposition"] = "initial",
        parent_profile_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "contract_version": COMPOSITION_CONTEXT_CONTRACT_VERSION,
            "environment": environment,
            "principal": {
                "kind": self.auth_claims.control_plane_principal_kind,
                "id": self.auth_claims.control_plane_principal_id,
            },
            "requested_profile_generation": {
                "mode": generation_mode,
                "parent_profile_id": parent_profile_id,
            },
            "task": {
                "id": self.task_id,
                "type": self.task_type,
                "objective": self.objective,
                "risk_level": _control_plane_risk_level(self.risk_level),
                "signals": {
                    "domain_tags": list(self.domains),
                    "capability_hints": list(self.capability_hints),
                    "available_inputs": list(self.available_inputs),
                    "constraints": list(self.constraints),
                    "classification_confidence": self.classification_confidence,
                    "ambiguous_task_types": list(self.ambiguous_task_types),
                    "classification_reasons": list(self.classification_reasons),
                    "requires_human_review": self.requires_human_review,
                },
            },
        }


class TaskAnalyzer:
    """Rule-based analyzer for initial repository task intake."""

    def analyze(self, task: Mapping[str, Any]) -> AnalyzedTask:
        objective = _objective(task)
        classification = _classify_task(objective)
        task_type = classification.task_type
        repository = _repository_context(task)
        constraints = _constraints(task, classification)
        required_inputs = _required_inputs(task_type, objective, repository)
        available_inputs = _available_inputs(task_type, objective, repository, task)
        missing_information = tuple(
            input_name for input_name in required_inputs if input_name not in available_inputs
        )

        return AnalyzedTask(
            task_id=_task_id(task, objective),
            task_type=task_type,
            objective=objective,
            risk_level=_risk_level(task_type, objective, constraints),
            domains=_domains(task_type, repository),
            required_inputs=required_inputs,
            available_inputs=available_inputs,
            capability_hints=_capability_hints(task_type, objective),
            constraints=constraints,
            missing_information=missing_information,
            auth_claims=_auth_claims(task, task_type),
            classification_confidence=classification.confidence,
            classification_reasons=classification.reasons,
            ambiguous_task_types=classification.ambiguous_task_types,
            requires_human_review=classification.requires_human_review,
        )


def _objective(task: Mapping[str, Any]) -> str:
    for key in ("request", "objective", "description"):
        value = task.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Process repository task."


def _task_id(task: Mapping[str, Any], objective: str) -> str:
    value = task.get("id")
    if isinstance(value, str) and _is_id(value):
        return value
    return "task-" + _slugify(objective)


def _classify_task(objective: str) -> TaskClassification:
    text = objective.casefold()
    categories: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "code-review",
            (
                "review",
                "pull request",
                "pr",
                "diff",
                "commit",
                "regression",
                "missing tests",
            ),
        ),
        (
            "research",
            (
                "research",
                "investigate",
                "compare",
                "summarize",
                "find information",
                "look up",
                "survey",
                "diagnose",
                "debug",
                "troubleshoot",
                "explain",
                "what causes",
                "why does",
                "how do i",
                "how should",
                "stack overflow",
                "error",
                "exception",
            ),
        ),
        (
            "task-execution",
            (
                "implement",
                "build",
                "fix",
                "update",
                "change",
                "create",
                "refactor",
                "migrate",
                "add",
                "remove",
            ),
        ),
    )
    matches: list[tuple[str, tuple[str, ...]]] = []
    for task_type, terms in categories:
        matched_terms = tuple(term for term in terms if _contains_task_term(text, term))
        if task_type == "task-execution":
            matched_terms = _filter_information_request_execution_terms(
                text,
                matched_terms,
            )
        if matched_terms:
            matches.append((task_type, matched_terms))

    if len(matches) == 1:
        task_type, matched_terms = matches[0]
        return TaskClassification(
            task_type=task_type,
            confidence="high",
            reasons=(
                f"Matched {task_type} task signals: {', '.join(matched_terms)}.",
            ),
        )

    if len(matches) > 1:
        ambiguous_task_types = tuple(task_type for task_type, _ in matches)
        reasons = tuple(
            f"Matched {task_type} task signals: {', '.join(matched_terms)}."
            for task_type, matched_terms in matches
        )
        return TaskClassification(
            task_type="general-task",
            confidence="low",
            reasons=(
                *reasons,
                "Fell back to general-task because multiple specialized task types matched.",
            ),
            ambiguous_task_types=ambiguous_task_types,
            requires_human_review=True,
        )

    return TaskClassification(
        task_type="general-task",
        confidence="medium",
        reasons=("No specialized task signals matched; using general-task fallback.",),
    )


def _contains_task_term(text: str, term: str) -> bool:
    if re.fullmatch(r"[a-z0-9]+", term):
        return re.search(rf"\b{re.escape(term)}\b", text) is not None
    return term in text


def _filter_information_request_execution_terms(
    text: str,
    matched_terms: tuple[str, ...],
) -> tuple[str, ...]:
    if not _is_information_request(text):
        return matched_terms
    suppressed_terms = {"fix"}
    return tuple(term for term in matched_terms if term not in suppressed_terms)


def _is_information_request(text: str) -> bool:
    return any(
        signal in text
        for signal in (
            "how do i",
            "how should",
            "why does",
            "why do",
            "what causes",
            "what is",
            "explain",
        )
    )


def _repository_context(task: Mapping[str, Any]) -> Mapping[str, Any] | None:
    context = task.get("context")
    if not isinstance(context, Mapping):
        return None
    repository = context.get("repository")
    if isinstance(repository, Mapping):
        return repository
    return None


def _domains(task_type: str, repository: Mapping[str, Any] | None) -> tuple[str, ...]:
    domains: list[str] = []
    if task_type == "code-review":
        domains.extend(["software-engineering", "git", "code-review"])
    elif task_type == "research":
        domains.extend(["research", "knowledge-retrieval"])
    elif task_type == "task-execution":
        domains.append("task-execution")
        if repository is not None:
            domains.append("software-engineering")
    if repository is not None:
        domains.append("repository")
    return _dedupe(domains)


def _required_inputs(
    task_type: str,
    objective: str,
    repository: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    inputs: list[str] = []
    if task_type == "code-review" or repository is not None:
        inputs.append("repository")
    if task_type == "code-review" and _objective_mentions_diff_source(objective):
        inputs.append("diff")
    return _dedupe(inputs)


def _available_inputs(
    task_type: str,
    objective: str,
    repository: Mapping[str, Any] | None,
    task: Mapping[str, Any],
) -> tuple[str, ...]:
    inputs: list[str] = []
    if repository is not None:
        inputs.append("repository")
    if (
        repository is not None
        and task_type == "code-review"
        and _objective_mentions_diff_source(objective)
    ):
        inputs.append("diff")

    context = task.get("context")
    if isinstance(context, Mapping):
        attachments = context.get("attachments")
        if isinstance(attachments, list) and attachments:
            inputs.append("attachments")

    return _dedupe(inputs)


def _objective_mentions_diff_source(objective: str) -> bool:
    text = objective.casefold()
    return any(term in text for term in ("diff", "commit", "pull request", "pr", "changes"))


def _capability_hints(task_type: str, objective: str) -> tuple[str, ...]:
    hints = []
    if task_type == "code-review":
        hints.append("analysis")
    elif task_type == "research":
        hints.extend(["retrieval", "analysis"])
    elif task_type == "task-execution":
        hints.append("execution")
    text = objective.casefold()
    if "schema" in text or "contract" in text:
        hints.append("schema-validation")
    return _dedupe(hints)


def _constraints(
    task: Mapping[str, Any],
    classification: TaskClassification | None = None,
) -> tuple[str, ...]:
    raw_constraints = task.get("constraints")
    constraints: list[str] = []
    if isinstance(raw_constraints, Mapping):
        if raw_constraints.get("write_access") is False:
            constraints.append("Do not grant write tools by default.")
        if raw_constraints.get("destructive_actions") is False:
            constraints.append("Destructive actions are not allowed.")
        if raw_constraints.get("write_access") is True:
            constraints.append("Write access was requested.")
        if raw_constraints.get("destructive_actions") is True:
            constraints.append("Destructive actions were requested.")
    elif isinstance(raw_constraints, list):
        constraints.extend(str(item) for item in raw_constraints if str(item).strip())

    if not constraints:
        constraints.append("Do not grant broad capabilities by default.")
    if classification is not None and classification.requires_human_review:
        constraints.append(
            "Task classification is ambiguous; do not route to a specialized runtime "
            "strategy without review."
        )
    return _dedupe(constraints)


def _risk_level(task_type: str, objective: str, constraints: tuple[str, ...]) -> RiskLevel:
    text = " ".join((objective, *constraints)).casefold()
    if any(term in text for term in ("production", "delete", "destroy", "reset", "secret")):
        return "high"
    if "destructive actions were requested" in text or "write access was requested" in text:
        return "high"
    if task_type == "code-review":
        return "medium"
    return "low"


def _auth_claims(task: Mapping[str, Any], task_type: str) -> AuthClaims:
    context = task.get("context")
    auth = context.get("auth") if isinstance(context, Mapping) else None
    if not isinstance(auth, Mapping):
        return AuthClaims(
            authorization_policies=(f"submitter-can-request-{task_type}",),
        )

    roles = _dedupe(
        str(role) for role in auth.get("roles", [DEFAULT_CONTROL_PLANE_PRINCIPAL_ID])
    )
    principal_id = str(auth.get("principal_id") or DEFAULT_PRINCIPAL_ID)
    principal_type = str(auth.get("principal_type") or "user")
    if principal_type not in {"user", "service", "system"}:
        principal_type = "user"

    control_plane_principal_kind = str(auth.get("control_plane_principal_kind") or "role")
    if control_plane_principal_kind not in {"role", "user", "service"}:
        control_plane_principal_kind = "role"

    control_plane_principal_id = str(
        auth.get("control_plane_principal_id") or roles[0] or DEFAULT_CONTROL_PLANE_PRINCIPAL_ID
    )
    authorization_policies = _dedupe(
        str(policy)
        for policy in auth.get("authorization_policies", [f"submitter-can-request-{task_type}"])
    )
    display_name = auth.get("display_name")

    return AuthClaims(
        principal_id=principal_id,
        principal_type=principal_type,  # type: ignore[arg-type]
        roles=roles or (DEFAULT_CONTROL_PLANE_PRINCIPAL_ID,),
        authorization_policies=authorization_policies or (f"submitter-can-request-{task_type}",),
        control_plane_principal_kind=control_plane_principal_kind,  # type: ignore[arg-type]
        control_plane_principal_id=_slugify(control_plane_principal_id),
        display_name=str(display_name) if isinstance(display_name, str) and display_name else None,
    )


def _control_plane_risk_level(risk_level: RiskLevel) -> Literal["low", "medium", "high"]:
    if risk_level == "critical":
        return "high"
    return risk_level


def _is_id(value: str) -> bool:
    return re.fullmatch(r"[a-z][a-z0-9-]*", value) is not None


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    if not slug:
        return "task"
    if not slug[0].isalpha():
        slug = "id-" + slug
    return slug[:80].strip("-")


def _dedupe(values: Any) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return tuple(result)
