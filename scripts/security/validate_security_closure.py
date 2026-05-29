"""Validate production security closure evidence."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_POLICY_PATH = Path("policies/security/production-security-closure.json")
REQUIRED_TOKEN_REVIEWS = {
    "AI_GATEWAY_AUTH_TOKEN",
    "CLOUDFLARE_API_TOKEN",
    "CONTROL_API_TOKEN",
    "HETZNER_SSH_KEY",
    "OPENAI_API_KEY",
}
REQUIRED_GATE_IDS = {
    "data-boundary-governance",
    "dependency-and-supply-chain",
    "release-evidence-minimization",
    "review-governance",
    "secret-scanning",
    "tracked-dotenv-guard",
    "workflow-hardening",
}
THREAT_MODEL_DOCUMENT = "docs/policies/threat-model.md"
SECRET_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def validate_security_closure(
    root: Path | None = None,
    policy_path: Path | None = None,
) -> list[str]:
    repo_root = root or Path.cwd()
    policy_file = policy_path or repo_root / DEFAULT_POLICY_PATH
    data = load_json(policy_file)

    failures: list[str] = []
    if data.get("closure_id") != "p5-08-security-hardening-threat-model-closure":
        failures.append("security closure id must be p5-08-security-hardening-threat-model-closure")
    if data.get("status") != "closed":
        failures.append("security closure status must be closed")
    if not data.get("owner"):
        failures.append("security closure owner is required")

    threat_model = _object(data.get("threat_model"), "threat_model", failures)
    threat_model_path = repo_root / str(threat_model.get("document", ""))
    if threat_model.get("status") != "current":
        failures.append("threat model status must be current")
    if threat_model.get("document") != THREAT_MODEL_DOCUMENT:
        failures.append(f"threat model document must be {THREAT_MODEL_DOCUMENT}")
    if not threat_model_path.exists():
        failures.append("threat model document is missing")
    elif "## Threat Model Closure" not in threat_model_path.read_text(encoding="utf-8"):
        failures.append("threat model document must include Threat Model Closure section")
    if not _valid_date(str(threat_model.get("reviewed_at", ""))):
        failures.append("threat model reviewed_at must be an ISO date")
    if not threat_model.get("next_review_trigger"):
        failures.append("threat model next_review_trigger is required")
    if not threat_model.get("covered_boundaries"):
        failures.append("threat model must list covered boundaries")

    _validate_required_gates(data.get("required_gates"), failures)
    _validate_token_reviews(data.get("token_scope_reviews"), failures)
    _validate_finding_closure(data.get("finding_closure"), failures)
    _validate_data_plane_boundaries(data.get("data_plane_boundaries"), failures)
    _validate_waiver_policy(data.get("waiver_policy"), failures)
    _validate_no_secret_values(data, failures)
    return failures


def _validate_required_gates(value: object, failures: list[str]) -> None:
    gates = _list(value, "required_gates", failures)
    seen = set()
    for gate in gates:
        if not isinstance(gate, dict):
            failures.append("required gate must be an object")
            continue
        seen.add(str(gate.get("id", "")))
        if gate.get("status") not in {"closed", "accepted"}:
            failures.append("required gate must be closed or accepted")
        if not gate.get("evidence"):
            failures.append("required gate must include evidence")
    missing = sorted(REQUIRED_GATE_IDS - seen)
    if missing:
        failures.append(f"missing required security gates: {', '.join(missing)}")


def _validate_token_reviews(value: object, failures: list[str]) -> None:
    reviews = _list(value, "token_scope_reviews", failures)
    seen = set()
    for review in reviews:
        if not isinstance(review, dict):
            failures.append("token review must be an object")
            continue
        name = str(review.get("secret_name", ""))
        seen.add(name)
        if review.get("status") != "reviewed":
            failures.append("token review must be reviewed")
        for field in ("environment_scope", "minimum_scope", "runtime_exposure", "rotation"):
            if not review.get(field):
                failures.append(f"token review missing {field}")
    missing = sorted(REQUIRED_TOKEN_REVIEWS - seen)
    if missing:
        failures.append(f"missing token scope reviews: {', '.join(missing)}")


def _validate_finding_closure(value: object, failures: list[str]) -> None:
    closure = _object(value, "finding_closure", failures)
    if closure.get("security_scan_status") != "no-open-critical-or-high-findings":
        failures.append("security scan status must close critical and high findings")
    if closure.get("remediation_required"):
        failures.append("security closure cannot have remediation_required entries")
    for finding in _list(closure.get("accepted_findings", []), "accepted_findings", failures):
        if not isinstance(finding, dict):
            failures.append("accepted finding must be an object")
            continue
        for field in ("id", "risk", "owner", "expires", "compensating_control"):
            if not finding.get(field):
                failures.append(f"accepted finding missing {field}")
        expires_value = str(finding.get("expires", ""))
        if expires_value and not _valid_date(expires_value):
            failures.append("accepted finding has invalid expires date")
        elif expires_value and date.fromisoformat(expires_value) < date.today():
            failures.append("accepted finding is expired")


def _validate_data_plane_boundaries(value: object, failures: list[str]) -> None:
    boundaries = _list(value, "data_plane_boundaries", failures)
    for boundary in boundaries:
        if not isinstance(boundary, dict):
            failures.append("data plane boundary must be an object")
            continue
        if boundary.get("status") not in {"documented", "tested"}:
            failures.append("boundary must be documented or tested")
        if not boundary.get("evidence"):
            failures.append("boundary must include evidence")


def _validate_waiver_policy(value: object, failures: list[str]) -> None:
    policy = _object(value, "waiver_policy", failures)
    for field in (
        "allows_committed_secrets",
        "allows_unaudited_production_claims",
        "allows_unbounded_data_movement",
    ):
        if policy.get(field) is not False:
            failures.append(f"waiver_policy.{field} must be false")


def _validate_no_secret_values(value: object, failures: list[str], path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _validate_no_secret_values(child, failures, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_no_secret_values(child, failures, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                failures.append("secret-like value is not allowed in security closure policy")


def _object(value: object, name: str, failures: list[str]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    failures.append(f"{name} must be an object")
    return {}


def _list(value: object, name: str, failures: list[str]) -> list[object]:
    if isinstance(value, list):
        return value
    failures.append(f"{name} must be an array")
    return []


def _valid_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--policy", type=Path)
    args = parser.parse_args()

    failures = validate_security_closure(args.root, args.policy)
    if failures:
        print("Security closure validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Security closure validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

