from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from skill_centric_agent_system.composition import (
    CompositionError,
    RuntimeProfileComposer,
    TaskAnalyzer,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_EXAMPLE_PATH = REPO_ROOT / "examples" / "tasks" / "code-review-task.json"
PROFILE_EXAMPLE_PATH = REPO_ROOT / "examples" / "profiles" / "code-review-profile.json"
HUMAN_REVIEW_PROFILE_EXAMPLE_PATH = (
    REPO_ROOT / "examples" / "profiles" / "human-review-required-profile.json"
)
COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response.json"
)
RESEARCH_COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response-research.json"
)
TENANT_RESEARCH_COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response-tenant-research.json"
)
COMPOSITION_CONTEXT_SCHEMA_PATH = REPO_ROOT / "schemas" / "composition-context.schema.json"
RUNTIME_PROFILE_SCHEMA_PATH = REPO_ROOT / "schemas" / "runtime-profile.schema.json"
TASK_ANALYZER_EVALUATIONS_PATH = (
    REPO_ROOT / "examples" / "evaluations" / "task-analyzer-cases.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    return {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": ref,
    }


def selected_profile_modules(profile: dict[str, Any]) -> set[str]:
    selected: set[str] = set()
    for field in (
        "instructions",
        "skills",
        "tools",
        "knowledge_scopes",
        "data_scopes",
        "memory_scopes",
        "policies",
        "validators",
    ):
        selected.update(profile[field])
    return selected


def test_task_analyzer_emits_control_plane_request_contract() -> None:
    task = load_json(TASK_EXAMPLE_PATH)
    schema = load_json(COMPOSITION_CONTEXT_SCHEMA_PATH)

    analyzed = TaskAnalyzer().analyze(task)
    request = analyzed.to_composition_context_request()

    Draft202012Validator(schema_ref(schema, "#/$defs/request")).validate(request)
    assert request["principal"] == {
        "kind": "role",
        "id": "repository-maintainer",
    }
    assert request["task"]["type"] == "code-review"
    assert request["task"]["risk_level"] == "medium"
    assert request["task"]["signals"]["available_inputs"] == ["repository", "diff"]
    assert request["task"]["signals"]["classification_confidence"] == "high"
    assert request["task"]["signals"]["ambiguous_task_types"] == []
    assert request["task"]["signals"]["requires_human_review"] is False
    assert "software-engineering" in request["task"]["signals"]["domain_tags"]
    assert "analysis" in request["task"]["signals"]["capability_hints"]
    assert analyzed.missing_information == ()


def test_task_analyzer_emits_tenant_context_for_tenant_scoped_request() -> None:
    task = deepcopy(load_json(TASK_EXAMPLE_PATH))
    task["context"]["auth"] = {
        "principal_id": "tenant-user",
        "tenant_id": "demo-tenant",
        "area_id": "demo-tenant",
        "tenant_hostname": "demo-tenant.example.invalid",
        "membership_id": "demo-tenant-membership-user",
        "roles": ["demo-tenant-reviewer"],
        "control_plane_principal_kind": "user",
        "control_plane_principal_id": "tenant-user",
    }
    schema = load_json(COMPOSITION_CONTEXT_SCHEMA_PATH)

    analyzed = TaskAnalyzer().analyze(task)
    request = analyzed.to_composition_context_request()

    Draft202012Validator(schema_ref(schema, "#/$defs/request")).validate(request)
    assert request["principal"] == {
        "kind": "user",
        "id": "tenant-user",
    }
    assert request["tenant_context"] == {
        "tenant_id": "demo-tenant",
        "area_id": "demo-tenant",
        "hostname": "demo-tenant.example.invalid",
        "membership_id": "demo-tenant-membership-user",
    }


def test_task_analyzer_matches_task_neutral_evaluation_cases() -> None:
    cases = json.loads(TASK_ANALYZER_EVALUATIONS_PATH.read_text(encoding="utf-8"))
    analyzer = TaskAnalyzer()

    for case in cases:
        analyzed = analyzer.analyze(case["task"])
        expected = case["expected"]
        assert analyzed.task_type == expected["task_type"], case["name"]
        assert analyzed.risk_level == expected["risk_level"], case["name"]
        assert list(analyzed.required_inputs) == expected["required_inputs"], case["name"]
        assert list(analyzed.available_inputs) == expected["available_inputs"], case["name"]
        assert set(expected["domains_include"]).issubset(analyzed.domains), case["name"]
        assert set(expected["capability_hints_include"]).issubset(
            analyzed.capability_hints
        ), case["name"]
        assert analyzed.classification_confidence == expected["classification_confidence"], (
            case["name"]
        )
        assert list(analyzed.ambiguous_task_types) == expected["ambiguous_task_types"], (
            case["name"]
        )
        assert analyzed.requires_human_review is expected["requires_human_review"], case["name"]
        assert analyzed.classification_reasons, case["name"]


def test_stack_overflow_like_routing_fixture_coverage_is_measured() -> None:
    cases = json.loads(TASK_ANALYZER_EVALUATIONS_PATH.read_text(encoding="utf-8"))
    analyzer = TaskAnalyzer()

    stackoverflow_cases = [
        case for case in cases if "stackoverflow-like" in case.get("fixture_tags", [])
    ]
    research_cases = [
        case
        for case in stackoverflow_cases
        if any(
            tag in case.get("fixture_tags", [])
            for tag in ("positive-research", "noisy-research")
        )
    ]
    human_review_cases = [
        case for case in stackoverflow_cases if "human-review" in case.get("fixture_tags", [])
    ]

    assert len(stackoverflow_cases) >= 5
    assert len(research_cases) >= 4
    assert human_review_cases

    research_hits = sum(
        1 for case in research_cases if analyzer.analyze(case["task"]).task_type == "research"
    )
    human_review_hits = sum(
        1
        for case in human_review_cases
        if analyzer.analyze(case["task"]).requires_human_review
    )

    assert research_hits / len(research_cases) == 1.0
    assert human_review_hits / len(human_review_cases) == 1.0


def test_profile_composer_emits_runtime_profile_from_control_plane_context() -> None:
    task = load_json(TASK_EXAMPLE_PATH)
    context_response = load_json(COMPOSITION_CONTEXT_RESPONSE_PATH)
    profile_schema = load_json(RUNTIME_PROFILE_SCHEMA_PATH)
    expected_profile = load_json(PROFILE_EXAMPLE_PATH)

    analyzed = TaskAnalyzer().analyze(task)
    profile = RuntimeProfileComposer().compose(analyzed, context_response)

    Draft202012Validator(profile_schema).validate(profile)
    assert profile == expected_profile
    assert selected_profile_modules(profile) == set(profile["module_versions"])
    assert profile["profile_version"] == "0.6.0"
    assert profile["tenant_context"]["role_derivation"] == {
        "grant_source": "tenant-role-bundles",
        "direct_user_grants_allowed": False,
        "capabilities_derive_from_roles": True,
        "data_sources_derive_from_roles": True,
    }
    assert profile["tenant_authority"] is None
    assert profile["human_review"]["required"] is False
    assert profile["skills"] == ["git-diff-analysis"]
    assert profile["skill_execution_roles"] == {
        "runtime_skills": ["git-diff-analysis"],
        "non_runtime_skills": [],
        "shared_skills": [],
    }
    assert profile["tools"] == ["filesystem-read", "git-read", "test-runner"]
    assert profile["memory_scopes"] == []


def test_profile_composer_derives_tenant_context_from_auth_claims() -> None:
    task = {
        "id": "task-demo-tenant-research",
        "objective": "Research the tenant website and summarize current context.",
        "context": {
            "auth": {
                "principal_id": "tenant-user",
                "tenant_id": "demo-tenant",
                "area_id": "demo-tenant",
                "tenant_hostname": "demo-tenant.example.invalid",
                "membership_id": "demo-tenant-membership-user",
                "roles": ["demo-tenant-researcher"],
                "control_plane_principal_id": "demo-tenant-researcher",
                "role_data_sources": ["demo-tenant-website"],
                "role_capabilities": ["research"],
            }
        },
    }
    context_response = load_json(TENANT_RESEARCH_COMPOSITION_CONTEXT_RESPONSE_PATH)

    analyzed = TaskAnalyzer().analyze(task)
    profile = RuntimeProfileComposer().compose(analyzed, context_response)

    assert profile["tenant_context"] == {
        "tenant_id": "demo-tenant",
        "area_id": "demo-tenant",
        "hostname": "demo-tenant.example.invalid",
        "membership_id": "demo-tenant-membership-user",
        "role_ids": ["demo-tenant-researcher"],
        "role_derivation": {
            "grant_source": "tenant-role-bundles",
            "direct_user_grants_allowed": False,
            "capabilities_derive_from_roles": True,
            "data_sources_derive_from_roles": True,
        },
        "allowed_role_data_sources": ["demo-tenant-website"],
        "allowed_role_capabilities": ["research"],
    }
    assert profile["tenant_authority"] == context_response["tenant_authority"]


def test_profile_composer_enforces_tenant_authority_for_tenant_profile() -> None:
    task = {
        "id": "task-demo-tenant-research",
        "objective": "Research the tenant website and summarize current context.",
        "context": {
            "auth": {
                "principal_id": "tenant-user",
                "tenant_id": "demo-tenant",
                "area_id": "demo-tenant",
                "tenant_hostname": "demo-tenant.example.invalid",
                "membership_id": "demo-tenant-membership-user",
                "roles": ["demo-tenant-researcher"],
                "control_plane_principal_id": "demo-tenant-researcher",
                "role_data_sources": ["demo-tenant-website"],
                "role_capabilities": ["research"],
            }
        },
    }
    context_response = load_json(TENANT_RESEARCH_COMPOSITION_CONTEXT_RESPONSE_PATH)

    analyzed = TaskAnalyzer().analyze(task)
    profile = RuntimeProfileComposer().compose(analyzed, context_response)

    assert profile["tenant_context"]["tenant_id"] == "demo-tenant"
    assert profile["tenant_context"]["membership_id"] == "demo-tenant-membership-user"
    assert profile["skills"] == ["research-context-synthesis"]
    assert profile["knowledge_scopes"] == ["knowledge-demo-tenant-docs"]
    assert profile["data_scopes"] == ["demo-tenant-website-read"]
    assert profile["tenant_context"]["allowed_role_data_sources"] == ["demo-tenant-website"]
    assert profile["tenant_context"]["allowed_role_capabilities"] == ["research"]
    assert profile["tenant_authority"]["membership"]["principal_id"] == "tenant-user"


@pytest.mark.parametrize(
    ("mutator", "message_part"),
    [
        (
            lambda task, response: task["context"]["auth"].pop("membership_id"),
            "membership id is required",
        ),
        (
            lambda task, response: task["context"]["auth"].__setitem__(
                "roles",
                ["other-tenant-researcher"],
            ),
            "not granted by the active membership",
        ),
        (
            lambda task, response: task["context"]["auth"].__setitem__(
                "role_data_sources",
                ["other-tenant-website"],
            ),
            "not derived from tenant roles",
        ),
        (
            lambda task, response: response["tenant_authority"].__setitem__(
                "status",
                "disabled",
            ),
            "Tenant is not active",
        ),
        (
            lambda task, response: response["tenant_authority"].__setitem__(
                "direct_user_grants_allowed",
                True,
            ),
            "Direct user grants are not allowed",
        ),
        (
            lambda task, response: response["tenant_authority"]["role_bundles"][0][
                "derived_runtime_modules"
            ]["skills"].clear(),
            "Selected skills are not allowed",
        ),
        (
            lambda task, response: response["tenant_authority"].__setitem__(
                "allowed_knowledge_scopes",
                [],
            ),
            "Selected knowledge_scopes are not allowed",
        ),
    ],
)
def test_profile_composer_fails_closed_on_invalid_tenant_authority(
    mutator: Any,
    message_part: str,
) -> None:
    task = {
        "id": "task-demo-tenant-research",
        "objective": "Research the tenant website and summarize current context.",
        "context": {
            "auth": {
                "principal_id": "tenant-user",
                "tenant_id": "demo-tenant",
                "area_id": "demo-tenant",
                "tenant_hostname": "demo-tenant.example.invalid",
                "membership_id": "demo-tenant-membership-user",
                "roles": ["demo-tenant-researcher"],
                "control_plane_principal_id": "demo-tenant-researcher",
                "role_data_sources": ["demo-tenant-website"],
                "role_capabilities": ["research"],
            }
        },
    }
    context_response = load_json(TENANT_RESEARCH_COMPOSITION_CONTEXT_RESPONSE_PATH)
    mutator(task, context_response)

    analyzed = TaskAnalyzer().analyze(task)

    with pytest.raises(CompositionError, match=message_part):
        RuntimeProfileComposer().compose(analyzed, context_response)


def test_profile_composer_requires_tenant_authority_for_tenant_profile() -> None:
    task = {
        "id": "task-demo-tenant-research",
        "objective": "Research the tenant website and summarize current context.",
        "context": {
            "auth": {
                "principal_id": "tenant-user",
                "tenant_id": "demo-tenant",
                "area_id": "demo-tenant",
                "tenant_hostname": "demo-tenant.example.invalid",
                "membership_id": "demo-tenant-membership-user",
                "roles": ["demo-tenant-researcher"],
                "control_plane_principal_id": "demo-tenant-researcher",
                "role_data_sources": ["demo-tenant-website"],
                "role_capabilities": ["research"],
            }
        },
    }
    context_response = load_json(TENANT_RESEARCH_COMPOSITION_CONTEXT_RESPONSE_PATH)
    context_response.pop("tenant_authority")

    analyzed = TaskAnalyzer().analyze(task)

    with pytest.raises(CompositionError, match="Tenant authority is required"):
        RuntimeProfileComposer().compose(analyzed, context_response)


def test_profile_composer_rejects_memory_scope_as_knowledge_substitute() -> None:
    task = {
        "id": "task-research-runtime-context",
        "objective": "Research runtime context and explain what causes validation drift.",
    }
    context_response = load_json(RESEARCH_COMPOSITION_CONTEXT_RESPONSE_PATH)
    context_response["allowed_knowledge_scopes"] = []
    context_response["allowed_memory_scopes"] = [
        {
            "id": "mod-project-memory",
            "name": "project-memory",
            "kind": "memory_scope",
            "version": "0.1.0",
            "score": 0.5,
            "reason": "Allowed for principal by scope binding.",
        }
    ]

    analyzed = TaskAnalyzer().analyze(task)

    with pytest.raises(CompositionError, match="Memory scopes cannot substitute"):
        RuntimeProfileComposer().compose(analyzed, context_response)


def test_profile_composer_emits_review_required_profile_for_ambiguous_task() -> None:
    cases = json.loads(TASK_ANALYZER_EVALUATIONS_PATH.read_text(encoding="utf-8"))
    task = next(
        case["task"]
        for case in cases
        if case["name"] == "ambiguous research and execution task falls back to general"
    )
    context_response = load_json(COMPOSITION_CONTEXT_RESPONSE_PATH)
    profile_schema = load_json(RUNTIME_PROFILE_SCHEMA_PATH)
    expected_profile = load_json(HUMAN_REVIEW_PROFILE_EXAMPLE_PATH)

    analyzed = TaskAnalyzer().analyze(task)
    profile = RuntimeProfileComposer().compose(analyzed, context_response)

    Draft202012Validator(profile_schema).validate(profile)
    assert profile == expected_profile
    assert selected_profile_modules(profile) == set(profile["module_versions"])
    assert profile["human_review"]["required"] is True
    assert profile["human_review"]["status"] == "required"
    assert profile["human_review"]["ambiguous_task_types"] == ["research", "task-execution"]
    assert profile["skills"] == []
    assert profile["skill_execution_roles"] == {
        "runtime_skills": [],
        "non_runtime_skills": [],
        "shared_skills": [],
    }
    assert profile["tools"] == []
    assert profile["knowledge_scopes"] == []
    assert profile["data_scopes"] == []
    assert profile["memory_scopes"] == []
    assert profile["validators"] == ["runtime-profile-schema"]
    assert profile["limits"]["max_tool_calls"] == 0
    assert profile["limits"]["max_data_reads"] == 0
    assert profile["limits"]["max_memory_ops"] == 0
    assert profile["limits"]["max_recompositions"] == 0
    assert "git-diff-analysis" not in selected_profile_modules(profile)


def test_profile_composer_fails_closed_when_control_plane_denies_context() -> None:
    task = load_json(TASK_EXAMPLE_PATH)
    context_response = load_json(COMPOSITION_CONTEXT_RESPONSE_PATH)
    context_response["composition_status"] = "denied"
    analyzed = TaskAnalyzer().analyze(task)

    with pytest.raises(CompositionError, match="not ready"):
        RuntimeProfileComposer().compose(analyzed, context_response)


def test_profile_composer_fails_closed_when_graph_is_invalid() -> None:
    task = load_json(TASK_EXAMPLE_PATH)
    context_response = load_json(COMPOSITION_CONTEXT_RESPONSE_PATH)
    context_response["graph_validation"]["is_valid"] = False
    context_response["graph_validation"]["errors"] = ["git-read is not allowed."]
    analyzed = TaskAnalyzer().analyze(task)

    with pytest.raises(CompositionError, match="graph validation failed"):
        RuntimeProfileComposer().compose(analyzed, context_response)


def test_profile_composer_fails_without_applicable_policies() -> None:
    task = load_json(TASK_EXAMPLE_PATH)
    context_response = load_json(COMPOSITION_CONTEXT_RESPONSE_PATH)
    context_response["applicable_policies"] = []
    analyzed = TaskAnalyzer().analyze(task)

    with pytest.raises(CompositionError, match="no applicable policies"):
        RuntimeProfileComposer().compose(analyzed, context_response)


def test_profile_composer_preserves_recomposition_traceability() -> None:
    task = load_json(TASK_EXAMPLE_PATH)
    context_response = load_json(COMPOSITION_CONTEXT_RESPONSE_PATH)
    analyzed = TaskAnalyzer().analyze(task)

    profile = RuntimeProfileComposer().compose(
        analyzed,
        context_response,
        profile_generation=2,
        parent_profile_id="profile-code-review-latest-commit",
        recomposition_reason="missing_capability",
    )

    assert profile["profile_generation"] == 2
    assert profile["id"] == "profile-code-review-latest-commit-g2"
    assert profile["parent_profile_id"] == "profile-code-review-latest-commit"
    assert profile["recomposition_reason"] == "missing_capability"


def test_profile_composer_rejects_invalid_recomposition_traceability() -> None:
    task = load_json(TASK_EXAMPLE_PATH)
    context_response = load_json(COMPOSITION_CONTEXT_RESPONSE_PATH)
    analyzed = TaskAnalyzer().analyze(task)

    with pytest.raises(CompositionError, match="recomposition_reason"):
        RuntimeProfileComposer().compose(
            analyzed,
            context_response,
            profile_generation=2,
            parent_profile_id="profile-code-review-latest-commit",
            recomposition_reason="freeform-capability-grant",
        )


def test_profile_composer_fails_when_required_inputs_are_missing() -> None:
    task = deepcopy(load_json(TASK_EXAMPLE_PATH))
    task["context"].pop("repository")
    analyzed = TaskAnalyzer().analyze(task)

    assert analyzed.missing_information == ("repository", "diff")
    with pytest.raises(CompositionError, match="missing required inputs"):
        RuntimeProfileComposer().compose(
            analyzed,
            load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
        )
