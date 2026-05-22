from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from skill_centric_agent_system.runtime import MemoryFeedbackError, MemoryFeedbackPipeline


class FakeMemoryClient:
    def __init__(self) -> None:
        self.requests: list[Mapping[str, Any]] = []

    def ingest_memory(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
        self.requests.append(request_body)
        return {
            "status": "succeeded",
            "memory_id": request_body["memory"]["id"],  # type: ignore[index]
        }


def approved_candidate() -> dict[str, Any]:
    return {
        "id": "memory-runtime-decision",
        "run_id": "run-code-review",
        "profile_id": "profile-code-review",
        "target_memory_scope_id": "mod-project-memory",
        "content_uri": "hetzner://runtime/traces/run-code-review/memory/candidate.json",
        "sensitivity": "internal",
        "retention_policy": "project-memory-180d",
        "validator_status": "approved",
        "policy_status": "approved",
    }


def test_memory_feedback_pipeline_submits_only_consolidated_approved_memory() -> None:
    client = FakeMemoryClient()
    pipeline = MemoryFeedbackPipeline(client)  # type: ignore[arg-type]

    response = pipeline.submit_candidate(
        approved_candidate(),
        consolidated_content={
            "summary": "Use Flight Recorder events for runtime reconstruction.",
        },
    )

    assert response == {
        "status": "succeeded",
        "memory_id": "memory-runtime-decision",
    }
    assert client.requests == [
        {
            "contract_version": "0.1.0",
            "memory": {
                "id": "memory-runtime-decision",
                "memory_scope_id": "mod-project-memory",
                "version": "0.1.0",
                "content": {
                    "summary": "Use Flight Recorder events for runtime reconstruction.",
                    "source_artifact_uri": "hetzner://runtime/traces/run-code-review/memory/candidate.json",
                },
                "source_run_id": "run-code-review",
                "source_profile_id": "profile-code-review",
                "sensitivity": "internal",
                "retention_policy": "project-memory-180d",
            },
        }
    ]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("validator_status", "pending", "validator_status"),
        ("policy_status", "rejected", "policy_status"),
    ],
)
def test_memory_feedback_pipeline_rejects_unapproved_candidates(
    field: str,
    value: str,
    message: str,
) -> None:
    client = FakeMemoryClient()
    pipeline = MemoryFeedbackPipeline(client)  # type: ignore[arg-type]
    candidate = approved_candidate()
    candidate[field] = value

    with pytest.raises(MemoryFeedbackError, match=message):
        pipeline.submit_candidate(candidate, consolidated_content={"summary": "not approved"})

    assert client.requests == []
