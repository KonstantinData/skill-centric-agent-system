"""Validate detect-secrets and Gitleaks reports for CI secret gates."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

IGNORED_PATH_PATTERNS = (
    re.compile(r"(^|/)\.git/"),
    re.compile(r"(^|/)\.mypy_cache/"),
    re.compile(r"(^|/)\.pytest_cache/"),
    re.compile(r"(^|/)\.ruff_cache/"),
    re.compile(r"(^|/)node_modules/"),
    re.compile(r"(^|/)[^/]+\.egg-info/"),
    re.compile(r"(^|/)\.venv/"),
    re.compile(r"(^|/)venv/"),
    re.compile(r"(^|/)security-evidence/"),
    re.compile(r"(^|/)production-readiness-evidence\.json$"),
    re.compile(r"(^|/)\.scas-runtime/"),
)

ALLOWED_FINDING_TYPES_BY_PATH = {
    ".github/workflows/ci.yml": {"Private Key", "Secret Keyword"},
    ".github/workflows/live-runtime-gates.yml": {"Private Key"},
    "examples/infrastructure/environment-manifest.json": {"Secret Keyword"},
}


def normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        return normalized[2:]
    return normalized


def is_ignored_path(path: str) -> bool:
    normalized = normalize_path(path)
    return any(pattern.search(normalized) for pattern in IGNORED_PATH_PATTERNS)


def is_allowed_finding(path: str, finding_type: str) -> bool:
    normalized = normalize_path(path)
    return finding_type in ALLOWED_FINDING_TYPES_BY_PATH.get(normalized, set())


def load_json(path: Path) -> Any:
    if not path.exists():
        raise SystemExit(f"Secret scan report missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def detect_secrets_findings(report: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    results = report.get("results", {})
    if not isinstance(results, dict):
        raise SystemExit("detect-secrets report has invalid results shape.")
    for path, entries in results.items():
        if is_ignored_path(str(path)):
            continue
        for entry in entries:
            finding_type = str(entry.get("type", ""))
            if not is_allowed_finding(str(path), finding_type):
                findings.append(str(path))
                break
    return findings


def gitleaks_findings(report: Any) -> list[str]:
    if isinstance(report, dict):
        entries = report.get("findings", report.get("results", []))
    else:
        entries = report
    if not isinstance(entries, list):
        raise SystemExit("Gitleaks report must be a list or object with findings/results.")
    findings: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("File") or entry.get("file") or entry.get("Path") or "")
        finding_type = str(entry.get("RuleID") or entry.get("type") or "")
        if path and not is_ignored_path(path) and not is_allowed_finding(path, finding_type):
            findings.append(path)
    return findings


def validate_detect_secrets(path: Path) -> None:
    findings = detect_secrets_findings(load_json(path))
    if findings:
        raise SystemExit("detect-secrets found potential secrets:\n- " + "\n- ".join(findings))


def validate_gitleaks(path: Path) -> None:
    findings = gitleaks_findings(load_json(path))
    if findings:
        raise SystemExit("Gitleaks found potential secrets:\n- " + "\n- ".join(findings))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scanner", choices=("detect-secrets", "gitleaks"))
    parser.add_argument("report", type=Path)
    args = parser.parse_args()

    if args.scanner == "detect-secrets":
        validate_detect_secrets(args.report)
    else:
        validate_gitleaks(args.report)
    print(f"{args.scanner} report passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
