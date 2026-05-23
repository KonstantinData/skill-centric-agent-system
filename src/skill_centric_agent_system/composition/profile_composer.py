from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from skill_centric_agent_system.composition.task_analyzer import AnalyzedTask

RUNTIME_PROFILE_VERSION = "0.2.0"
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


class CompositionError(ValueError):
    """Raised when a runtime profile cannot be composed safely."""


class RuntimeProfileComposer:
    """Build schema-shaped runtime profiles from Control Plane composition context."""

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

        instructions = _dedupe(
            (
                "base-agent-rules",
                *TASK_INSTRUCTION_VERSIONS.get(analyzed_task.task_type, ()),
                *_names(candidate_modules, "instruction"),
            )
        )
        skills = _dedupe(_names(candidate_modules, "skill"))
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
            "instructions": list(instructions),
            "skills": list(skills),
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
        if not candidate_modules:
            raise CompositionError("Control Plane returned no candidate modules.")

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
