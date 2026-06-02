from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

CONTRACT_VERSION = "0.1.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = REPO_ROOT / "policies" / "runtime" / "hooks-usage-model.json"
DEFAULT_SCHEMA = REPO_ROOT / "schemas" / "hooks-usage-model.schema.json"

REQUIRED_HOOK_IDS = {
    "composition-context-received",
    "profile-before-seal",
    "runtime-before-plan",
    "runtime-before-tool",
    "runtime-after-tool",
    "runtime-before-final-validation",
    "recomposition-requested",
    "runtime-completed",
}
REQUIRED_FORBIDDEN_CAPABILITIES = {
    "grant_capability",
    "mutate_active_profile",
    "bypass_policy_filter",
    "bypass_validator",
    "access_unscoped_data",
    "execute_unregistered_tool",
    "write_secret_or_raw_trace",
    "change_module_version_pin",
}
REQUIRED_FAILURE_MODES = {
    "unknown_hook": "fail_closed",
    "schema_failure": "fail_closed",
    "policy_denial": "fail_closed",
    "missing_evidence": "fail_closed",
    "unregistered_hook_request": "fail_closed",
}


class HooksUsageModelError(ValueError):
    """Raised when the HOOKS usage model is invalid."""


def validate_policy(
    policy: Mapping[str, Any],
    *,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    schema = _load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)

    violations = _policy_violations(policy)
    report = {
        "contract_version": CONTRACT_VERSION,
        "status": "passed" if not violations else "failed",
        "summary": {
            "hook_count": len(policy["hook_points"]),
            "forbidden_capability_count": len(policy["forbidden_capabilities"]),
            "failure_mode_count": len(policy["mandatory_failure_modes"]),
        },
        "violations": violations,
    }
    if violations:
        raise HooksUsageModelError(
            "HOOKS usage model failed validation: " + "; ".join(violations)
        )
    return report


def assert_policy_current(
    *,
    policy_path: Path = DEFAULT_POLICY,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    return validate_policy(_load_json(policy_path), schema_path=schema_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the SCAS HOOKS usage model policy.",
    )
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = assert_policy_current(policy_path=args.policy, schema_path=args.schema)
    except (OSError, json.JSONDecodeError, HooksUsageModelError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1 if args.check else 2

    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True), end="\n")
    return 0


def _policy_violations(policy: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []

    forbidden = set(policy["forbidden_capabilities"])
    missing_forbidden = REQUIRED_FORBIDDEN_CAPABILITIES - forbidden
    if missing_forbidden:
        violations.append(
            "missing forbidden capabilities: " + ", ".join(sorted(missing_forbidden))
        )

    failure_modes = dict(policy["mandatory_failure_modes"])
    for failure_mode, required_value in REQUIRED_FAILURE_MODES.items():
        if failure_modes.get(failure_mode) != required_value:
            violations.append(f"{failure_mode} must be {required_value}")

    hooks = list(policy["hook_points"])
    hook_ids = [str(hook["id"]) for hook in hooks]
    missing_hooks = REQUIRED_HOOK_IDS - set(hook_ids)
    unexpected_hooks = set(hook_ids) - REQUIRED_HOOK_IDS
    duplicate_hooks = sorted({hook_id for hook_id in hook_ids if hook_ids.count(hook_id) > 1})
    if missing_hooks:
        violations.append("missing hook points: " + ", ".join(sorted(missing_hooks)))
    if unexpected_hooks:
        violations.append("unexpected hook points: " + ", ".join(sorted(unexpected_hooks)))
    if duplicate_hooks:
        violations.append("duplicate hook points: " + ", ".join(duplicate_hooks))

    for hook in hooks:
        hook_id = str(hook["id"])
        hook_forbidden = set(hook["forbidden_effects"])
        missing_hook_forbidden = REQUIRED_FORBIDDEN_CAPABILITIES - hook_forbidden
        if missing_hook_forbidden:
            violations.append(
                f"{hook_id} missing forbidden effects: "
                + ", ".join(sorted(missing_hook_forbidden))
            )

        allowed_overlap = set(hook["allowed_effects"]) & hook_forbidden
        if allowed_overlap:
            violations.append(
                f"{hook_id} allows forbidden effects: "
                + ", ".join(sorted(allowed_overlap))
            )

        if not hook["required_evidence"]:
            violations.append(f"{hook_id} must require evidence")
        if not hook["required_profile_bindings"]:
            violations.append(f"{hook_id} must bind to profile fields")

    return violations


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HooksUsageModelError(f"{_repo_path(path)} must contain a JSON object")
    return payload


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
