from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skill_centric_agent_system.runtime import SafetyCompiler

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "policies" / "runtime" / "semantic-drift-guard.json"
RED_TEAM_CASES_PATH = (
    REPO_ROOT / "examples" / "evaluations" / "semantic-drift-red-team-cases.json"
)
BLOCKING_GATES = {"freeze_prior", "needs_human_review", "needs_more_evidence", "reject"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_semantic_drift_red_team_cases_block_learned_authority_bypass() -> None:
    fixture = load_json(RED_TEAM_CASES_PATH)
    compiler = SafetyCompiler.from_policy_file(POLICY_PATH)
    seen_attack_vectors = set[str]()

    for case in fixture["cases"]:
        report = compiler.compile_decision_report(case["prior"])
        seen_attack_vectors.add(str(case["attack_vector"]))

        assert report["final_gate"] == case["expected_gate"], case["case_id"]
        assert report["final_gate"] in BLOCKING_GATES, case["case_id"]
        assert report["automatic_promotion_allowed"] is False, case["case_id"]
        assert (
            report["matched_contrastive_pair_ids"] == case["expected_matched_pair_ids"]
        ), case["case_id"]
        assert report["safe_for_release_evidence"] is True
        assert report["raw_runtime_trace_included"] is False

    assert {
        "staging-to-prod generalization",
        "low-risk-to-high-risk drift",
        "memory scope expansion",
        "validator removal",
        "policy exception",
        "failure mode relaxation",
    } <= seen_attack_vectors


def test_semantic_drift_red_team_fixture_is_wired_into_policy_docs() -> None:
    policy_doc = (REPO_ROOT / "docs" / "policies" / "semantic-drift-guard.md").read_text(
        encoding="utf-8"
    )

    assert "semantic-drift-red-team-cases.json" in policy_doc
