from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKIPPED_PARTS = {
    ".git",
    ".env",
    ".pytest_cache",
    ".ruff_cache",
    ".wrangler",
    "__pycache__",
    ".venv",
    "coverage",
    "dist",
    "node_modules",
    "skill_centric_agent_system.egg-info",
    "venv",
}
FORBIDDEN_BRAND = "liqui" + "sto"


def iter_repository_text_files() -> list[Path]:
    paths: list[Path] = []
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    for relative_path in result.stdout.splitlines():
        path = REPO_ROOT / relative_path
        if not path.is_file():
            continue
        if SKIPPED_PARTS.intersection(path.relative_to(REPO_ROOT).parts):
            continue
        paths.append(path)
    return paths


def test_repository_content_uses_neutral_naming() -> None:
    offenders: list[str] = []

    for path in iter_repository_text_files():
        content = path.read_text(encoding="utf-8", errors="ignore")
        if FORBIDDEN_BRAND in content.lower():
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert not offenders
