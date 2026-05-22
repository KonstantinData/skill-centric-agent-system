from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from skill_centric_agent_system.runtime.enforcement import (
    ProfileEnforcementError,
    RuntimeProfileEnforcer,
)


class RetrievalContextClient(Protocol):
    def retrieval_context(self, request_body: Mapping[str, Any]) -> dict[str, Any]: ...


class RuntimeContextManager:
    """Load only profile-authorized retrieval context for a runtime run."""

    def __init__(
        self,
        *,
        enforcer: RuntimeProfileEnforcer,
        control_plane_client: RetrievalContextClient | None = None,
        contract_version: str = "0.1.0",
        top_k: int = 5,
    ) -> None:
        self.enforcer = enforcer
        self.control_plane_client = control_plane_client
        self.contract_version = contract_version
        self.top_k = top_k

    def load(self, profile: Mapping[str, Any], *, query: str) -> dict[str, Any]:
        knowledge_scopes = tuple(str(scope) for scope in profile.get("knowledge_scopes", []))
        memory_scopes = tuple(str(scope) for scope in profile.get("memory_scopes", []))
        data_scopes = tuple(str(scope) for scope in profile.get("data_scopes", []))

        self.enforcer.require_knowledge_scopes(knowledge_scopes)
        self.enforcer.require_memory_scopes(memory_scopes)
        self.enforcer.require_data_scopes(data_scopes)

        request = {
            "contract_version": self.contract_version,
            "principal": _retrieval_principal(profile),
            "query": query,
            "knowledge_scope_ids": [_module_id(scope) for scope in knowledge_scopes],
            "memory_scope_ids": [_module_id(scope) for scope in memory_scopes],
            "top_k": self.top_k,
        }
        if self.control_plane_client is None:
            response = _empty_retrieval_response(request)
        else:
            response = self.control_plane_client.retrieval_context(request)
            _assert_retrieval_response_is_bounded(request, response)

        return {
            "profile_id": profile["id"],
            "instructions": profile["instructions"],
            "knowledge_scopes": list(knowledge_scopes),
            "memory_scopes": list(memory_scopes),
            "data_scopes": list(data_scopes),
            "retrieval_request": request,
            "retrieval_response": response,
            "knowledge_chunks": response.get("knowledge_chunks", []),
            "memory_records": response.get("memory_records", []),
        }


def _retrieval_principal(profile: Mapping[str, Any]) -> dict[str, str]:
    auth_context = profile.get("auth_context", {})
    if isinstance(auth_context, Mapping):
        roles = auth_context.get("roles", [])
        if isinstance(roles, list) and roles:
            return {"kind": "role", "id": str(roles[0])}
        principal = auth_context.get("principal", {})
        if isinstance(principal, Mapping):
            principal_type = str(principal.get("type", "user"))
            kind = "service" if principal_type == "service" else "user"
            return {"kind": kind, "id": str(principal.get("id", "unknown-principal"))}
    return {"kind": "user", "id": "unknown-principal"}


def _module_id(scope_name: str) -> str:
    return scope_name if scope_name.startswith("mod-") else f"mod-{scope_name}"


def _empty_retrieval_response(request: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": request["contract_version"],
        "retrieval_status": "not_requested",
        "query": request["query"],
        "vectorize": {
            "status": "d1_prefilter_ready",
            "knowledge_index": "scas-knowledge-dev",
            "memory_index": "scas-memory-dev",
            "bindings": {"knowledge": False, "memory": False},
            "note": "No Control Plane client was provided for retrieval.",
        },
        "allowed_knowledge_scope_ids": [],
        "allowed_memory_scope_ids": [],
        "knowledge_chunks": [],
        "memory_records": [],
        "vectorize_matches": {"knowledge": [], "memory": []},
    }


def _assert_retrieval_response_is_bounded(
    request: Mapping[str, Any],
    response: Mapping[str, Any],
) -> None:
    requested_knowledge = {str(scope) for scope in request.get("knowledge_scope_ids", [])}
    requested_memory = {str(scope) for scope in request.get("memory_scope_ids", [])}
    allowed_knowledge = {
        str(scope) for scope in response.get("allowed_knowledge_scope_ids", [])
    }
    allowed_memory = {str(scope) for scope in response.get("allowed_memory_scope_ids", [])}
    unexpected_knowledge = sorted(allowed_knowledge - requested_knowledge)
    unexpected_memory = sorted(allowed_memory - requested_memory)
    if unexpected_knowledge or unexpected_memory:
        raise ProfileEnforcementError(
            "Retrieval response included scopes outside the active runtime profile.",
            stop_reason="policy_denied",
            code="retrieval_response_scope_not_in_runtime_profile",
        )
