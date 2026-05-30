"""Executable invariant assertions for profile sealing safety guarantees."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

PROFILE_SELECTION_FIELDS = (
    "instructions",
    "skills",
    "tools",
    "knowledge_scopes",
    "data_scopes",
    "memory_scopes",
    "policies",
    "validators",
)

TASK_TYPE_VALIDATOR_REQUIREMENTS: dict[str, str] = {
    "code-review": "review-findings-contract",
    "research": "research-output-contract",
    "task-execution": "task-execution-output-contract",
    "general-task": "general-output-contract",
}


@dataclass(frozen=True)
class InvariantFinding:
    invariant_id: str
    message: str


def assert_profile_sealing_invariants(profile: Mapping[str, Any]) -> list[InvariantFinding]:
    """Run all invariant checks for a single runtime profile payload."""
    findings: list[InvariantFinding] = []
    findings.extend(assert_fail_closed_on_unknowns(profile))
    findings.extend(assert_no_self_granting(profile))
    findings.extend(assert_mandatory_validators_per_change_type(profile))
    findings.extend(assert_immutable_profile_after_seal(profile))
    return findings


def assert_fail_closed_on_unknowns(profile: Mapping[str, Any]) -> list[InvariantFinding]:
    """Ensure selected modules and version pins are exact and fail-closed."""
    findings: list[InvariantFinding] = []
    selected_modules = _selected_modules(profile)
    module_versions = profile.get("module_versions")
    if not isinstance(module_versions, Mapping):
        return [
            InvariantFinding(
                invariant_id="fail_closed_on_unknowns",
                message="module_versions must be an object with explicit pins.",
            )
        ]

    version_keys = {str(key) for key in module_versions}
    missing = sorted(selected_modules - version_keys)
    extras = sorted(version_keys - selected_modules)
    if missing:
        findings.append(
            InvariantFinding(
                invariant_id="fail_closed_on_unknowns",
                message="missing module version pins for selected modules: " + ", ".join(missing),
            )
        )
    if extras:
        findings.append(
            InvariantFinding(
                invariant_id="fail_closed_on_unknowns",
                message="unexpected module version pins without selection: " + ", ".join(extras),
            )
        )

    return findings


def assert_no_self_granting(profile: Mapping[str, Any]) -> list[InvariantFinding]:
    """Ensure runtime skill routing cannot self-grant executable capabilities."""
    findings: list[InvariantFinding] = []
    skills = _string_set(profile.get("skills"))
    role_map = profile.get("skill_execution_roles")
    if not isinstance(role_map, Mapping):
        return [
            InvariantFinding(
                invariant_id="no_self_granting",
                message="skill_execution_roles must be present for runtime skill enforcement.",
            )
        ]

    runtime_skills = _string_set(role_map.get("runtime_skills"))
    shared_skills = _string_set(role_map.get("shared_skills"))
    unknown_execution_skills = sorted((runtime_skills | shared_skills) - skills)
    if unknown_execution_skills:
        findings.append(
            InvariantFinding(
                invariant_id="no_self_granting",
                message=(
                    "skill_execution_roles references unselected skills: "
                    + ", ".join(unknown_execution_skills)
                ),
            )
        )

    human_review = profile.get("human_review")
    if isinstance(human_review, Mapping) and human_review.get("required") is True:
        for field in ("skills", "tools", "knowledge_scopes", "data_scopes", "memory_scopes"):
            if _string_set(profile.get(field)):
                findings.append(
                    InvariantFinding(
                        invariant_id="no_self_granting",
                        message=f"human-review-required profile must not select {field}.",
                    )
                )

    return findings


def assert_mandatory_validators_per_change_type(
    profile: Mapping[str, Any],
) -> list[InvariantFinding]:
    """Ensure validator requirements are satisfied for the chosen task type."""
    findings: list[InvariantFinding] = []
    validators = _string_set(profile.get("validators"))
    if "runtime-profile-schema" not in validators:
        findings.append(
            InvariantFinding(
                invariant_id="mandatory_validators_per_change_type",
                message="runtime-profile-schema validator must always be selected.",
            )
        )

    task_type = str(profile.get("task_type", ""))
    required_validator = TASK_TYPE_VALIDATOR_REQUIREMENTS.get(task_type)
    human_review_required = bool(
        isinstance(profile.get("human_review"), Mapping)
        and profile["human_review"].get("required") is True
    )
    if required_validator and required_validator not in validators and not human_review_required:
        findings.append(
            InvariantFinding(
                invariant_id="mandatory_validators_per_change_type",
                message=f"missing task-type validator for {task_type}: {required_validator}",
            )
        )

    return findings


def assert_immutable_profile_after_seal(profile: Mapping[str, Any]) -> list[InvariantFinding]:
    """Ensure sealed-profile generation metadata follows immutable profile rules."""
    findings: list[InvariantFinding] = []
    generation = profile.get("profile_generation")
    parent_profile_id = profile.get("parent_profile_id")
    recomposition_reason = profile.get("recomposition_reason")

    if not isinstance(generation, int) or generation < 1:
        findings.append(
            InvariantFinding(
                invariant_id="immutable_profile_after_seal",
                message="profile_generation must be an integer >= 1.",
            )
        )
        return findings

    if generation == 1:
        if parent_profile_id is not None or recomposition_reason is not None:
            findings.append(
                InvariantFinding(
                    invariant_id="immutable_profile_after_seal",
                    message=(
                        "profile_generation 1 must not set parent_profile_id or "
                        "recomposition_reason."
                    ),
                )
            )
    else:
        if not parent_profile_id or not recomposition_reason:
            findings.append(
                InvariantFinding(
                    invariant_id="immutable_profile_after_seal",
                    message=(
                        "recomposed profiles must set parent_profile_id and "
                        "recomposition_reason."
                    ),
                )
            )

    return findings


def assert_scope_monotonicity(
    parent_profile: Mapping[str, Any],
    current_profile: Mapping[str, Any],
) -> list[InvariantFinding]:
    """Ensure scope sets are equal or narrowed within one run-attempt lineage."""
    findings: list[InvariantFinding] = []
    for field in ("tools", "knowledge_scopes", "data_scopes", "memory_scopes"):
        parent_scope = _string_set(parent_profile.get(field))
        current_scope = _string_set(current_profile.get(field))
        widened = sorted(current_scope - parent_scope)
        if widened:
            findings.append(
                InvariantFinding(
                    invariant_id="scope_monotonicity",
                    message=(
                        f"{field} widened compared to parent profile: " + ", ".join(widened)
                    ),
                )
            )
    return findings


def _selected_modules(profile: Mapping[str, Any]) -> set[str]:
    modules: set[str] = set()
    for field in PROFILE_SELECTION_FIELDS:
        modules.update(_string_set(profile.get(field)))
    return modules


def _string_set(value: Any) -> set[str]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return set()
    out: set[str] = set()
    for item in value:
        if isinstance(item, str):
            out.add(item)
    return out
