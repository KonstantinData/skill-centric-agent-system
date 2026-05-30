# Automatic Rollback Rules

## Purpose

This policy defines automatic rollback behavior when pre-canary safety gates
fail.
Rollback must target a signed and verified last-known-good descriptor/policy
version pair.

## Policy Artifacts

- Policy: `policies/runtime/automatic-rollback-rules.json`
- Schema: `schemas/automatic-rollback-rules.schema.json`
- Evaluator: `scripts/release/evaluate_automatic_rollback_rules.py`

## Trigger Rule

Rollback is required when:

- `rollback_on_pre_canary_failed = true`, and
- the pre-canary gate report status is not `passed`.

## Target Validation

When rollback is required, `last_known_good_versions` metadata must provide:

- `descriptor_version`,
- `policy_version`,
- `signature_ref`, and
- `signature_verified = true`.

Missing fields or unsigned targets fail closed and produce remediation paths.
