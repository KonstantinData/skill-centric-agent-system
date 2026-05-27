from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from skill_centric_agent_system.runtime import (
    BUILTIN_SKILL_HANDLER_REGISTRY,
    InMemoryRuntimeStore,
    JsonArtifactStore,
    MinimalRuntimeLoop,
    ProfileEnforcementError,
    RuntimeEntryPoint,
    RuntimeLoopError,
    RuntimeProfileEnforcer,
    SkillHandler,
    SkillHandlerRegistrationError,
    SkillHandlerRegistry,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_EXAMPLE_PATH = REPO_ROOT / "examples" / "tasks" / "code-review-task.json"
PROFILE_EXAMPLE_PATH = REPO_ROOT / "examples" / "profiles" / "code-review-profile.json"
COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_artifact(root: Path, uri: str) -> dict[str, Any]:
    artifact_path = root / Path(uri.removeprefix("hetzner://runtime/"))
    return load_json(artifact_path)


def test_builtin_skill_handler_registry_resolves_profile_selected_version() -> None:
    profile = load_json(PROFILE_EXAMPLE_PATH)

    plan = BUILTIN_SKILL_HANDLER_REGISTRY.build_plan(
        profile,
        enforcer=RuntimeProfileEnforcer(profile),
    )

    assert plan.strategy == "code-review-readonly"
    assert plan.output_contract == "review-findings-contract"
    assert plan.skill_handlers == (
        {
            "name": "git-diff-analysis",
            "version": "0.1.0",
            "handler_id": "git-diff-analysis@0.1.0",
        },
    )
    assert [action["tool"] for action in plan.actions] == ["git-read", "filesystem-read"]


def test_builtin_skill_handler_registry_exposes_coverage_descriptors() -> None:
    handlers = BUILTIN_SKILL_HANDLER_REGISTRY.handlers()

    assert [handler.handler_id for handler in handlers] == [
        "dependency-audit@0.1.0",
        "document-synthesis@0.1.0",
        "general-task-summary@0.1.0",
        "git-diff-analysis@0.1.0",
        "research-context-synthesis@0.1.0",
        "task-execution-planning@0.1.0",
    ]
    assert all(
        descriptor["runtime_path"] == "src/skill_centric_agent_system/runtime/skill_handlers.py"
        for descriptor in (handler.descriptor() for handler in handlers)
    )
    assert all(handler.test_coverage for handler in handlers)


def test_profile_enforcer_denies_skill_not_selected_by_profile() -> None:
    profile = load_json(PROFILE_EXAMPLE_PATH)
    enforcer = RuntimeProfileEnforcer(profile)

    with pytest.raises(ProfileEnforcementError) as exc_info:
        enforcer.require_skill("task-execution-planning")

    assert exc_info.value.stop_reason == "policy_denied"
    assert exc_info.value.code == "skill_not_in_runtime_profile"


def test_skill_handler_registry_fails_closed_for_unknown_selected_skill() -> None:
    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["skills"] = ["unregistered-production-skill"]
    profile["module_versions"]["unregistered-production-skill"] = "0.1.0"

    with pytest.raises(ProfileEnforcementError) as exc_info:
        BUILTIN_SKILL_HANDLER_REGISTRY.build_plan(
            profile,
            enforcer=RuntimeProfileEnforcer(profile),
        )

    assert exc_info.value.stop_reason == "policy_denied"
    assert exc_info.value.code == "skill_handler_not_registered"


def test_skill_handler_registry_fails_closed_for_mismatched_version() -> None:
    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["module_versions"]["git-diff-analysis"] = "9.9.9"

    with pytest.raises(ProfileEnforcementError) as exc_info:
        BUILTIN_SKILL_HANDLER_REGISTRY.build_plan(
            profile,
            enforcer=RuntimeProfileEnforcer(profile),
        )

    assert exc_info.value.stop_reason == "policy_denied"
    assert exc_info.value.code == "skill_handler_version_mismatch"


def test_skill_handler_registry_rejects_duplicate_name_version() -> None:
    handler = SkillHandler(
        skill_name="example-skill",
        skill_version="0.1.0",
        strategy="example",
        output_contract="example-output-contract",
        build_actions=lambda profile: (),
    )

    with pytest.raises(SkillHandlerRegistrationError):
        SkillHandlerRegistry((handler, handler))


def test_runtime_loop_records_executed_skill_handler_binding(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
    )

    loop.run(start_result)

    planner_checkpoint = next(
        checkpoint for checkpoint in store.runtime_checkpoints if checkpoint["phase"] == "planner"
    )
    planner_payload = load_artifact(tmp_path, str(planner_checkpoint["state_uri"]))
    assert planner_payload["skill_handlers"] == [
        {
            "name": "git-diff-analysis",
            "version": "0.1.0",
            "handler_id": "git-diff-analysis@0.1.0",
        }
    ]


def test_runtime_loop_fails_closed_before_executor_for_unknown_skill_handler(
    tmp_path: Path,
) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )
    start_result.profile["skills"] = ["unregistered-production-skill"]
    start_result.profile["module_versions"]["unregistered-production-skill"] = "0.1.0"
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
    )

    with pytest.raises(RuntimeLoopError):
        loop.run(start_result)

    assert store.runtime_runs[start_result.run_id]["status"] == "failed"
    assert store.runtime_runs[start_result.run_id]["stop_reason"] == "policy_denied"
    assert store.tool_invocations == []


def test_document_synthesis_skill_handler_builds_no_tool_actions() -> None:
    profile = load_json(PROFILE_EXAMPLE_PATH)
    profile["skills"] = ["document-synthesis"]
    profile["module_versions"]["document-synthesis"] = "0.1.0"
    profile["validators"] = ["general-output-contract"]
    profile["module_versions"]["general-output-contract"] = "0.1.0"

    plan = BUILTIN_SKILL_HANDLER_REGISTRY.build_plan(
        profile,
        enforcer=RuntimeProfileEnforcer(profile),
    )

    assert plan.strategy == "document-synthesis"
    assert plan.output_contract == "general-output-contract"
    assert plan.actions == ()
    assert plan.skill_handlers == (
        {
            "name": "document-synthesis",
            "version": "0.1.0",
            "handler_id": "document-synthesis@0.1.0",
        },
    )


def test_dependency_audit_skill_handler_builds_expected_actions() -> None:
    profile = load_json(PROFILE_EXAMPLE_PATH)
    profile["skills"] = ["dependency-audit"]
    profile["module_versions"]["dependency-audit"] = "0.1.0"
    profile["validators"] = ["task-execution-output-contract"]
    profile["module_versions"]["task-execution-output-contract"] = "0.1.0"
    profile["tools"] = ["filesystem-list", "filesystem-read"]

    plan = BUILTIN_SKILL_HANDLER_REGISTRY.build_plan(
        profile,
        enforcer=RuntimeProfileEnforcer(profile),
    )

    assert plan.strategy == "dependency-audit-readonly"
    assert plan.output_contract == "task-execution-output-contract"
    assert [action["tool"] for action in plan.actions] == [
        "filesystem-list",
        "filesystem-read",
        "filesystem-read",
    ]
    assert plan.skill_handlers == (
        {
            "name": "dependency-audit",
            "version": "0.1.0",
            "handler_id": "dependency-audit@0.1.0",
        },
    )
