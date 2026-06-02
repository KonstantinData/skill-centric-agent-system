from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

DECISION_VERSION = "0.1.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DECISION = (
    REPO_ROOT / "policies" / "runtime" / "structured-evidence-extraction-decision.json"
)
DEFAULT_SCHEMA = REPO_ROOT / "schemas" / "structured-evidence-extraction-decision.schema.json"


class StructuredEvidenceDecisionError(ValueError):
    """Raised when the Structured Outputs evaluation decision is invalid."""


def validate_structured_evidence_decision(
    decision: dict[str, Any],
    *,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    schema = _load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(decision)

    violations = _decision_violations(decision)
    report = {
        "decision_version": DECISION_VERSION,
        "status": "passed" if not violations else "failed",
        "summary": {
            "recommendation": decision["recommendation"],
            "source_count": len(decision["official_sources"]),
            "guardrail_count": len(decision["required_guardrails"]),
        },
        "violations": violations,
    }
    if violations:
        raise StructuredEvidenceDecisionError(
            "structured evidence extraction decision failed validation: "
            + "; ".join(violations)
        )
    return report


def assert_decision_current(
    *,
    decision_path: Path = DEFAULT_DECISION,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    return validate_structured_evidence_decision(
        _load_json(decision_path),
        schema_path=schema_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate SCAS Structured Outputs extraction decision.",
    )
    parser.add_argument("--decision", type=Path, default=DEFAULT_DECISION)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = assert_decision_current(
            decision_path=args.decision,
            schema_path=args.schema,
        )
    except (OSError, json.JSONDecodeError, StructuredEvidenceDecisionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1 if args.check else 2

    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True), end="\n")
    return 0


def _decision_violations(decision: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if decision["recommendation"] == "adopt_with_guardrails":
        violations.append("runtime adoption is not allowed before provider subset schema exists")
    guardrails = set(decision["required_guardrails"])
    required = {
        "deterministic_scanners_authoritative",
        "local_schema_validation_authoritative",
        "hash_and_offset_verification",
        "scanner_coverage_required",
        "fail_closed_on_provider_errors",
        "no_provider_output_can_grant_authority",
    }
    missing = required - guardrails
    if missing:
        violations.append("missing required guardrails: " + ", ".join(sorted(missing)))
    if not decision["local_schema_assessment"]["provider_subset_schema_required"]:
        violations.append("provider subset schema must be required")
    if not decision["local_schema_assessment"]["authoritative_local_validation_required"]:
        violations.append("local validation must remain authoritative")
    return violations


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise StructuredEvidenceDecisionError(f"{path} must contain a JSON object")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
