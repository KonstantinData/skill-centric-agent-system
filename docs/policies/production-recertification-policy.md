# Production Recertification Policy

## Purpose

This policy defines when a SCAS release claim must be recertified after a
production-readiness evidence run. It turns the release cadence, expiry rules,
and mandatory recertification triggers into a machine-checkable policy.

The executable policy lives in
`policies/runtime/production-recertification-policy.json` and is validated by
`scripts/release/validate_production_recertification_policy.py`.

## Cadence

| Environment | Release Claim | Required Mode | Maximum Evidence Age | Cadence |
| --- | --- | --- | --- | --- |
| `dev` | `initial-productive-core` | `evidence-only` | 30 days | Monthly |
| `staging` | `staging-ready` | `certify` | 45 days | Per release |
| `prod` | `production-ready` | `certify` | 90 days | Quarterly |

The next review date is anchored to the completed certification timestamp. A
staging or production claim is stale once the maximum evidence age is reached.
Stale evidence changes the release decision outcome to
`recertification-required` until fresh production-readiness evidence is
generated.

## Mandatory Recertification Triggers

Recertification is required when any of these events occur:

- release scope changes,
- target environment changes,
- Runtime Plane or Control Plane behavior changes,
- production skill, handler, instruction pack, or handler version policy
  changes,
- policy, schema, validator, HOOKS model, or release gate changes,
- security, privacy, data-governance, token-scope, or threat-model posture
  changes,
- branch protection, required checks, workflow hardening, dependency policy, or
  supply-chain gate changes,
- Cloudflare or Hetzner live infrastructure resources, secrets, queues,
  databases, buckets, indexes, or runtime artifact roots change,
- a production incident, failed release gate, failed pre-canary gate, rollback,
  or incident-locked regression occurs, or
- target-environment evidence expires.

Each trigger requires a fresh production-readiness evidence run. A narrative
statement cannot replace the rerun.

## Release Decision Requirements

Every release decision must record:

- release commit,
- target environment,
- release scope,
- certification mode,
- gate results,
- external evidence,
- open release gaps,
- waivers,
- owner,
- completion timestamp,
- next review due timestamp, and
- recertification triggers.

Release evidence must not contain secret values, private keys, bearer tokens,
raw runtime traces, raw tool outputs, or confidential customer data.

## Waivers

Waivers are allowed only for bounded, owner-approved risks. A waiver must name
the gate, risk, owner, expiry condition, and compensating control. Waivers
expire after at most 14 days.

Waivers are forbidden for secret exposure, unverified release commits, and
missing production-readiness evidence.

## CI Gate

The policy must pass:

```bash
PYTHONPATH=src python scripts/release/validate_production_recertification_policy.py --check
```

The command runs in both CI contract tests and the Production Readiness
Evidence workflow.
