from __future__ import annotations

from pathlib import Path

from skill_centric_agent_system.runtime.invariant_replay import (
    load_replay_cases,
    run_replay_cases,
    validate_replay_corpus_shape,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_CASES_PATH = (
    REPO_ROOT / "examples" / "evaluations" / "formal-safety-invariant-replay-cases.json"
)
PROFILE_FIXTURES_DIR = REPO_ROOT / "examples" / "profiles"


def test_replay_fixture_corpus_shape_is_complete() -> None:
    cases = load_replay_cases(REPLAY_CASES_PATH)
    failures = validate_replay_corpus_shape(cases)
    assert failures == []


def test_replay_fixture_corpus_matches_expected_violation_outcomes() -> None:
    cases = load_replay_cases(REPLAY_CASES_PATH)
    results = run_replay_cases(cases=cases, profiles_dir=PROFILE_FIXTURES_DIR)
    mismatches = [result for result in results if not result.passed]

    assert mismatches == []
