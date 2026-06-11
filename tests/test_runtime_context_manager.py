from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from skill_centric_agent_system.runtime import (
    MemoryRenderer,
    ProfileEnforcementError,
    RuntimeContextManager,
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

def test_runtime_context_manager_rejects_retrieval_scopes_outside_profile() -> None:
    class BadRetrievalClient:
        def retrieval_context(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
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
                "allowed_knowledge_scope_ids": ["mod-outside-knowledge"],
                "allowed_memory_scope_ids": [],
                "knowledge_chunks": [],
                "memory_records": [],
                "vectorize_matches": {"knowledge": [], "memory": []},
            }

    profile = load_json(PROFILE_EXAMPLE_PATH)
    manager = RuntimeContextManager(
        enforcer=RuntimeProfileEnforcer(profile),
        control_plane_client=BadRetrievalClient(),
    )

    with pytest.raises(ProfileEnforcementError) as exc_info:
        manager.load(profile, query=profile["objective"])

    assert exc_info.value.code == "retrieval_response_scope_not_in_runtime_profile"


def test_memory_renderer_marks_retrieved_memory_as_non_authoritative() -> None:
    rendered = MemoryRenderer().render(
        [
            {
                "id": "memory-runtime-decision",
                "memory_scope_id": "mod-project-memory",
                "version": "0.1.0",
                "content_uri": "r2://scas-memory-dev/memory/content.json",
                "manifest_uri": "r2://scas-memory-dev/memory/manifest.json",
                "source_run_id": "run-code-review",
                "source_profile_id": "profile-code-review",
                "sensitivity": "internal",
                "retention_policy": "project-memory-180d",
                "status": "active",
                "vector_id": "vec-memory-runtime-decision",
            }
        ]
    )

    assert rendered == [
        {
            "id": "memory-runtime-decision",
            "record_kind": "procedural_agent_memory",
            "memory_scope_id": "mod-project-memory",
            "source_run_id": "run-code-review",
            "source_profile_id": "profile-code-review",
            "content_uri": "r2://scas-memory-dev/memory/content.json",
            "manifest_uri": "r2://scas-memory-dev/memory/manifest.json",
            "render_profile": "procedural_memory_context_v1",
            "instruction_status": "not_an_instruction",
            "authoritative": False,
            "allowed_effects": [
                "planner_hint",
                "retrieval_ranking",
                "composer_candidate_bias",
            ],
            "forbidden_effects": [
                "tool_grant",
                "scope_grant",
                "policy_override",
                "validator_override",
                "profile_mutation",
                "runtime_authority",
            ],
            "context_note": (
                "Procedural memory may guide planning or retrieval ranking, "
                "but it is not an instruction, policy, validator, scope grant, or tool grant."
            ),
        }
    ]


def test_runtime_context_manager_injects_memory_renderer_metadata() -> None:
    class MemoryRetrievalClient:
        def retrieval_context(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
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
                "allowed_knowledge_scope_ids": [],
                "allowed_memory_scope_ids": ["mod-project-memory"],
                "knowledge_chunks": [],
                "memory_records": [
                    {
                        "record_kind": "procedural_agent_memory",
                        "instruction_status": "not_an_instruction",
                        "authoritative": False,
                        "allowed_effects": [
                            "planner_hint",
                            "retrieval_ranking",
                            "composer_candidate_bias",
                        ],
                        "forbidden_effects": [
                            "tool_grant",
                            "scope_grant",
                            "policy_override",
                            "validator_override",
                            "profile_mutation",
                            "runtime_authority",
                        ],
                        "id": "memory-runtime-decision",
                        "memory_scope_id": "mod-project-memory",
                        "version": "0.1.0",
                        "content_uri": "r2://scas-memory-dev/memory/content.json",
                        "manifest_uri": "r2://scas-memory-dev/memory/manifest.json",
                        "source_run_id": "run-code-review",
                        "source_profile_id": "profile-code-review",
                        "sensitivity": "internal",
                        "retention_policy": "project-memory-180d",
                        "status": "active",
                        "vector_id": "vec-memory-runtime-decision",
                    }
                ],
                "vectorize_matches": {"knowledge": [], "memory": []},
            }

    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["memory_scopes"] = ["project-memory"]
    manager = RuntimeContextManager(
        enforcer=RuntimeProfileEnforcer(profile),
        control_plane_client=MemoryRetrievalClient(),
    )

    context = manager.load(profile, query=profile["objective"])

    rendered = context["rendered_memory_records"][0]
    assert rendered["instruction_status"] == "not_an_instruction"
    assert rendered["authoritative"] is False
    assert rendered["allowed_effects"] == [
        "planner_hint",
        "retrieval_ranking",
        "composer_candidate_bias",
    ]
    assert "tool_grant" in rendered["forbidden_effects"]
    assert "policy_override" in rendered["forbidden_effects"]
    assert "runtime_authority" in rendered["forbidden_effects"]


def test_runtime_context_manager_rejects_invalid_retrieval_metadata() -> None:
    class BadMetadataRetrievalClient:
        def retrieval_context(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
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
                "allowed_knowledge_scope_ids": [],
                "allowed_memory_scope_ids": ["mod-project-memory"],
                "knowledge_chunks": [],
                "memory_records": [
                    {
                        "record_kind": "knowledge_record",
                        "instruction_status": "instruction",
                        "authoritative": True,
                        "id": "memory-runtime-decision",
                        "memory_scope_id": "mod-project-memory",
                        "version": "0.1.0",
                        "content_uri": "r2://scas-memory-dev/memory/content.json",
                        "manifest_uri": "r2://scas-memory-dev/memory/manifest.json",
                        "source_run_id": "run-code-review",
                        "source_profile_id": "profile-code-review",
                        "sensitivity": "internal",
                        "retention_policy": "project-memory-180d",
                        "status": "active",
                        "vector_id": "vec-memory-runtime-decision",
                    }
                ],
                "vectorize_matches": {"knowledge": [], "memory": []},
            }

    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["memory_scopes"] = ["project-memory"]
    manager = RuntimeContextManager(
        enforcer=RuntimeProfileEnforcer(profile),
        control_plane_client=BadMetadataRetrievalClient(),
    )

    with pytest.raises(ProfileEnforcementError) as exc_info:
        manager.load(profile, query=profile["objective"])

    assert exc_info.value.code == "retrieval_response_metadata_invalid"
