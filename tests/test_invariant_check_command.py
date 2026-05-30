from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMAND_PATH = REPO_ROOT / "scripts" / "runtime" / "invariant_check.py"
CASES_PATH = REPO_ROOT / "examples" / "evaluations" / "formal-safety-invariant-replay-cases.json"
PROFILES_DIR = REPO_ROOT / "examples" / "profiles"


def run_command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(COMMAND_PATH), *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_invariant_check_command_passes_for_committed_corpus() -> None:
    result = run_command("--print-json")
    assert result.returncode == 0, result.stderr

    payload = json.loads(result.stdout)
    assert payload["status"] == "passed"
    assert payload["mismatch_count"] == 0
    assert payload["total_cases"] >= 15


def test_invariant_check_command_fails_on_mismatched_expected_outcome(tmp_path: Path) -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases[0]["expected_violation"] = not bool(cases[0]["expected_violation"])
    bad_cases_path = tmp_path / "bad-cases.json"
    bad_cases_path.write_text(json.dumps(cases, indent=2), encoding="utf-8")

    result = run_command("--cases", str(bad_cases_path), "--profiles-dir", str(PROFILES_DIR))
    assert result.returncode == 1
    assert "mismatches" in result.stdout
