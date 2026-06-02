from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from skill_centric_agent_system.runtime import (
    FlightRecorder,
    InMemoryRuntimeStore,
    JsonArtifactStore,
    RuntimeProfileEnforcer,
    ToolDeniedError,
    ToolGateway,
    build_capability_gap_candidate,
    capture_capability_gap_candidate,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "capability-gap-candidate.schema.json"
PROFILE_EXAMPLE_PATH = REPO_ROOT / "examples" / "profiles" / "code-review-profile.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_artifact(root: Path, uri: str) -> dict[str, Any]:
    artifact_path = root / Path(uri.removeprefix("hetzner://runtime/"))
    return load_json(artifact_path)


def test_capability_gap_candidate_schema_accepts_runtime_candidate() -> None:
    schema = load_json(SCHEMA_PATH)
    candidate = build_capability_gap_candidate(
        run_id="run-code-review",
        profile_id="profile-code-review",
        source_step_id="step-executor-1",
        blocking_predicate="tool_not_in_runtime_profile",
        requested_capability_kind="tool",
        requested_capability_id="git-read",
        stop_reason="policy_denied",
        evidence_uris=("hetzner://runtime/events/run-code-review/access-denied.json",),
        known_capability_ids=("git-read",),
    )

    assert candidate is not None
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(candidate)
    assert candidate["learning_status"] == "review_required"
    assert candidate["executable"] is False


def test_capability_gap_candidate_excludes_secret_denials(tmp_path: Path) -> None:
    result = capture_capability_gap_candidate(
        artifacts=JsonArtifactStore(tmp_path),
        run_id="run-secret",
        profile_id="profile-secret",
        source_step_id="step-secret",
        blocking_predicate="data_scope_not_in_runtime_profile",
        requested_capability_kind="data_scope",
        requested_capability_id="customer-secrets",
        stop_reason="policy_denied",
        evidence_uris=("hetzner://runtime/events/run-secret/access-denied.json",),
        sensitivity="secret",
    )

    assert not result.captured
    assert result.skipped_reason == "denial is not eligible for capability-gap learning"


def test_capability_gap_candidate_excludes_unknown_tools() -> None:
    candidate = build_capability_gap_candidate(
        run_id="run-unknown-tool",
        profile_id="profile-unknown-tool",
        source_step_id="step-executor-1",
        blocking_predicate="tool_not_in_runtime_profile",
        requested_capability_kind="tool",
        requested_capability_id="unknown-shell",
        stop_reason="policy_denied",
        evidence_uris=("hetzner://runtime/events/run-unknown-tool/access-denied.json",),
        known_capability_ids=("git-read", "filesystem-read"),
    )

    assert candidate is None


def test_tool_gateway_emits_gap_candidate_for_known_tool_denial(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    artifact_root = tmp_path / "artifacts"
    recorder = FlightRecorder(store, JsonArtifactStore(artifact_root))
    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["tools"] = ["filesystem-read"]
    run = recorder.start_run(task_id="task-code-review-latest-commit", profile=profile)
    step = recorder.start_step(run_id=str(run["id"]), step_index=0, kind="executor")
    gateway = ToolGateway(
        profile=profile,
        run_id=str(run["id"]),
        step_id=str(step["id"]),
        recorder=recorder,
        repository_root=REPO_ROOT,
    )

    with pytest.raises(ToolDeniedError):
        gateway.invoke("git-read", {"args": ["status", "--short"]})

    access_result = load_artifact(artifact_root, str(store.runtime_events[-1]["result_uri"]))
    candidate_uri = access_result["capability_gap_candidate_uri"]
    candidate = load_artifact(artifact_root, candidate_uri)
    Draft202012Validator(load_json(SCHEMA_PATH)).validate(candidate)
    assert candidate["blocking_predicate"] == "tool_not_in_runtime_profile"
    assert candidate["requested_capability"] == {"kind": "tool", "id": "git-read"}
    assert candidate["source_run_id"] == run["id"]
    assert candidate["source_profile_id"] == profile["id"]
    assert candidate["source_step_id"] == step["id"]
    assert candidate["executable"] is False


def test_tool_gateway_does_not_emit_gap_candidate_for_unknown_tool(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    artifact_root = tmp_path / "artifacts"
    recorder = FlightRecorder(store, JsonArtifactStore(artifact_root))
    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["tools"] = []
    run = recorder.start_run(task_id="task-code-review-latest-commit", profile=profile)
    step = recorder.start_step(run_id=str(run["id"]), step_index=0, kind="executor")
    gateway = ToolGateway(
        profile=profile,
        run_id=str(run["id"]),
        step_id=str(step["id"]),
        recorder=recorder,
        repository_root=REPO_ROOT,
    )

    with pytest.raises(ToolDeniedError):
        gateway.invoke("unknown-shell", {})

    access_result = load_artifact(artifact_root, str(store.runtime_events[-1]["result_uri"]))
    assert "capability_gap_candidate_uri" not in access_result


def test_budget_denial_can_be_captured_without_mutating_profile() -> None:
    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["limits"]["max_tokens"] = 1
    enforcer = RuntimeProfileEnforcer(profile)

    with pytest.raises(Exception) as exc_info:
        enforcer.consume_tokens(2)

    error = exc_info.value
    candidate = build_capability_gap_candidate(
        run_id="run-budget",
        profile_id=profile["id"],
        source_step_id="step-planner",
        blocking_predicate=error.code,
        requested_capability_kind="budget",
        requested_capability_id="max-tokens",
        stop_reason=error.stop_reason,
        evidence_uris=("hetzner://runtime/events/run-budget/budget-denied.json",),
    )

    assert candidate is not None
    assert candidate["requested_capability"] == {"kind": "budget", "id": "max-tokens"}
    assert candidate["executable"] is False
