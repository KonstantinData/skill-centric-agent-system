from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from skill_centric_agent_system.composition import CompositionError
from skill_centric_agent_system.runtime import (
    InMemoryRuntimeStore,
    JsonArtifactStore,
    MinimalRuntimeLoop,
    RuntimeEntryPoint,
    RuntimeLoopError,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TENANT_RESEARCH_CONTEXT_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response-tenant-research.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
                "control_plane_principal_kind": "user",
                "control_plane_principal_id": "tenant-user",
                "role_data_sources": ["demo-tenant-website"],
                "role_capabilities": ["research"],
            }
        },
    }


class TenantE2EControlPlaneClient:
    def __init__(self, composition_response: Mapping[str, Any] | None = None) -> None:
        self.composition_requests: list[Mapping[str, Any]] = []
        self.retrieval_requests: list[Mapping[str, Any]] = []
        self.composition_response = composition_response or load_json(TENANT_RESEARCH_CONTEXT_PATH)

    def composition_context(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
        self.composition_requests.append(deepcopy(dict(request_body)))
        return deepcopy(dict(self.composition_response))

    def retrieval_context(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
        self.retrieval_requests.append(deepcopy(dict(request_body)))
        return {
            "contract_version": "0.1.0",
            "retrieval_status": "ready",
            "query": request_body["query"],
            "vectorize": {
                "status": "d1_prefilter_ready",
                "knowledge_index": "scas-knowledge-dev",
                "memory_index": "scas-memory-dev",
                "bindings": {"knowledge": True, "memory": True},
                "note": "Tenant E2E fixture response.",
            },
            "allowed_knowledge_scope_ids": list(request_body["knowledge_scope_ids"]),
            "allowed_memory_scope_ids": list(request_body["memory_scope_ids"]),
            "knowledge_chunks": [
                {
                    "record_kind": "knowledge_record",
                    "context_kind": "factual_knowledge",
                    "id": "chunk-demo-tenant-knowledge-0",
                    "document_id": "knowledge-doc-demo-tenant",
                    "scope_id": "mod-knowledge-demo-tenant-docs",
                    "vector_id": "vec-demo-tenant-knowledge-0",
                    "content_uri": (
                        "hetzner://runtime/tenant-e2e/demo-tenant/knowledge/chunk-0.json"
                    ),
                }
            ],
            "memory_records": [],
            "vectorize_matches": {"knowledge": [], "memory": []},
        }


def test_tenant_scoped_runtime_e2e_starts_and_completes_with_control_plane_client(
    tmp_path: Path,
) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    control_plane = TenantE2EControlPlaneClient()
    entrypoint = RuntimeEntryPoint(
        store=store,
        artifacts=artifacts,
        control_plane_client=control_plane,
    )

    start_result = entrypoint.start(tenant_research_task())
    result = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
        control_plane_client=control_plane,
    ).run(start_result)

    assert result.status == "succeeded"
    assert result.stop_reason == "completed"
    assert start_result.composition_context_request["principal"] == {
        "kind": "user",
        "id": "tenant-user",
    }
    assert start_result.composition_context_request["tenant_context"] == {
        "tenant_id": "demo-tenant",
        "area_id": "demo-tenant",
        "hostname": "demo-tenant.example.invalid",
        "membership_id": "demo-tenant-membership-user",
    }
    assert control_plane.composition_requests == [start_result.composition_context_request]
    assert control_plane.retrieval_requests
    assert control_plane.retrieval_requests[0]["knowledge_scope_ids"] == [
        "mod-knowledge-demo-tenant-docs"
    ]
    assert control_plane.retrieval_requests[0]["memory_scope_ids"] == []
    assert start_result.profile["tenant_context"]["tenant_id"] == "demo-tenant"
    assert start_result.profile["tenant_authority"]["membership"]["id"] == (
        "demo-tenant-membership-user"
    )
    assert result.response["runtime_output"]["task_type"] == "research"
    assert result.response["runtime_output"]["details"]["key_points"] == [
        "Loaded 1 knowledge chunk(s) and 0 memory record(s) through the Control API "
        "retrieval boundary."
    ]
    assert store.runtime_runs[result.run_id]["status"] == "succeeded"
    assert store.runtime_runs[result.run_id]["stop_reason"] == "completed"


def test_tenant_scoped_runtime_e2e_denies_missing_membership_before_run_start(
    tmp_path: Path,
) -> None:
    response = load_json(TENANT_RESEARCH_CONTEXT_PATH)
    response["composition_status"] = "denied"
    response.pop("tenant_authority")
    store = InMemoryRuntimeStore()
    control_plane = TenantE2EControlPlaneClient(response)
    entrypoint = RuntimeEntryPoint(
        store=store,
        artifacts=JsonArtifactStore(tmp_path),
        control_plane_client=control_plane,
    )

    with pytest.raises(CompositionError, match="not ready"):
        entrypoint.start(tenant_research_task())

    assert control_plane.composition_requests
    assert store.runtime_runs == {}


def test_tenant_scoped_runtime_e2e_denies_cross_tenant_authority_before_run_start(
    tmp_path: Path,
) -> None:
    response = load_json(TENANT_RESEARCH_CONTEXT_PATH)
    response["tenant_authority"]["tenant_id"] = "other-tenant"
    store = InMemoryRuntimeStore()
    control_plane = TenantE2EControlPlaneClient(response)
    entrypoint = RuntimeEntryPoint(
        store=store,
        artifacts=JsonArtifactStore(tmp_path),
        control_plane_client=control_plane,
    )

    with pytest.raises(CompositionError, match="does not match the analyzed tenant"):
        entrypoint.start(tenant_research_task())

    assert store.runtime_runs == {}


def test_tenant_scoped_runtime_e2e_denies_tampered_profile_before_execution_steps(
    tmp_path: Path,
) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    control_plane = TenantE2EControlPlaneClient()
    entrypoint = RuntimeEntryPoint(
        store=store,
        artifacts=artifacts,
        control_plane_client=control_plane,
    )
    start_result = entrypoint.start(tenant_research_task())
    start_result.profile["knowledge_scopes"].append("other-tenant-knowledge")
    start_result.profile["module_versions"]["other-tenant-knowledge"] = "0.1.0"

    with pytest.raises(RuntimeLoopError) as error:
        MinimalRuntimeLoop(
            store=store,
            artifacts=artifacts,
            repository_root=REPO_ROOT,
            control_plane_client=control_plane,
        ).run(start_result)

    assert error.value.stop_reason == "policy_denied"
    assert store.runtime_runs[start_result.run_id]["status"] == "failed"
    assert store.runtime_runs[start_result.run_id]["stop_reason"] == "policy_denied"
    assert store.runtime_steps == {}
    assert [event["event_type"] for event in store.runtime_events][-1] == "runtime_failed"
