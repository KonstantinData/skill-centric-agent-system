from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "release" / "build_production_readiness_evidence.py"


def load_evidence_module():
    spec = importlib.util.spec_from_file_location("production_readiness_evidence", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


evidence = load_evidence_module()

REPOSITORY = "KonstantinData/skill-centric-agent-system"
COMMIT = "a" * 40
LIVE_RUN_URL = f"https://github.com/{REPOSITORY}/actions/runs/123456789"
AI_GATEWAY_RUN_URL = f"https://github.com/{REPOSITORY}/actions/runs/987654321"


def run_metadata(
    *,
    run_id: int,
    workflow_name: str,
    url: str,
    head_sha: str = COMMIT,
    status: str = "completed",
    conclusion: str = "success",
) -> dict[str, object]:
    return {
        "databaseId": run_id,
        "workflowName": workflow_name,
        "status": status,
        "conclusion": conclusion,
        "headSha": head_sha,
        "url": url,
        "event": "workflow_dispatch",
        "displayTitle": "Release evidence run",
        "createdAt": "2026-05-24T13:00:00Z",
        "updatedAt": "2026-05-24T13:10:00Z",
    }


def live_handler_binding_evidence() -> dict[str, object]:
    return {
        "status": "passed",
        "handler_binding_status": "passed",
        "task_suite": "generic",
        "case_count": 1,
        "results": [
            {
                "case": "code-review",
                "status": "passed",
                "run_id": "run-live-123-code-review",
                "task_type": "code-review",
                "profile_id": "profile-code-review",
                "handler_binding_status": "passed",
                "planner_checkpoint_uri": (
                    "hetzner://runtime/traces/run-live-123-code-review/"
                    "checkpoints/001-planner.json"
                ),
                "skill_handlers": [
                    {
                        "name": "git-diff-analysis",
                        "version": "0.1.0",
                        "handler_id": "git-diff-analysis@0.1.0",
                    }
                ],
            }
        ],
    }


def test_parse_actions_run_url_requires_same_repository() -> None:
    parsed = evidence.parse_actions_run_url(LIVE_RUN_URL, REPOSITORY)

    assert parsed.repository == REPOSITORY
    assert parsed.run_id == "123456789"
    assert parsed.url == LIVE_RUN_URL

    with pytest.raises(evidence.EvidenceError, match="does not match expected repository"):
        evidence.parse_actions_run_url(
            "https://github.com/Other/repo/actions/runs/123456789",
            REPOSITORY,
        )


def test_evidence_only_dev_records_initial_productive_core() -> None:
    payload = evidence.build_evidence(
        repository=REPOSITORY,
        commit=COMMIT,
        workflow_run_id="111",
        workflow_run_attempt="1",
        target_environment="dev",
        release_scope="initial-productive-core",
        certification_mode="evidence-only",
        generated_at="2026-05-24T13:00:00+00:00",
    )

    assert payload["contract_version"] == "0.3.0"
    assert payload["status"] == "initial-productive-core"
    assert payload["final_decision"] == "not-certified"
    assert payload["open_release_gaps"] == []
    assert "Credential values are not written" in payload["sensitive_data_handling"]
    assert any(result["gate"] == "Repository integrity" for result in payload["gate_results"])
    assert any(result["gate"] == "Executable skill runtime" for result in payload["gate_results"])
    assert any(
        result["gate"] == "Controlled write-capable execution"
        for result in payload["gate_results"]
    )
    assert any(
        result["gate"] == "Scheduled runtime retention cleanup"
        for result in payload["gate_results"]
    )


def test_certify_mode_requires_both_external_run_urls() -> None:
    with pytest.raises(evidence.EvidenceError, match="certify mode requires live_runtime"):
        evidence.validate_certification_inputs(
            repository=REPOSITORY,
            target_environment="prod",
            release_scope="production-runtime",
            certification_mode="certify",
            live_runtime_gates_run_url="",
            ai_gateway_smoke_run_url=AI_GATEWAY_RUN_URL,
        )

    with pytest.raises(evidence.EvidenceError, match="certify mode requires ai_gateway"):
        evidence.validate_certification_inputs(
            repository=REPOSITORY,
            target_environment="prod",
            release_scope="production-runtime",
            certification_mode="certify",
            live_runtime_gates_run_url=LIVE_RUN_URL,
            ai_gateway_smoke_run_url="",
        )


def test_certify_mode_validates_external_run_metadata_against_commit_and_workflow() -> None:
    payload = evidence.build_evidence(
        repository=REPOSITORY,
        commit=COMMIT,
        workflow_run_id="111",
        workflow_run_attempt="1",
        target_environment="prod",
        release_scope="production-runtime",
        certification_mode="certify",
        live_runtime_gates_run_url=LIVE_RUN_URL,
        ai_gateway_smoke_run_url=AI_GATEWAY_RUN_URL,
        live_runtime_gates_metadata=run_metadata(
            run_id=123456789,
            workflow_name="Live Runtime Gates",
            url=LIVE_RUN_URL,
        ),
        ai_gateway_smoke_metadata=run_metadata(
            run_id=987654321,
            workflow_name="CI",
            url=AI_GATEWAY_RUN_URL,
        ),
        live_handler_binding_evidence=live_handler_binding_evidence(),
        generated_at="2026-05-24T13:00:00+00:00",
    )

    assert payload["external_evidence"]["live_runtime_gates"]["validation_status"] == "passed"
    assert payload["external_evidence"]["ai_gateway_smoke"]["validation_status"] == "passed"
    assert payload["external_evidence"]["live_handler_bindings"]["validation_status"] == (
        "passed"
    )
    assert any(
        result["gate"] == "Live handler binding evidence"
        for result in payload["gate_results"]
    )
    assert payload["status"] == "not-production-ready"
    assert payload["final_decision"] == "not-certified"
    assert not any(gap["id"] == "P5.04" for gap in payload["open_release_gaps"])
    assert not any(gap["id"] == "P5.05" for gap in payload["open_release_gaps"])
    assert not any(gap["id"] == "P5.06" for gap in payload["open_release_gaps"])
    assert any(gap["id"] == "P5.07" for gap in payload["open_release_gaps"])


def test_write_release_scope_uses_controlled_write_gate_without_open_p5_05_gap() -> None:
    payload = evidence.build_evidence(
        repository=REPOSITORY,
        commit=COMMIT,
        workflow_run_id="111",
        workflow_run_attempt="1",
        target_environment="dev",
        release_scope="controlled-write-runtime",
        certification_mode="evidence-only",
        generated_at="2026-05-24T13:00:00+00:00",
    )

    assert any(
        result["gate"] == "Controlled write-capable execution"
        for result in payload["gate_results"]
    )
    assert not any(gap["id"] == "P5.05" for gap in payload["open_release_gaps"])


def test_certify_mode_rejects_wrong_external_workflow() -> None:
    with pytest.raises(evidence.EvidenceError, match="expected workflow"):
        evidence.build_evidence(
            repository=REPOSITORY,
            commit=COMMIT,
            workflow_run_id="111",
            workflow_run_attempt="1",
            target_environment="prod",
            release_scope="production-runtime",
            certification_mode="certify",
            live_runtime_gates_run_url=LIVE_RUN_URL,
            ai_gateway_smoke_run_url=AI_GATEWAY_RUN_URL,
            live_runtime_gates_metadata=run_metadata(
                run_id=123456789,
                workflow_name="CI",
                url=LIVE_RUN_URL,
            ),
            ai_gateway_smoke_metadata=run_metadata(
                run_id=987654321,
                workflow_name="CI",
                url=AI_GATEWAY_RUN_URL,
            ),
            live_handler_binding_evidence=live_handler_binding_evidence(),
        )


def test_certify_mode_requires_live_handler_binding_evidence() -> None:
    with pytest.raises(evidence.EvidenceError, match="live handler binding evidence"):
        evidence.build_evidence(
            repository=REPOSITORY,
            commit=COMMIT,
            workflow_run_id="111",
            workflow_run_attempt="1",
            target_environment="prod",
            release_scope="production-runtime",
            certification_mode="certify",
            live_runtime_gates_run_url=LIVE_RUN_URL,
            ai_gateway_smoke_run_url=AI_GATEWAY_RUN_URL,
            live_runtime_gates_metadata=run_metadata(
                run_id=123456789,
                workflow_name="Live Runtime Gates",
                url=LIVE_RUN_URL,
            ),
            ai_gateway_smoke_metadata=run_metadata(
                run_id=987654321,
                workflow_name="CI",
                url=AI_GATEWAY_RUN_URL,
            ),
        )


def test_live_handler_binding_evidence_rejects_mismatched_handler_id() -> None:
    invalid_evidence = live_handler_binding_evidence()
    result = invalid_evidence["results"][0]
    assert isinstance(result, dict)
    handlers = result["skill_handlers"]
    assert isinstance(handlers, list)
    handlers[0]["handler_id"] = "wrong-handler@0.1.0"

    with pytest.raises(evidence.EvidenceError, match="does not match"):
        evidence.validate_live_handler_binding_evidence(invalid_evidence)
