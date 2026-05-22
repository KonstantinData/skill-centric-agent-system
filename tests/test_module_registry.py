from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from skill_centric_agent_system.registries import (
    InMemoryModuleRegistry,
    ModuleMetadata,
    PolicyContext,
    RegistryQuery,
    TaskSignals,
)
from skill_centric_agent_system.registries.modules import UnknownModuleError

REPO_ROOT = Path(__file__).resolve().parents[1]
GIT_DIFF_MODULE_PATH = REPO_ROOT / "examples" / "modules" / "git-diff-analysis.json"


def load_git_diff_module() -> dict[str, object]:
    return json.loads(GIT_DIFF_MODULE_PATH.read_text(encoding="utf-8"))


def module_fixture(
    name: str,
    kind: str,
    *,
    capability_class: str = "analysis",
    task_types: list[str] | None = None,
    domains: list[str] | None = None,
    required_inputs: list[str] | None = None,
    policies: list[str] | None = None,
    validators: list[str] | None = None,
) -> ModuleMetadata:
    module = {
        "name": name,
        "version": "0.1.0",
        "kind": kind,
        "description": f"{name} test module.",
        "capability_class": capability_class,
        "domain_tags": domains or [name],
        "task_signals": {
            "task_types": task_types or ["code-review"],
            "risk_levels": ["low", "medium", "high"],
            "domains": domains or [name],
            "required_inputs": required_inputs or [],
            "phrases": [name],
            "negative_phrases": [],
        },
        "triggers": [name],
        "inputs": required_inputs or [],
        "outputs": [f"{name}-output"],
        "required_tools": [],
        "optional_tools": [],
        "knowledge_scopes": [],
        "data_scopes": [],
        "policies": policies or [],
        "validators": validators or [],
        "selection": {
            "base_score": 0.5,
            "score_modifiers": [],
            "requires_all_policies": bool(policies),
        },
        "tests": [f"{name}-test"],
    }
    return ModuleMetadata.from_mapping(module)


def dependency_modules() -> list[ModuleMetadata]:
    return [
        module_fixture("git-read", "tool", capability_class="tool_access"),
        module_fixture("filesystem-read", "tool", capability_class="tool_access"),
        module_fixture("test-runner", "tool", capability_class="tool_access"),
        module_fixture(
            "architecture-docs",
            "knowledge_scope",
            capability_class="knowledge_access",
        ),
        module_fixture(
            "coding-guidelines",
            "knowledge_scope",
            capability_class="knowledge_access",
        ),
        module_fixture(
            "repository-readonly",
            "data_scope",
            capability_class="data_access",
        ),
        module_fixture(
            "no-destructive-commands",
            "policy",
            capability_class="policy",
        ),
        module_fixture(
            "require-file-references",
            "policy",
            capability_class="policy",
        ),
        module_fixture(
            "review-findings-contract",
            "validator",
            capability_class="validation",
        ),
    ]


def registry_with_git_module_and_dependencies() -> InMemoryModuleRegistry:
    return InMemoryModuleRegistry(
        [
            ModuleMetadata.from_mapping(load_git_diff_module()),
            *dependency_modules(),
        ]
    )


def code_review_signals(*, phrases: list[str] | None = None) -> TaskSignals:
    return TaskSignals(
        task_type="code-review",
        risk_level="medium",
        domains=frozenset({"software-engineering", "git"}),
        available_inputs=frozenset({"repository", "diff"}),
        capability_hints=frozenset({"analysis"}),
        phrases=frozenset(phrases or ["review", "diff"]),
    )


def test_registry_discovers_candidates_by_structured_signals() -> None:
    registry = registry_with_git_module_and_dependencies()

    discovered = registry.discover(
        RegistryQuery(
            kinds=frozenset({"skill"}),
            capability_classes=frozenset({"analysis"}),
            domains=frozenset({"git"}),
            task_types=frozenset({"code-review"}),
            available_inputs=frozenset({"repository", "diff"}),
            require_available_inputs=True,
        )
    )

    assert [module.name for module in discovered] == ["git-diff-analysis"]


def test_registry_does_not_select_keyword_only_candidates_when_structured_signal_misses() -> None:
    keyword_only = module_fixture(
        "review-trigger-only",
        "skill",
        task_types=["deployment"],
        domains=["operations"],
        required_inputs=["release"],
    )
    registry = InMemoryModuleRegistry(
        [
            ModuleMetadata.from_mapping(load_git_diff_module()),
            keyword_only,
            *dependency_modules(),
        ]
    )

    discovered = registry.discover(
        RegistryQuery(
            kinds=frozenset({"skill"}),
            domains=frozenset({"git"}),
            task_types=frozenset({"code-review"}),
            available_inputs=frozenset({"repository", "diff"}),
            require_available_inputs=True,
        )
    )

    assert [module.name for module in discovered] == ["git-diff-analysis"]


def test_registry_scores_positive_and_negative_structured_evidence() -> None:
    registry = registry_with_git_module_and_dependencies()
    module = registry.resolve("git-diff-analysis", "0.1.0")

    positive_score = registry.score(module, code_review_signals())
    negative_score = registry.score(module, code_review_signals(phrases=["review", "deploy"]))

    assert positive_score.score == 1.0
    assert "task_type:code-review" in positive_score.matched_signals
    assert "input:diff" in positive_score.matched_signals
    assert negative_score.score == 0.75
    assert "phrase:deploy" in negative_score.negative_signals


def test_policy_filter_requires_explicit_policy_context() -> None:
    registry = registry_with_git_module_and_dependencies()
    module = registry.resolve("git-diff-analysis", "0.1.0")

    missing_policy_decision = registry.filter_candidate(module, PolicyContext())
    allowed_decision = registry.filter_candidate(
        module,
        PolicyContext(
            allowed_policy_ids=frozenset(
                {
                    "no-destructive-commands",
                    "require-file-references",
                }
            )
        ),
    )
    denied_decision = registry.filter_candidate(
        module,
        PolicyContext(denied_capability_classes=frozenset({"analysis"})),
    )

    assert missing_policy_decision.effect == "needs_clarification"
    assert "missing required policies" in missing_policy_decision.reasons[0]
    assert allowed_decision.effect == "allow"
    assert denied_decision.effect == "deny"


def test_registry_resolve_requires_available_pinned_version() -> None:
    registry = registry_with_git_module_and_dependencies()

    assert registry.resolve("git-diff-analysis", "0.1.0").name == "git-diff-analysis"
    with pytest.raises(UnknownModuleError, match="git-diff-analysis@9.9.9"):
        registry.resolve("git-diff-analysis", "9.9.9")


def test_graph_validation_accepts_complete_dependency_graph() -> None:
    registry = registry_with_git_module_and_dependencies()

    result = registry.validate_graph(["git-diff-analysis"])

    assert result.is_valid
    assert set(result.reachable_modules) >= {
        "git-diff-analysis",
        "git-read",
        "filesystem-read",
        "architecture-docs",
        "repository-readonly",
        "no-destructive-commands",
        "review-findings-contract",
    }


def test_graph_validation_rejects_missing_references() -> None:
    registry = InMemoryModuleRegistry([ModuleMetadata.from_mapping(load_git_diff_module())])

    result = registry.validate_graph(["git-diff-analysis"])

    assert not result.is_valid
    assert any("references missing tool: git-read" in error for error in result.errors)
    assert any(
        "references missing knowledge_scope: architecture-docs" in error
        for error in result.errors
    )


def test_graph_validation_rejects_wrong_reference_kind() -> None:
    wrong_kind_dependency = module_fixture(
        "git-read",
        "knowledge_scope",
        capability_class="knowledge_access",
    )
    registry = InMemoryModuleRegistry(
        [
            ModuleMetadata.from_mapping(load_git_diff_module()),
            wrong_kind_dependency,
            *[
                module
                for module in dependency_modules()
                if module.name != "git-read"
            ],
        ]
    )

    result = registry.validate_graph(["git-diff-analysis"])

    assert not result.is_valid
    assert any(
        "references git-read as tool, got knowledge_scope" in error
        for error in result.errors
    )


def test_graph_validation_rejects_circular_dependencies() -> None:
    skill = module_fixture("cycle-skill", "skill", policies=["cycle-policy"])
    policy = module_fixture(
        "cycle-policy",
        "policy",
        capability_class="policy",
        validators=["cycle-validator"],
    )
    validator = module_fixture(
        "cycle-validator",
        "validator",
        capability_class="validation",
        policies=["cycle-policy"],
    )
    registry = InMemoryModuleRegistry([skill, policy, validator])

    result = registry.validate_graph(["cycle-skill"])

    assert not result.is_valid
    assert any(
        "circular dependency: cycle-policy -> cycle-validator -> cycle-policy" in error
        for error in result.errors
    )


def test_graph_validation_rejects_denied_transitive_capability() -> None:
    registry = registry_with_git_module_and_dependencies()

    result = registry.validate_graph(
        ["git-diff-analysis"],
        PolicyContext(denied_capability_classes=frozenset({"tool_access"})),
    )

    assert not result.is_valid
    assert any(
        "reachable module filesystem-read uses denied capability" in error
        for error in result.errors
    )


def test_registry_loads_modules_from_paths() -> None:
    registry = InMemoryModuleRegistry.from_paths([GIT_DIFF_MODULE_PATH])

    assert registry.resolve("git-diff-analysis").version == "0.1.0"


def test_duplicate_module_versions_are_rejected() -> None:
    module_data = load_git_diff_module()
    duplicate = deepcopy(module_data)

    with pytest.raises(ValueError, match="Duplicate module version"):
        InMemoryModuleRegistry(
            [
                ModuleMetadata.from_mapping(module_data),
                ModuleMetadata.from_mapping(duplicate),
            ]
        )
