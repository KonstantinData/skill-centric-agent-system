from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any

from skill_centric_agent_system.composition.task_analyzer import AnalyzedTask
from skill_centric_agent_system.composition.tenant_access import (
    TenantAccessError,
    TenantAccessValidator,
)

RUNTIME_PROFILE_VERSION = "0.6.0"
BASELINE_MODULE_VERSIONS = {
    "base-agent-rules": "0.1.0",
    "runtime-profile-schema": "0.1.0",
}
TASK_INSTRUCTION_VERSIONS = {
    "code-review": {
        "code-review-rules": "0.1.0",
    },
}
DEFAULT_LIMITS = {
    "max_tool_calls": 30,
    "max_tokens": 60000,
    "max_duration_seconds": 900,
    "max_data_reads": 120,
    "max_memory_ops": 10,
    "max_recompositions": 1,
}
DEFAULT_FAILURE_POLICY = {
    "on_composer_failure": "request_clarification",
    "on_validator_failure": "fail_closed",
    "on_policy_denial": "return_error",
    "on_budget_exhausted": "return_error",
}
HUMAN_REVIEW_LIMITS = {
    **DEFAULT_LIMITS,
    "max_tool_calls": 0,
    "max_data_reads": 0,
    "max_memory_ops": 0,
    "max_recompositions": 0,
}
HUMAN_REVIEW_FAILURE_POLICY = {
    "on_composer_failure": "fail_closed",
    "on_validator_failure": "fail_closed",
    "on_policy_denial": "fail_closed",
    "on_budget_exhausted": "return_error",
}
DEFAULT_CAPTURE_EVENTS = (
    "task_analyzed",
    "candidates_discovered",
    "candidates_scored",
    "policies_evaluated",
    "graph_validated",
    "profile_emitted",
    "profile_validated",
    "runtime_completed",
)
RECOMPOSITION_REASONS = frozenset(
    (
        "task_reclassified",
        "missing_capability",
        "policy_change",
        "budget_exhausted",
        "validator_failure",
    )
)
SKILL_RUNTIME_ROLES = frozenset(("runtime", "non-runtime", "shared"))


class CompositionError(ValueError):
    """Raised when a runtime profile cannot be composed safely."""


class RuntimeProfileComposer:
    """Build schema-shaped runtime profiles from Control Plane composition context."""

    def __init__(self, tenant_access_validator: TenantAccessValidator | None = None) -> None:
        self.tenant_access_validator = tenant_access_validator or TenantAccessValidator()

    def compose(
        self,
        analyzed_task: AnalyzedTask,
        context_response: Mapping[str, Any],
        *,
        profile_generation: int = 1,
        parent_profile_id: str | None = None,
        recomposition_reason: str | None = None,
    ) -> dict[str, Any]:
        _assert_recomposition_traceability(
            profile_generation=profile_generation,
            parent_profile_id=parent_profile_id,
            recomposition_reason=recomposition_reason,
        )
        self._assert_composable(analyzed_task, context_response)

        candidate_modules = _references(context_response, "candidate_modules")
        graph_modules = _graph_references(context_response)
        version_by_name = _versions_by_name(
            [
                *candidate_modules,
                *_references(context_response, "applicable_policies"),
                *_references(context_response, "allowed_knowledge_scopes"),
                *_references(context_response, "allowed_data_scopes"),
                *_references(context_response, "allowed_memory_scopes"),
                *_references(context_response, "validation_requirements"),
                *graph_modules,
            ]
        )

        if analyzed_task.requires_human_review:
            profile = _human_review_profile(
                analyzed_task,
                context_response,
                version_by_name,
                profile_generation=profile_generation,
                parent_profile_id=parent_profile_id,
                recomposition_reason=recomposition_reason,
            )
            self._assert_tenant_access(
                analyzed_task,
                context_response,
                selected_modules={
                    "instructions": profile["instructions"],
                    "skills": profile["skills"],
                    "tools": profile["tools"],
                    "knowledge_scopes": profile["knowledge_scopes"],
                    "data_scopes": profile["data_scopes"],
                    "memory_scopes": profile["memory_scopes"],
                    "policies": profile["policies"],
                    "validators": profile["validators"],
                },
            )
            return profile

        instructions = _dedupe(
            (
                "base-agent-rules",
                *TASK_INSTRUCTION_VERSIONS.get(analyzed_task.task_type, ()),
                *_names(candidate_modules, "instruction"),
            )
        )
        skills = _dedupe(_names(candidate_modules, "skill"))
        skill_execution_roles = _skill_execution_roles(candidate_modules, skills)
        tools = _dedupe((*_names(candidate_modules, "tool"), *_names(graph_modules, "tool")))
        knowledge_scopes = _dedupe(
            _names(_references(context_response, "allowed_knowledge_scopes"))
        )
        data_scopes = _dedupe(_names(_references(context_response, "allowed_data_scopes")))
        memory_scopes = _dedupe(_names(_references(context_response, "allowed_memory_scopes")))
        policies = _dedupe(_names(_references(context_response, "applicable_policies")))
        validators = _dedupe(
            (
                "runtime-profile-schema",
                *_names(_references(context_response, "validation_requirements")),
            )
        )
        if not policies:
            raise CompositionError("Control Plane returned no applicable policies.")

        selected_modules = (
            *instructions,
            *skills,
            *tools,
            *knowledge_scopes,
            *data_scopes,
            *memory_scopes,
            *policies,
            *validators,
        )
        selected_by_field = {
            "instructions": instructions,
            "skills": skills,
            "tools": tools,
            "knowledge_scopes": knowledge_scopes,
            "data_scopes": data_scopes,
            "memory_scopes": memory_scopes,
            "policies": policies,
            "validators": validators,
        }
        self._assert_tenant_access(
            analyzed_task,
            context_response,
            selected_modules=selected_by_field,
        )

        return {
            "id": _profile_id(analyzed_task.task_id, profile_generation),
            "profile_version": RUNTIME_PROFILE_VERSION,
            "profile_generation": profile_generation,
            "parent_profile_id": parent_profile_id,
            "recomposition_reason": recomposition_reason,
            "task_type": analyzed_task.task_type,
            "objective": analyzed_task.objective,
            "risk_level": analyzed_task.risk_level,
            "auth_context": _auth_context(analyzed_task),
            "tenant_context": _tenant_context(analyzed_task),
            "tenant_authority": _tenant_authority_snapshot(analyzed_task, context_response),
            "human_review": _human_review_not_required(analyzed_task),
            "instructions": list(instructions),
            "skills": list(skills),
            "skill_execution_roles": skill_execution_roles,
            "tools": list(tools),
            "knowledge_scopes": list(knowledge_scopes),
            "data_scopes": list(data_scopes),
            "memory_scopes": list(memory_scopes),
            "policies": list(policies),
            "validators": list(validators),
            "module_versions": {
                name: _version_for(name, version_by_name, analyzed_task.task_type)
                for name in selected_modules
            },
            "limits": dict(DEFAULT_LIMITS),
            "failure_policy": dict(DEFAULT_FAILURE_POLICY),
            "observability": {
                "trace_id": _trace_id(analyzed_task.task_id),
                "log_level": "info",
                "capture_events": list(DEFAULT_CAPTURE_EVENTS),
                "redact_sensitive_data": True,
            },
        }

    def _assert_tenant_access(
        self,
        analyzed_task: AnalyzedTask,
        context_response: Mapping[str, Any],
        *,
        selected_modules: Mapping[str, Iterable[str]],
    ) -> None:
        try:
            self.tenant_access_validator.validate(
                analyzed_task,
                context_response,
                selected_modules=selected_modules,
            )
        except TenantAccessError as error:
            raise CompositionError(str(error)) from error

    def _assert_composable(
        self,
        analyzed_task: AnalyzedTask,
        context_response: Mapping[str, Any],
    ) -> None:
        if analyzed_task.missing_information:
            missing = ", ".join(analyzed_task.missing_information)
            raise CompositionError(f"Cannot compose profile; missing required inputs: {missing}.")

        status = context_response.get("composition_status")
        if status != "ready":
            raise CompositionError(f"Control Plane composition status is not ready: {status}.")

        graph_validation = context_response.get("graph_validation")
        if not isinstance(graph_validation, Mapping):
            raise CompositionError("Control Plane response is missing graph validation.")
        if graph_validation.get("is_valid") is not True:
            errors = graph_validation.get("errors", [])
            if isinstance(errors, list) and errors:
                raise CompositionError(
                    "Control Plane graph validation failed: " + "; ".join(errors)
                )
            raise CompositionError("Control Plane graph validation failed.")

        candidate_modules = _references(context_response, "candidate_modules")
        if not candidate_modules and not analyzed_task.requires_human_review:
            raise CompositionError("Control Plane returned no candidate modules.")
        if analyzed_task.requires_human_review:
            return

        if _requires_knowledge_context(analyzed_task):
            allowed_knowledge_scopes = _references(context_response, "allowed_knowledge_scopes")
            allowed_memory_scopes = _references(context_response, "allowed_memory_scopes")
            if allowed_memory_scopes and not allowed_knowledge_scopes:
                raise CompositionError(
                    "Memory scopes cannot substitute for knowledge scopes on research or "
                    "retrieval tasks."
                )

        policy_effects = {
            decision["module"]["name"]: decision["effect"]
            for decision in _policy_decisions(context_response)
            if isinstance(decision.get("module"), Mapping)
        }
        for module in candidate_modules:
            effect = policy_effects.get(str(module["name"]))
            if effect is not None and effect != "allow":
                raise CompositionError(
                    f"Candidate module {module['name']} is not policy-allowed: {effect}."
                )
        for module in _graph_references(context_response):
            if module.get("kind") != "tool":
                continue
            effect = policy_effects.get(str(module["name"]))
            if effect != "allow":
                raise CompositionError(
                    f"Selected tool {module['name']} is not policy-allowed: "
                    f"{effect or 'missing'}."
                )


def _human_review_profile(
    analyzed_task: AnalyzedTask,
    context_response: Mapping[str, Any],
    version_by_name: Mapping[str, str],
    *,
    profile_generation: int,
    parent_profile_id: str | None,
    recomposition_reason: str | None,
) -> dict[str, Any]:
    instructions = ("base-agent-rules",)
    policies = _dedupe(_names(_references(context_response, "applicable_policies")))
    validators = ("runtime-profile-schema",)
    if not policies:
        raise CompositionError("Control Plane returned no applicable policies.")

    selected_modules = (*instructions, *policies, *validators)
    return {
        "id": _profile_id(analyzed_task.task_id, profile_generation),
        "profile_version": RUNTIME_PROFILE_VERSION,
        "profile_generation": profile_generation,
        "parent_profile_id": parent_profile_id,
        "recomposition_reason": recomposition_reason,
        "task_type": analyzed_task.task_type,
        "objective": analyzed_task.objective,
        "risk_level": analyzed_task.risk_level,
        "auth_context": _auth_context(analyzed_task),
        "tenant_context": _tenant_context(analyzed_task),
        "tenant_authority": _tenant_authority_snapshot(analyzed_task, context_response),
        "human_review": _human_review_required(analyzed_task),
        "instructions": list(instructions),
        "skills": [],
        "skill_execution_roles": {
            "runtime_skills": [],
            "non_runtime_skills": [],
            "shared_skills": [],
        },
        "tools": [],
        "knowledge_scopes": [],
        "data_scopes": [],
        "memory_scopes": [],
        "policies": list(policies),
        "validators": list(validators),
        "module_versions": {
            name: _version_for(name, version_by_name, analyzed_task.task_type)
            for name in selected_modules
        },
        "limits": dict(HUMAN_REVIEW_LIMITS),
        "failure_policy": dict(HUMAN_REVIEW_FAILURE_POLICY),
        "observability": {
            "trace_id": _trace_id(analyzed_task.task_id),
            "log_level": "info",
            "capture_events": list(DEFAULT_CAPTURE_EVENTS),
            "redact_sensitive_data": True,
        },
    }


def _human_review_required(analyzed_task: AnalyzedTask) -> dict[str, Any]:
    return {
        "required": True,
        "status": "required",
        "reason": (
            "Task classification matched multiple specialized task types; "
            "specialized runtime composition requires human approval."
        ),
        "ambiguous_task_types": list(analyzed_task.ambiguous_task_types),
        "classification_confidence": analyzed_task.classification_confidence,
        "classification_reasons": list(analyzed_task.classification_reasons),
        "allowed_before_approval": [
            "profile_validation",
            "audit_recording",
            "clarification_request",
        ],
    }


def _human_review_not_required(analyzed_task: AnalyzedTask) -> dict[str, Any]:
    return {
        "required": False,
        "status": "not_required",
        "reason": "Analyzer did not require human review.",
        "ambiguous_task_types": list(analyzed_task.ambiguous_task_types),
        "classification_confidence": analyzed_task.classification_confidence,
        "classification_reasons": list(analyzed_task.classification_reasons),
        "allowed_before_approval": [],
    }


def _references(context_response: Mapping[str, Any], field: str) -> tuple[Mapping[str, Any], ...]:
    values = context_response.get(field, [])
    if not isinstance(values, list):
        return ()
    return tuple(value for value in values if isinstance(value, Mapping))


def _graph_references(context_response: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    graph_validation = context_response.get("graph_validation", {})
    if not isinstance(graph_validation, Mapping):
        return ()
    reachable = graph_validation.get("reachable_modules", [])
    if not isinstance(reachable, list):
        return ()
    return tuple(value for value in reachable if isinstance(value, Mapping))


def _policy_decisions(context_response: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    decisions = context_response.get("policy_decisions", [])
    if not isinstance(decisions, list):
        return ()
    return tuple(value for value in decisions if isinstance(value, Mapping))


def _names(
    references: Iterable[Mapping[str, Any]],
    kind: str | None = None,
) -> tuple[str, ...]:
    names: list[str] = []
    for reference in references:
        if kind is not None and reference.get("kind") != kind:
            continue
        name = reference.get("name")
        if isinstance(name, str):
            names.append(name)
    return tuple(names)


def _versions_by_name(references: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for reference in references:
        name = reference.get("name")
        version = reference.get("version")
        if isinstance(name, str) and isinstance(version, str):
            versions[name] = version
    return versions


def _skill_execution_roles(
    candidate_modules: Iterable[Mapping[str, Any]],
    selected_skills: Iterable[str],
) -> dict[str, list[str]]:
    role_by_skill_name: dict[str, str] = {}
    for module in candidate_modules:
        if module.get("kind") != "skill":
            continue
        name = module.get("name")
        if not isinstance(name, str):
            continue
        raw_role = module.get("runtime_role", "runtime")
        role = str(raw_role)
        if role not in SKILL_RUNTIME_ROLES:
            choices = ", ".join(sorted(SKILL_RUNTIME_ROLES))
            raise CompositionError(
                f"Invalid runtime_role for skill module {name}: {role}. Expected one of: {choices}."
            )
        role_by_skill_name[name] = role

    runtime_skills: list[str] = []
    non_runtime_skills: list[str] = []
    shared_skills: list[str] = []
    for skill_name in selected_skills:
        role = role_by_skill_name.get(skill_name, "runtime")
        if role == "runtime":
            runtime_skills.append(skill_name)
        elif role == "non-runtime":
            non_runtime_skills.append(skill_name)
        else:
            shared_skills.append(skill_name)

    return {
        "runtime_skills": runtime_skills,
        "non_runtime_skills": non_runtime_skills,
        "shared_skills": shared_skills,
    }


def _requires_knowledge_context(analyzed_task: AnalyzedTask) -> bool:
    return analyzed_task.task_type == "research" or "retrieval" in analyzed_task.capability_hints


def _version_for(
    name: str,
    version_by_name: Mapping[str, str],
    task_type: str,
) -> str:
    if name in version_by_name:
        return version_by_name[name]
    if name in BASELINE_MODULE_VERSIONS:
        return BASELINE_MODULE_VERSIONS[name]
    task_versions = TASK_INSTRUCTION_VERSIONS.get(task_type, {})
    if name in task_versions:
        return task_versions[name]
    raise CompositionError(f"No version pin is available for selected module: {name}.")


def _assert_recomposition_traceability(
    *,
    profile_generation: int,
    parent_profile_id: str | None,
    recomposition_reason: str | None,
) -> None:
    if profile_generation < 1:
        raise CompositionError("profile_generation must be greater than zero.")
    if profile_generation == 1:
        if parent_profile_id is not None or recomposition_reason is not None:
            raise CompositionError("Initial profiles cannot include recomposition traceability.")
        return
    if parent_profile_id is None or recomposition_reason is None:
        raise CompositionError(
            "Recomposed profiles require parent_profile_id and recomposition_reason."
        )
    if recomposition_reason not in RECOMPOSITION_REASONS:
        allowed = ", ".join(sorted(RECOMPOSITION_REASONS))
        raise CompositionError(
            f"recomposition_reason must be one of: {allowed}. Got: {recomposition_reason}."
        )


def _auth_context(analyzed_task: AnalyzedTask) -> dict[str, Any]:
    principal: dict[str, Any] = {
        "id": analyzed_task.auth_claims.principal_id,
        "type": analyzed_task.auth_claims.principal_type,
    }
    if analyzed_task.auth_claims.display_name is not None:
        principal["display_name"] = analyzed_task.auth_claims.display_name

    return {
        "principal": principal,
        "roles": list(analyzed_task.auth_claims.roles),
        "authorization_policies": list(analyzed_task.auth_claims.authorization_policies),
    }


def _tenant_context(analyzed_task: AnalyzedTask) -> dict[str, Any]:
    role_data_sources = analyzed_task.auth_claims.role_data_sources
    role_capabilities = analyzed_task.auth_claims.role_capabilities

    return {
        "tenant_id": analyzed_task.auth_claims.tenant_id,
        "area_id": analyzed_task.auth_claims.area_id,
        "hostname": analyzed_task.auth_claims.tenant_hostname,
        "membership_id": analyzed_task.auth_claims.membership_id,
        "role_ids": list(analyzed_task.auth_claims.roles),
        "role_derivation": {
            "grant_source": "tenant-role-bundles",
            "direct_user_grants_allowed": False,
            "capabilities_derive_from_roles": True,
            "data_sources_derive_from_roles": True,
        },
        "allowed_role_data_sources": list(role_data_sources),
        "allowed_role_capabilities": list(role_capabilities),
    }


def _tenant_authority_snapshot(
    analyzed_task: AnalyzedTask,
    context_response: Mapping[str, Any],
) -> dict[str, Any] | None:
    if analyzed_task.auth_claims.tenant_id == "global":
        return None

    authority = context_response.get("tenant_authority")
    if not isinstance(authority, Mapping):
        raise CompositionError("Tenant authority is required for tenant-scoped profiles.")
    return deepcopy(dict(authority))


def _profile_id(task_id: str, profile_generation: int = 1) -> str:
    if task_id.startswith("task-"):
        profile_id = "profile-" + task_id.removeprefix("task-")
    else:
        profile_id = "profile-" + task_id
    if profile_generation <= 1:
        return profile_id
    return f"{profile_id}-g{profile_generation}"


def _trace_id(task_id: str) -> str:
    if task_id.startswith("task-"):
        return "trace-" + task_id.removeprefix("task-")
    return "trace-" + task_id


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return tuple(result)
