from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_READINESS_PATH = REPO_ROOT / "docs" / "policies" / "production-readiness.md"
README_PATH = REPO_ROOT / "README.md"


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
        "Executable skill runtime",
        "Skill handler version policy",
        "Operational telemetry",
        "Security closure",
        "Release decision",
    )
    for required_gate in required_gates:
        assert required_gate in gate


def test_readme_links_production_readiness_gate() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "docs/policies/production-readiness.md" in readme
    assert "not-production-ready" in readme

