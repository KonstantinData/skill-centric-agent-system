from __future__ import annotations

import json
from pathlib import Path

from skill_centric_agent_system.composition.task_analyzer import TaskAnalyzer

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_READINESS_PATH = REPO_ROOT / "docs" / "policies" / "production-readiness.md"
README_PATH = REPO_ROOT / "README.md"
FIRST_PRODUCTIVE_OPERATION_PATH = (
    REPO_ROOT / "docs" / "runbooks" / "first-productive-agent-operation.md"
)
FIRST_PRODUCTIVE_TASK_PATH = (
    REPO_ROOT / "operations" / "staging-tasks" / "first-productive-scas-operations-review.json"
)


def test_production_readiness_gate_exists() -> None:
    assert PRODUCTION_READINESS_PATH.exists()


def test_production_readiness_gate_defines_required_release_evidence() -> None:
    gate = PRODUCTION_READINESS_PATH.read_text(encoding="utf-8")

    required_sections = (
        "Purpose",
        "Status Vocabulary",
        "Release Gate",
        "Evidence Rules",
        "Certification Output",
        "Evidence Workflow",
    )
    for section in required_sections:
        assert f"## {section}" in gate

    assert "docs/roadmap/production-readiness-backlog.md" in gate

    required_gates = (
        "Repository integrity",
        "Repository security and supply chain",
        "Data governance and quality",
        "Environment separation",
        "Control Plane readiness",
        "Runtime Plane readiness",
        "Live runtime gates",
        "Live handler binding evidence",
        "Recertification cadence and release policy",
        "Executable skill runtime",
        "Skill handler version policy",
        "Operational telemetry",
        "Security closure",
        "Release decision",
    )
    for required_gate in required_gates:
        assert required_gate in gate


def test_production_readiness_gate_defines_consumed_evidence_mode() -> None:
    gate = PRODUCTION_READINESS_PATH.read_text(encoding="utf-8")

    assert "evidence_source_mode = consume-existing" in gate
    assert "evidence_source_mode = recheck" in gate
    assert "CI" in gate
    assert "Security Governance" in gate
    assert "SHA-256" in gate
    assert "checksums" in gate
    assert "no more than 14 days" in gate


def test_readme_links_production_readiness_gate() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "docs/policies/production-readiness.md" in readme
    assert "not-production-ready" in readme
    assert "docs/runbooks/first-productive-agent-operation.md" in readme


def test_first_productive_operation_runbook_defines_staging_boundary() -> None:
    runbook = FIRST_PRODUCTIVE_OPERATION_PATH.read_text(encoding="utf-8")

    assert "staging" in runbook
    assert "This baseline certifies staging only. It does not certify `prod`." in runbook
    assert "SCAS_CONTROL_API_TOKEN" not in runbook
    assert "SCAS_RUNTIME_DATABASE_URL" not in runbook
    assert "production customer data" in runbook
    assert "workflow_dispatch" in runbook
    assert "live-runtime-handler-binding-evidence" in runbook


def test_first_productive_operation_runbook_defers_dedicated_workflow() -> None:
    runbook = FIRST_PRODUCTIVE_OPERATION_PATH.read_text(encoding="utf-8")

    assert "No dedicated productive-operation workflow is required" in runbook
    assert "live_task_suite=single" in runbook
    assert "committed non-secret task file" in runbook
    assert "Create a dedicated manual productive-operation workflow only after" in runbook
    assert "staging operation through the existing path" in runbook
    assert "proves a concrete operator" in runbook
    assert "evidence, or safety gap" in runbook
    assert "The next implementation slice should add" not in runbook


def test_first_productive_operation_uses_real_staging_task_file() -> None:
    runbook = FIRST_PRODUCTIVE_OPERATION_PATH.read_text(encoding="utf-8")

    assert str(FIRST_PRODUCTIVE_TASK_PATH.relative_to(REPO_ROOT)).replace("\\", "/") in runbook
    assert "examples/tasks/<approved-task>.json" not in runbook
    assert FIRST_PRODUCTIVE_TASK_PATH.is_file()

    task = json.loads(FIRST_PRODUCTIVE_TASK_PATH.read_text(encoding="utf-8"))
    assert task["constraints"]["write_access"] is False
    assert task["constraints"]["destructive_actions"] is False
    assert task["constraints"]["target_environment"] == "staging"
    assert task["constraints"]["production_data"] is False
    assert task["constraints"]["secret_access"] is False

    analysis = TaskAnalyzer().analyze(task)
    assert analysis.task_type == "research"
    assert analysis.risk_level == "low"
    assert analysis.requires_human_review is False

