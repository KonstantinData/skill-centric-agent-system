from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

CONTRACT_VERSION = "0.1.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.runtime.scan_transition_signals import scanner_coverage_violations  # noqa: E402

DEFAULT_EVIDENCE = REPO_ROOT / "examples" / "evaluations" / "transition-evidence.json"
DEFAULT_SCHEMA = REPO_ROOT / "schemas" / "transition-evidence.schema.json"

TRUE_VALUE = "true"
UNKNOWN_VALUE = "unknown"
COMPLETE_COVERAGE = "complete"
ESCALATION_BLOCKING_UNKNOWN_FIELDS = {
    "repository_bound",
    "explicit_write_intent",
    "protected_path_reference",
    "scan_coverage",
    "raw_artifact_hash_verified",
    "previous_profile_authority_verified",
}
FORBIDDEN_AUDIT_CONTENT = {
    "secret_values",
    "private_keys",
    "bearer_tokens",
    "raw_runtime_traces",
    "raw_tool_outputs",
    "confidential_customer_data",
}
NON_ESCALATING_DECISIONS = {
    "clarification_required",
    "human_review_required",
    "denied",
}


class TransitionEvidenceError(ValueError):
    """Raised when transition evidence is invalid."""


def validate_transition_evidence(
    evidence: Mapping[str, Any],
    *,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    schema = _load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(evidence)

    violations = _evidence_violations(evidence)
    report = {
        "contract_version": CONTRACT_VERSION,
        "status": "passed" if not violations else "failed",
        "summary": {
            "raw_artifact_count": len(evidence["raw_artifacts"]),
            "mentioned_path_count": len(evidence["mentioned_paths"]),
            "unknown_field_count": len(evidence["decision"]["unknown_fields"]),
            "escalates_authority": evidence["capability_delta"]["escalates_authority"],
            "decision": evidence["decision"]["status"],
        },
        "violations": violations,
    }
    if violations:
        raise TransitionEvidenceError(
            "transition evidence failed validation: " + "; ".join(violations)
        )
    return report


def assert_evidence_current(
    *,
    evidence_path: Path = DEFAULT_EVIDENCE,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    return validate_transition_evidence(_load_json(evidence_path), schema_path=schema_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate SCAS transition evidence artifacts.",
    )
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = assert_evidence_current(
            evidence_path=args.evidence,
            schema_path=args.schema,
        )
    except (OSError, json.JSONDecodeError, TransitionEvidenceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1 if args.check else 2

    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True), end="\n")
    return 0


def _evidence_violations(evidence: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    artifacts = _artifact_index(evidence)

    violations.extend(_artifact_hash_violations(artifacts.values()))
    violations.extend(_span_violations(evidence, artifacts))
    violations.extend(_critical_field_violations(evidence))
    violations.extend(_capability_delta_violations(evidence))
    violations.extend(scanner_coverage_violations(evidence))
    violations.extend(_audit_violations(evidence))

    return violations


def _artifact_index(evidence: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(artifact["artifact_id"]): artifact
        for artifact in evidence["raw_artifacts"]
    }


def _artifact_hash_violations(
    artifacts: Iterable[Mapping[str, Any]],
) -> list[str]:
    violations: list[str] = []
    for artifact in artifacts:
        artifact_id = str(artifact["artifact_id"])
        actual_hash = _sha256(str(artifact["text"]))
        if artifact["artifact_hash"] != actual_hash:
            violations.append(f"{artifact_id} artifact_hash does not match text")
    return violations


def _span_violations(
    evidence: Mapping[str, Any],
    artifacts: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    violations: list[str] = []
    for field_name, span in _iter_evidence_spans(evidence):
        artifact_id = str(span["artifact_id"])
        artifact = artifacts.get(artifact_id)
        if artifact is None:
            violations.append(f"{field_name} references unknown artifact {artifact_id}")
            continue
        if span["artifact_hash"] != artifact["artifact_hash"]:
            violations.append(f"{field_name} artifact_hash does not match {artifact_id}")
        offset_start = int(span["offset_start"])
        offset_end = int(span["offset_end"])
        raw_text = str(artifact["text"])
        if offset_start >= offset_end:
            violations.append(f"{field_name} offset_start must be before offset_end")
            continue
        if offset_end > len(raw_text):
            violations.append(f"{field_name} offset_end exceeds artifact length")
            continue
        if raw_text[offset_start:offset_end] != span["span"]:
            violations.append(f"{field_name} span does not match artifact offsets")
    return violations


def _iter_evidence_spans(
    evidence: Mapping[str, Any],
) -> Iterable[tuple[str, Mapping[str, Any]]]:
    for field_name, field in evidence["critical_fields"].items():
        if not isinstance(field, Mapping):
            continue
        for index, span in enumerate(field.get("evidence", [])):
            yield f"critical_fields.{field_name}.evidence[{index}]", span

    for index, path in enumerate(evidence["mentioned_paths"]):
        yield f"mentioned_paths[{index}].evidence", path["evidence"]


def _critical_field_violations(evidence: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    critical_fields = evidence["critical_fields"]
    for field_name, field in critical_fields.items():
        value = str(field["value"])
        if value == TRUE_VALUE and not field["evidence"]:
            violations.append(f"{field_name}=true requires at least one evidence span")

    if (
        critical_fields["scan_coverage"]["value"] != COMPLETE_COVERAGE
        and evidence["capability_delta"]["escalates_authority"]
    ):
        violations.append("scan_coverage must be complete for capability escalation")

    for artifact in evidence["raw_artifacts"]:
        if (
            artifact["scan_coverage"] != COMPLETE_COVERAGE
            and evidence["capability_delta"]["escalates_authority"]
        ):
            violations.append(
                f"{artifact['artifact_id']} scan_coverage must be complete "
                "for capability escalation"
            )

    return violations


def _capability_delta_violations(evidence: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    delta = evidence["capability_delta"]
    decision = evidence["decision"]
    critical_fields = evidence["critical_fields"]
    escalates_authority = bool(delta["escalates_authority"])

    if escalates_authority and not delta["requires_recomposition"]:
        violations.append("capability escalation requires recomposition")

    unknown_fields = {
        field_name
        for field_name, field in critical_fields.items()
        if str(field["value"]) == UNKNOWN_VALUE
    }
    decision_unknowns = set(str(field) for field in decision["unknown_fields"])
    if unknown_fields != decision_unknowns:
        violations.append("decision unknown_fields must match critical unknown fields")

    if (
        escalates_authority
        and unknown_fields & ESCALATION_BLOCKING_UNKNOWN_FIELDS
        and decision["status"] not in NON_ESCALATING_DECISIONS
    ):
        violations.append("unknown escalation-critical fields must block escalation")

    if escalates_authority and decision["status"] == "allowed":
        violations.append("capability escalation cannot be directly allowed")

    if (
        "repo-write" in delta["to_capability_classes"]
        and decision["status"] not in NON_ESCALATING_DECISIONS
    ):
        if critical_fields["explicit_write_intent"]["value"] != TRUE_VALUE:
            violations.append("repo-write transition requires explicit_write_intent=true")
        if critical_fields["repository_bound"]["value"] != TRUE_VALUE:
            violations.append("repo-write transition requires repository_bound=true")

    return violations


def _audit_violations(evidence: Mapping[str, Any]) -> list[str]:
    forbidden_content = set(evidence["audit"]["forbidden_content"])
    missing_forbidden = FORBIDDEN_AUDIT_CONTENT - forbidden_content
    if not missing_forbidden:
        return []
    return [
        "audit forbidden_content missing: "
        + ", ".join(sorted(missing_forbidden))
    ]


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise TransitionEvidenceError(f"{_repo_path(path)} must contain a JSON object")
    return parsed


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
