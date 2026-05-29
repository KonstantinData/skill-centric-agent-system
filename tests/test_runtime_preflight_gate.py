from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_PATH = REPO_ROOT / "docs" / "runbooks" / "runtime-preflight.md"
ROADMAP_PATH = REPO_ROOT / "docs" / "reference" / "repository-roadmap.md"
ARCHITECTURE_PATH = REPO_ROOT / "docs" / "reference" / "architecture.md"
INFRASTRUCTURE_PATH = REPO_ROOT / "docs" / "policies" / "infrastructure-boundary.md"
OPERATIONS_RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "operations-runbook.md"


PHASE_0_ITEMS = [
    "P0.01 Runtime Preflight Gate: Synchronize Backlog and Roadmap",
    "P0.02 Runtime Preflight Gate: Finalize Terms and Naming",
    "P0.03 Runtime Preflight Gate: Define Productive Runtime Phase",
    "P0.04 Runtime Preflight Gate: Verify Dev Infrastructure Status",
    "P0.05 Runtime Preflight Gate: Define Runtime Entry Criteria",
    "P0.06 Runtime Preflight Gate: Define Generic Validation Scenarios",
    "P0.07 Runtime Preflight Gate: Define Risk Boundaries",
    "P0.08 Runtime Preflight Gate: "
    "Seed Project Memory Scope and Fail Closed on Unknown Memory Scope",
]

PHASE_1_ITEMS = [
    "P1.01 Finalize Generic Runtime Contract",
    "P1.02 Define Runtime API/CLI Contract",
    "P1.03 Wire Real Hetzner Runtime Storage",
    "P1.04 Complete Profile Enforcement",
    "P1.05 Harden Tool Gateway for Productive Runtime Use",
    "P1.06 Bind Context Manager to Control API Retrieval",
    "P1.07 Make Validator Framework Generic",
    "P1.08 Implement Controlled Recomposition Path",
    "P1.09 Build Live Dev E2E Gate",
    "P1.10 Establish Operations Baseline",
]


def test_runtime_preflight_document_defines_phase_order() -> None:
    preflight = PREFLIGHT_PATH.read_text(encoding="utf-8")
    for item in [*PHASE_0_ITEMS, *PHASE_1_ITEMS]:
        assert item in preflight

    phase_0_positions = [preflight.index(item) for item in PHASE_0_ITEMS]
    phase_1_positions = [preflight.index(item) for item in PHASE_1_ITEMS]
    assert phase_0_positions == sorted(phase_0_positions)
    assert phase_1_positions == sorted(phase_1_positions)
    assert max(phase_0_positions) < min(phase_1_positions)


def test_roadmap_architecture_and_infrastructure_reference_preflight_gate() -> None:
    assert "Runtime Preflight Gate" in ROADMAP_PATH.read_text(encoding="utf-8")
    assert "docs/runbooks/runtime-preflight.md" in ARCHITECTURE_PATH.read_text(encoding="utf-8")
    assert "docs/runbooks/runtime-preflight.md" in INFRASTRUCTURE_PATH.read_text(encoding="utf-8")


def test_task_type_values_use_kebab_case_in_json_contract_examples() -> None:
    json_paths = [
        *sorted((REPO_ROOT / "examples").rglob("*.json")),
        *sorted((REPO_ROOT / "schemas").rglob("*.json")),
    ]
    for path in json_paths:
        parsed = json.loads(path.read_text(encoding="utf-8"))
        serialized = json.dumps(parsed, sort_keys=True)
        assert "code_review" not in serialized, path
        assert "git_diff_analysis" not in serialized, path
        assert "filesystem_read" not in serialized, path


def test_runtime_gate_docs_use_the_english_backlog_titles() -> None:
    combined_docs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            PREFLIGHT_PATH,
            ROADMAP_PATH,
            ARCHITECTURE_PATH,
            INFRASTRUCTURE_PATH,
            REPO_ROOT / "README.md",
        ]
    )
    assert "P0.01 Runtime Preflight Gate: Synchronize Backlog and Roadmap" in combined_docs
    assert "P1.10 Establish Operations Baseline" in combined_docs


def test_live_preflight_docs_define_auth_and_secret_checks() -> None:
    preflight = PREFLIGHT_PATH.read_text(encoding="utf-8")
    runbook = OPERATIONS_RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "Any non-health route without a bearer token returns `401`." in preflight
    assert "wrangler secret list --config workers/control-api/wrangler.toml" in runbook
    assert "CONTROL_API_TOKEN" in runbook
    assert "SCAS_RUNTIME_DATABASE_URL" in runbook

