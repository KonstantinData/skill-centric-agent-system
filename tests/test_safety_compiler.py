from __future__ import annotations

import json
from pathlib import Path

from skill_centric_agent_system.runtime import (
    InMemoryRuntimeStore,
    SafetyCompiler,
)
from skill_centric_agent_system.runtime.memory_candidates import MemoryCandidateValidator

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "policies" / "runtime" / "semantic-drift-guard.json"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def staging_to_prod_budget_prior() -> dict[str, object]:
    return {
        "source_context": {
            "environment": "staging",
            "risk_level": "medium",
            "workflow_id": "runtime-preflight-required",
            "principal_role": "repository-maintainer",
            "task_type": "production-preflight",
        },
        "target_context": {
            "environment": "prod",
            "risk_level": "high",
            "workflow_id": "runtime-preflight-required",
            "principal_role": "repository-maintainer",
            "task_type": "production-preflight",
        },
        "authority_delta": ["budget_increase"],
    }


def memory_candidate() -> dict[str, object]:
    return {
        "id": "mc-semantic-drift",
        "run_id": "run-semantic-drift",
        "profile_id": "profile-runtime",
        "source_step_id": "step-validator",
        "target_memory_scope_id": "mod-project-memory",
        "content_uri": "hetzner://runtime/run-semantic-drift/memory/candidate.json",
        "sensitivity": "internal",
        "retention_policy": "project-memory-180d",
        "validator_id": "memory-candidate-contract",
        "policy_id": "mod-no-destructive-commands",
    }


def test_safety_compiler_loads_semantic_drift_guard_policy() -> None:
    compiler = SafetyCompiler.from_policy_file(POLICY_PATH)

    decision = compiler.compile_learned_authority_prior(
        {
            "source_context": {"environment": "dev", "risk_level": "low"},
            "target_context": {"environment": "dev", "risk_level": "low"},
            "authority_delta": [],
        }
    )

    assert decision.decision == "allow_ranking_only"
    assert decision.automatic_promotion_allowed is True
    assert decision.matched_pair_ids == ()


def test_safety_compiler_blocks_matching_contrastive_authority_boundary() -> None:
    compiler = SafetyCompiler.from_policy_file(POLICY_PATH)

    decision = compiler.compile_learned_authority_prior(staging_to_prod_budget_prior())

    assert decision.decision == "needs_human_review"
    assert decision.automatic_promotion_allowed is False
    assert decision.matched_pair_ids == (
        "staging-budget-gap-must-not-generalize-to-prod",
    )
    assert decision.authority_delta == ("budget_increase",)


def test_safety_compiler_rejects_unreviewed_authority_delta_without_pair() -> None:
    compiler = SafetyCompiler.from_policy_file(POLICY_PATH)

    decision = compiler.compile_learned_authority_prior(
        {
            "source_context": {
                "environment": "dev",
                "risk_level": "low",
                "workflow_id": "memory-retrieval-required",
            },
            "target_context": {
                "environment": "staging",
                "risk_level": "medium",
                "workflow_id": "memory-retrieval-required",
            },
            "authority_delta": ["knowledge_scope_expansion"],
        }
    )

    assert decision.decision == "reject"
    assert decision.automatic_promotion_allowed is False
    assert decision.reason == "Learned authority delta has no reviewed policy artifact."


def test_safety_compiler_allows_reviewed_policy_bound_authority_delta() -> None:
    compiler = SafetyCompiler.from_policy_file(POLICY_PATH)

    decision = compiler.compile_learned_authority_prior(
        {
            "source_context": {"environment": "dev", "risk_level": "low"},
            "target_context": {"environment": "staging", "risk_level": "medium"},
            "authority_delta": ["knowledge_scope_expansion"],
        },
        reviewed_policy_artifacts=("policies/runtime/reviewed-scope-change.json",),
    )

    assert decision.decision == "allow_ranking_only"
    assert decision.automatic_promotion_allowed is True
    assert decision.reviewed_policy_artifacts == (
        "policies/runtime/reviewed-scope-change.json",
    )


def test_memory_promotion_rejects_learned_authority_boundary() -> None:
    store = InMemoryRuntimeStore()
    candidate = store.insert_memory_candidate(memory_candidate())
    compiler = SafetyCompiler.from_policy_file(POLICY_PATH)
    validator = MemoryCandidateValidator(
        store=store,
        allowed_memory_scope_ids={"mod-project-memory"},
        allowed_policy_ids={"mod-no-destructive-commands"},
        safety_compiler=compiler,
    )

    result = validator.validate(
        candidate,
        content={
            "summary": "Staging budget issue should become a prod budget prior.",
            "learned_context_authority_prior": staging_to_prod_budget_prior(),
        },
    )

    assert not result.approved
    assert result.policy_status == "rejected"
    assert "semantic drift guard blocked learned authority" in result.policy_reason
    assert "staging-budget-gap-must-not-generalize-to-prod" in result.policy_reason


def test_memory_promotion_allows_ranking_only_prior() -> None:
    store = InMemoryRuntimeStore()
    candidate = store.insert_memory_candidate(memory_candidate())
    compiler = SafetyCompiler.from_policy_file(POLICY_PATH)
    validator = MemoryCandidateValidator(
        store=store,
        allowed_memory_scope_ids={"mod-project-memory"},
        allowed_policy_ids={"mod-no-destructive-commands"},
        safety_compiler=compiler,
    )

    result = validator.validate(
        candidate,
        content={
            "summary": "Research retrieval signal only changes ranking.",
            "learned_context_authority_prior": {
                "source_context": {"environment": "dev", "risk_level": "low"},
                "target_context": {"environment": "dev", "risk_level": "low"},
                "authority_delta": [],
            },
        },
    )

    assert result.approved


def test_safety_compiler_decision_report_is_operator_safe() -> None:
    compiler = SafetyCompiler.from_policy_file(POLICY_PATH)

    report = compiler.compile_decision_report(staging_to_prod_budget_prior())

    assert report["report_kind"] == "semantic_drift_guard_decision"
    assert report["source_context"] == staging_to_prod_budget_prior()["source_context"]
    assert report["target_context"] == staging_to_prod_budget_prior()["target_context"]
    assert report["authority_delta"] == ["budget_increase"]
    assert report["matched_contrastive_pair_ids"] == [
        "staging-budget-gap-must-not-generalize-to-prod"
    ]
    assert report["final_gate"] == "needs_human_review"
    assert report["safe_for_release_evidence"] is True
    assert report["raw_runtime_trace_included"] is False


def test_safety_compiler_coverage_report_lists_pair_coverage_and_gaps() -> None:
    compiler = SafetyCompiler.from_policy_file(POLICY_PATH)

    report = compiler.contrastive_pair_coverage_report()

    assert report["report_kind"] == "semantic_drift_guard_coverage"
    assert "staging-budget-gap-must-not-generalize-to-prod" in report["covered_pair_ids"]
    assert "prod" in report["coverage"]["environments"]
    assert "high" in report["coverage"]["risk_levels"]
    assert "runtime-preflight-required" in report["coverage"]["workflow_ids"]
    assert "budget_increase" in report["coverage"]["authority_delta"]
    assert "validator_removal" in report["coverage_gaps"]["authority_delta"]
    assert report["safe_for_release_evidence"] is True
    assert report["raw_runtime_trace_included"] is False
