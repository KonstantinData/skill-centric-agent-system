from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from skill_centric_agent_system.composition import RuntimeProfileComposer, TaskAnalyzer
from skill_centric_agent_system.runtime import (
    InMemoryRuntimeStore,
    JsonArtifactStore,
    MinimalRuntimeLoop,
    ProfileEnforcementError,
    RuntimeEntryPoint,
    RuntimeProfileEnforcer,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_EXAMPLE_PATH = REPO_ROOT / "examples" / "tasks" / "code-review-task.json"
PROFILE_EXAMPLE_PATH = REPO_ROOT / "examples" / "profiles" / "code-review-profile.json"
COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response.json"
)
RESEARCH_TASK_EXAMPLE_PATH = REPO_ROOT / "examples" / "tasks" / "research-task.json"
TASK_EXECUTION_TASK_EXAMPLE_PATH = (
    REPO_ROOT / "examples" / "tasks" / "task-execution-task.json"
)
GENERAL_TASK_EXAMPLE_PATH = REPO_ROOT / "examples" / "tasks" / "general-task.json"
RESEARCH_COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response-research.json"
)
TENANT_RESEARCH_COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response-tenant-research.json"
)
TASK_EXECUTION_COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response-task-execution.json"
)
GENERAL_COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response-general-task.json"
)
RUNTIME_PLANE_SCHEMA_PATH = REPO_ROOT / "schemas" / "hetzner-runtime-plane.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_artifact(root: Path, uri: str) -> dict[str, Any]:
    artifact_path = root / Path(uri.removeprefix("hetzner://runtime/"))
    return load_json(artifact_path)


def tenant_research_task() -> dict[str, Any]:
    return {
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


def tenant_research_profile() -> dict[str, Any]:
    analyzed = TaskAnalyzer().analyze(tenant_research_task())
    return RuntimeProfileComposer().compose(
        analyzed,
        load_json(TENANT_RESEARCH_COMPOSITION_CONTEXT_RESPONSE_PATH),
    )


def test_profile_enforcer_denies_unselected_knowledge_and_memory_scopes() -> None:
    profile = load_json(PROFILE_EXAMPLE_PATH)
    enforcer = RuntimeProfileEnforcer(profile)

    with pytest.raises(ProfileEnforcementError) as knowledge_error:
        enforcer.require_knowledge_scopes(["outside-knowledge"])
    with pytest.raises(ProfileEnforcementError) as memory_error:
        enforcer.require_memory_scopes(["project-memory"])

    assert knowledge_error.value.stop_reason == "policy_denied"
    assert knowledge_error.value.code == "knowledge_scope_not_in_runtime_profile"
    assert memory_error.value.stop_reason == "policy_denied"
    assert memory_error.value.code == "memory_scope_not_in_runtime_profile"


def test_profile_enforcer_accepts_tenant_authority_sealed_profile() -> None:
    profile = tenant_research_profile()
    enforcer = RuntimeProfileEnforcer(profile)

    enforcer.validate_profile_for_runtime()

    assert profile["tenant_authority"]["tenant_id"] == "demo-tenant"
    assert profile["tenant_authority"]["direct_user_grants_allowed"] is False


@pytest.mark.parametrize(
    ("mutator", "expected_code"),
    [
        (
            lambda profile: profile.pop("tenant_authority"),
            "tenant_authority_missing",
        ),
        (
            lambda profile: profile["tenant_authority"].__setitem__(
                "tenant_id",
                "other-tenant",
            ),
            "tenant_authority_tenant_mismatch",
        ),
        (
            lambda profile: profile["tenant_authority"]["hostname"].__setitem__(
                "hostname",
                "other-tenant.example.invalid",
            ),
            "tenant_hostname_authority_mismatch",
        ),
        (
            lambda profile: profile["tenant_context"]["role_ids"].append(
                "demo-tenant-admin",
            ),
            "tenant_role_not_in_membership",
        ),
        (
            lambda profile: (
                profile["skills"].append("unapproved-skill"),
                profile["module_versions"].__setitem__("unapproved-skill", "0.1.0"),
            ),
            "tenant_skill_denied",
        ),
        (
            lambda profile: (
                profile["knowledge_scopes"].append("outside-knowledge"),
                profile["module_versions"].__setitem__("outside-knowledge", "0.1.0"),
            ),
            "tenant_knowledge_scope_denied",
        ),
        (
            lambda profile: (
                profile["data_scopes"].append("other-tenant-website-read"),
                profile["module_versions"].__setitem__("other-tenant-website-read", "0.1.0"),
            ),
            "tenant_data_scope_denied",
        ),
        (
            lambda profile: profile["tenant_context"]["role_derivation"].__setitem__(
                "direct_user_grants_allowed",
                True,
            ),
            "tenant_direct_user_grants_enabled",
        ),
        (
            lambda profile: profile["tenant_authority"]["membership"].__setitem__(
                "principal_id",
                "other-user",
            ),
            "tenant_membership_principal_mismatch",
        ),
    ],
)
def test_profile_enforcer_fails_closed_for_invalid_tenant_authority_profile(
    mutator: Any,
    expected_code: str,
) -> None:
    profile = tenant_research_profile()
    mutator(profile)
    enforcer = RuntimeProfileEnforcer(profile)

    with pytest.raises(ProfileEnforcementError) as error:
        enforcer.validate_profile_for_runtime()

    assert error.value.stop_reason == "policy_denied"
    assert error.value.code == expected_code


def test_profile_enforcer_rejects_global_profile_with_tenant_authority() -> None:
    profile = load_json(PROFILE_EXAMPLE_PATH)
    profile["tenant_authority"] = load_json(TENANT_RESEARCH_COMPOSITION_CONTEXT_RESPONSE_PATH)[
        "tenant_authority"
    ]
    enforcer = RuntimeProfileEnforcer(profile)

    with pytest.raises(ProfileEnforcementError) as error:
        enforcer.validate_profile_for_runtime()

    assert error.value.code == "global_tenant_authority_present"


def test_profile_enforcer_enforces_token_and_memory_budgets() -> None:
    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["limits"]["max_tokens"] = 1
    profile["limits"]["max_memory_ops"] = 0
    token_enforcer = RuntimeProfileEnforcer(profile)
    memory_enforcer = RuntimeProfileEnforcer(profile)

    with pytest.raises(ProfileEnforcementError) as token_error:
        token_enforcer.consume_tokens(2)
    with pytest.raises(ProfileEnforcementError) as memory_error:
        memory_enforcer.record_memory_op()

    assert token_error.value.stop_reason == "max_tokens"
    assert memory_error.value.stop_reason == "max_memory_ops"


def test_minimal_runtime_loop_executes_profile_scoped_read_tools(tmp_path: Path) -> None:
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

    result = loop.run(start_result)

    assert result.status == "succeeded"
    assert result.response["error_classification"]["error_class"] in {
        "NONE",
        "F1_INEFFICIENCY_PATH",
    }
    assert store.runtime_runs[result.run_id]["status"] == "succeeded"
    assert store.runtime_runs[result.run_id]["stop_reason"] == "completed"
    assert [step["kind"] for step in store.runtime_steps.values()] == [
        "context",
        "planner",
        "executor",
        "validator",
    ]
    assert [invocation["tool_name"] for invocation in store.tool_invocations] == [
        "git-read",
        "filesystem-read",
    ]
    assert [result["validator_id"] for result in store.validation_results] == [
        "runtime-profile-schema",
        "review-findings-contract",
    ]
    assert [result["status"] for result in store.validation_results] == [
        "passed",
        "passed",
    ]

    event_types = [event["event_type"] for event in store.runtime_events]
    assert "runtime_started" in event_types
    assert "tool_invocation_started" in event_types
    assert "tool_invocation_completed" in event_types
    assert event_types[-1] == "runtime_completed"

    recordset = store.as_runtime_plane_recordset()
    Draft202012Validator(load_json(RUNTIME_PLANE_SCHEMA_PATH)).validate(recordset)


def test_minimal_runtime_loop_loads_retrieval_context_through_control_plane(
    tmp_path: Path,
) -> None:
    class FakeRetrievalClient:
        def __init__(self) -> None:
            self.requests: list[Mapping[str, Any]] = []

        def retrieval_context(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
            self.requests.append(dict(request_body))
            return {
                "contract_version": "0.1.0",
                "retrieval_status": "ready",
                "query": request_body["query"],
                "vectorize": {
                    "status": "d1_prefilter_ready",
                    "knowledge_index": "scas-knowledge-dev",
                    "memory_index": "scas-memory-dev",
                    "bindings": {"knowledge": True, "memory": True},
                    "note": "D1 prefilter only.",
                },
                "allowed_knowledge_scope_ids": list(request_body["knowledge_scope_ids"]),
                "allowed_memory_scope_ids": list(request_body["memory_scope_ids"]),
                "knowledge_chunks": [],
                "memory_records": [],
                "vectorize_matches": {"knowledge": [], "memory": []},
            }

    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    client = FakeRetrievalClient()
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
        control_plane_client=client,
    )

    loop.run(start_result)

    assert client.requests
    request = client.requests[0]
    assert request["principal"] == {"kind": "role", "id": "repository-maintainer"}
    assert request["knowledge_scope_ids"] == [
        "mod-architecture-docs",
        "mod-coding-guidelines",
    ]
    assert request["memory_scope_ids"] == []
    context_checkpoint = next(
        checkpoint for checkpoint in store.runtime_checkpoints if checkpoint["phase"] == "context"
    )
    context_payload = load_artifact(tmp_path, str(context_checkpoint["state_uri"]))
    assert context_payload["retrieval_response"]["retrieval_status"] == "ready"


def test_postgres_runtime_store_uses_uri_tool_and_validation_payloads() -> None:
    class FakeConnection:
        def __init__(self) -> None:
            self.calls: list[tuple[str, Mapping[str, Any] | None]] = []

        def execute(self, sql: str, params: Mapping[str, Any] | None = None) -> Any:
            self.calls.append((sql, params))
            return self

        def fetchall(self) -> list[Mapping[str, Any]]:
            return []

    from skill_centric_agent_system.runtime.storage import PostgresRuntimeStore

    fake = FakeConnection()
    store = PostgresRuntimeStore(fake)
    store.insert_tool_invocation(
        {
            "id": "tool-example",
            "run_id": "run-example",
            "step_id": "step-example",
            "tool_name": "git-read",
            "status": "succeeded",
            "input_uri": "hetzner://runtime/tool/input.json",
            "output_uri": "hetzner://runtime/tool/output.json",
            "started_at": "2026-05-22T08:00:00Z",
            "completed_at": "2026-05-22T08:00:01Z",
        }
    )
    store.insert_validation_result(
        {
            "id": "validation-example",
            "run_id": "run-example",
            "step_id": "step-example",
            "validator_id": "review-findings-contract",
            "status": "passed",
            "findings_uri": "hetzner://runtime/findings.json",
            "created_at": "2026-05-22T08:00:02Z",
        }
    )
    store.insert_memory_candidate(
        {
            "id": "mc-example",
            "run_id": "run-example",
            "profile_id": "profile-example",
            "source_step_id": "step-example",
            "target_memory_scope_id": "mod-project-memory",
            "candidate_class": "procedural_lesson",
            "classification_reason": "Fixture captures a reusable runtime lesson.",
            "content_uri": "hetzner://runtime/memory/candidate.json",
            "sensitivity": "internal",
            "retention_policy": "project-memory-180d",
            "validator_status": "pending",
            "validator_id": "memory-candidate-contract",
            "policy_status": "pending",
            "policy_id": "mod-no-destructive-commands",
            "created_at": "2026-05-22T08:00:03Z",
        }
    )
    store.update_memory_candidate(
        "mc-example",
        {
            "validator_status": "approved",
            "validation_reason": "passed",
            "policy_status": "approved",
            "policy_reason": "allowed",
        },
    )

    sql = "\n".join(call[0] for call in fake.calls)
    assert "input_uri" in sql
    assert "output_uri" in sql
    assert "findings_uri" in sql
    assert "validation_reason" in sql
    assert "policy_reason" in sql
    assert "input_json" not in sql
    assert "output_json" not in sql
    assert "findings_json" not in sql


@pytest.mark.parametrize(
    ("task_path", "context_response_path", "expected_task_type", "expected_validator"),
    [
        (
            RESEARCH_TASK_EXAMPLE_PATH,
            RESEARCH_COMPOSITION_CONTEXT_RESPONSE_PATH,
            "research",
            "research-output-contract",
        ),
        (
            TASK_EXECUTION_TASK_EXAMPLE_PATH,
            TASK_EXECUTION_COMPOSITION_CONTEXT_RESPONSE_PATH,
            "task-execution",
            "task-execution-output-contract",
        ),
        (
            GENERAL_TASK_EXAMPLE_PATH,
            GENERAL_COMPOSITION_CONTEXT_RESPONSE_PATH,
            "general-task",
            "general-output-contract",
        ),
    ],
)
def test_minimal_runtime_loop_dispatches_task_type_strategies(
    tmp_path: Path,
    task_path: Path,
    context_response_path: Path,
    expected_task_type: str,
    expected_validator: str,
) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        load_json(task_path),
        composition_context_response=load_json(context_response_path),
    )
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
    )

    result = loop.run(start_result)

    assert result.status == "succeeded"
    assert result.response["task_type"] == expected_task_type
    assert result.response["runtime_output"]["task_type"] == expected_task_type
    assert result.response["runtime_output"]["status"] == "completed"
    assert expected_validator in [record["validator_id"] for record in store.validation_results]
    validator_record = next(
        record
        for record in store.validation_results
        if record["validator_id"] == expected_validator
    )
    assert validator_record["status"] == "passed"
