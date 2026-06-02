"""Validate effective CODEOWNERS coverage for high-impact repository paths."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REQUIRED_OWNER = "@KonstantinData"
DEFAULT_CODEOWNERS = Path(".github/CODEOWNERS")
CONTRACT_VERSION = "0.1.0"
HIGH_IMPACT_PATHS = (
    ".github/workflows/ci.yml",
    ".github/workflows/security-governance.yml",
    ".github/rulesets/main-protection.json",
    ".github/CODEOWNERS",
    "policies/runtime/production-recertification-policy.json",
    "policies/security/production-security-closure.json",
    "schemas/production-recertification-policy.schema.json",
    "schemas/runtime-profile.schema.json",
    "workers/control-api/src/index.ts",
    "src/skill_centric_agent_system/runtime/skill_handlers.py",
    "src/skill_centric_agent_system/composition/profile_composer.py",
    "docs/policies/production-readiness.md",
    "docs/policies/production-recertification-policy.md",
    "docs/policies/review-gates.md",
    "docs/policies/data-governance.md",
    "docs/adr/0006-formal-safety-guarantees-profile-sealing.md",
    "AGENTS.md",
    "SECURITY.md",
)


@dataclass(frozen=True)
class CodeownersRule:
    pattern: str
    owners: tuple[str, ...]
    line_number: int


def parse_codeowners(path: Path = DEFAULT_CODEOWNERS) -> tuple[CodeownersRule, ...]:
    rules: list[CodeownersRule] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        pattern, owners = parts[0], tuple(parts[1:])
        rules.append(CodeownersRule(pattern=pattern, owners=owners, line_number=line_number))
    return tuple(rules)


def effective_rule_for_path(
    repo_path: str,
    rules: tuple[CodeownersRule, ...],
) -> CodeownersRule | None:
    normalized_path = repo_path.replace("\\", "/").lstrip("/")
    matched: CodeownersRule | None = None
    for rule in rules:
        if _pattern_matches(rule.pattern, normalized_path):
            matched = rule
    return matched


def validate_effective_coverage(
    *,
    codeowners_path: Path = DEFAULT_CODEOWNERS,
    required_paths: tuple[str, ...] = HIGH_IMPACT_PATHS,
    required_owner: str = REQUIRED_OWNER,
) -> list[str]:
    rules = parse_codeowners(codeowners_path)
    failures: list[str] = []
    for path in required_paths:
        effective_rule = effective_rule_for_path(path, rules)
        if effective_rule is None:
            failures.append(f"{path}: no effective CODEOWNERS rule")
            continue
        if required_owner not in effective_rule.owners:
            failures.append(
                f"{path}: effective owners {list(effective_rule.owners)!r} from "
                f"line {effective_rule.line_number} do not include {required_owner}"
            )
    return failures


def build_evidence(
    *,
    codeowners_path: Path = DEFAULT_CODEOWNERS,
    required_paths: tuple[str, ...] = HIGH_IMPACT_PATHS,
    required_owner: str = REQUIRED_OWNER,
) -> dict[str, object]:
    rules = parse_codeowners(codeowners_path)
    path_results = []
    failures = validate_effective_coverage(
        codeowners_path=codeowners_path,
        required_paths=required_paths,
        required_owner=required_owner,
    )
    for path in required_paths:
        effective_rule = effective_rule_for_path(path, rules)
        path_results.append(
            {
                "path": path,
                "required_owner": required_owner,
                "effective_pattern": effective_rule.pattern if effective_rule else None,
                "effective_line": effective_rule.line_number if effective_rule else None,
                "effective_owners": list(effective_rule.owners) if effective_rule else [],
                "status": (
                    "passed"
                    if effective_rule is not None and required_owner in effective_rule.owners
                    else "failed"
                ),
            }
        )

    return {
        "contract_version": CONTRACT_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not failures else "failed",
        "summary": {
            "checked_path_count": len(required_paths),
            "failed_path_count": len(failures),
        },
        "path_results": path_results,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codeowners", type=Path, default=DEFAULT_CODEOWNERS)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()

    evidence = build_evidence(codeowners_path=args.codeowners)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(evidence, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    if evidence["status"] != "passed":
        print("CODEOWNERS effective ownership validation failed:")
        for failure in evidence["failures"]:
            print(f"- {failure}")
        return 1
    print("CODEOWNERS effective ownership validation passed.")
    return 0


def _pattern_matches(pattern: str, repo_path: str) -> bool:
    normalized_pattern = pattern.replace("\\", "/").lstrip("/")
    if not normalized_pattern:
        return False
    if normalized_pattern.endswith("/"):
        return repo_path.startswith(normalized_pattern)
    if any(token in normalized_pattern for token in ("*", "?", "[")):
        return fnmatch.fnmatch(repo_path, normalized_pattern)
    return repo_path == normalized_pattern or repo_path.startswith(normalized_pattern + "/")


if __name__ == "__main__":
    sys.exit(main())
