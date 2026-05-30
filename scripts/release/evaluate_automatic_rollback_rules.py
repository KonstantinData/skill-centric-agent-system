from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def evaluate(
    policy: dict[str, Any],
    pre_canary_report: dict[str, Any],
    rollout_metadata: dict[str, Any],
) -> dict[str, Any]:
    trigger_policy = policy.get("trigger_policy")
    if not isinstance(trigger_policy, dict):
        raise ValueError("policy.trigger_policy must be an object.")
    target_policy = policy.get("rollback_target_policy")
    if not isinstance(target_policy, dict):
        raise ValueError("policy.rollback_target_policy must be an object.")

    rollback_on_pre_canary_failed = bool(
        trigger_policy.get("rollback_on_pre_canary_failed", True)
    )
    pre_canary_status = str(pre_canary_report.get("status") or "").lower()

    rollback_required = rollback_on_pre_canary_failed and pre_canary_status != "passed"
    rollback_allowed = True
    rollback_target: dict[str, Any] = {}
    failure_reasons: list[str] = []
    remediation_paths: list[str] = []

    if rollback_required:
        lkg = rollout_metadata.get("last_known_good_versions")
        if not isinstance(lkg, dict):
            rollback_allowed = False
            failure_reasons.append(
                "Rollback required but rollout metadata is missing last_known_good_versions."
            )
        else:
            required_fields = target_policy.get("required_metadata_fields")
            if not isinstance(required_fields, list):
                raise ValueError(
                    "rollback_target_policy.required_metadata_fields must be an array."
                )
            missing_fields = [
                field
                for field in required_fields
                if not isinstance(field, str) or field not in lkg
            ]
            if missing_fields:
                rollback_allowed = False
                failure_reasons.append(
                    "Rollback required but last_known_good metadata is missing fields: "
                    + ", ".join(sorted(str(field) for field in missing_fields))
                )

            require_signed = bool(
                target_policy.get("require_signed_last_known_good", True)
            )
            signature_verified = bool(lkg.get("signature_verified", False))
            if require_signed and not signature_verified:
                rollback_allowed = False
                failure_reasons.append(
                    "Rollback required but last-known-good signature is not verified."
                )

            rollback_target = {
                "descriptor_version": lkg.get("descriptor_version"),
                "policy_version": lkg.get("policy_version"),
                "signature_ref": lkg.get("signature_ref"),
                "signature_verified": signature_verified,
            }

        if not rollback_allowed:
            remediation_paths.append(
                "Publish a signed and verified last-known-good descriptor/policy version "
                "record in rollout metadata before retrying pre-canary promotion."
            )
            remediation_paths.append(
                "Re-run `python scripts/release/evaluate_pre_canary_gate.py` and "
                "`python scripts/release/evaluate_automatic_rollback_rules.py`."
            )
    else:
        rollback_target = {
            "descriptor_version": None,
            "policy_version": None,
            "signature_ref": None,
            "signature_verified": None,
        }

    status = "passed" if (not rollback_required or rollback_allowed) else "failed"

    return {
        "status": status,
        "rollback_required": rollback_required,
        "rollback_allowed": rollback_allowed,
        "rollback_target": rollback_target,
        "trigger_reasons": pre_canary_report.get("failure_reasons", []),
        "failure_reasons": failure_reasons,
        "required_remediation_paths": remediation_paths,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate automatic rollback rules for pre-canary safety regressions."
        ),
    )
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--pre-canary-report", type=Path, required=True)
    parser.add_argument("--rollout-metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-failed", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = evaluate(
            load_json(args.policy),
            load_json(args.pre_canary_report),
            load_json(args.rollout_metadata),
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")

    if args.fail_on_failed and result["status"] != "passed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
