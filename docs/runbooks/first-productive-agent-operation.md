# First Productive Agent Operation

## Purpose

This runbook defines the controlled path from a certified staging release to the
first productive SCAS agent operation. It does not approve production launch and
does not replace `docs/policies/production-readiness.md`.

The immediate goal is to let the agent perform bounded, supervised work against
the certified staging runtime while preserving the same fail-closed profile,
tool, data, and evidence boundaries used by the release gate.

## Current Certified Baseline

The current staging-certified baseline is:

- repository commit:
  `5bf301b8c0fdfe6d547c50890c72bbd6a0bf7648`
- target environment: `staging`
- release scope: `initial-productive-core`
- certification mode: `certify`
- production-readiness run:
  `https://github.com/KonstantinData/skill-centric-agent-system/actions/runs/27407053285`
- live runtime gates run:
  `https://github.com/KonstantinData/skill-centric-agent-system/actions/runs/27406070114`
- AI Gateway live smoke run:
  `https://github.com/KonstantinData/skill-centric-agent-system/actions/runs/27406070126`
- certification artifact result: `status = "staging-ready"`,
  `final_decision = "certified"`, `open_release_gaps = []`

This baseline certifies staging only. It does not certify `prod`.

## Allowed First Operation Scope

The first productive operation may use the certified staging environment for
supervised SCAS repository and platform work only.

Allowed task classes match the live handler-binding evidence:

- `code-review`
- `research`
- `task-execution`
- `general-task`

Allowed capabilities:

- profile-selected read tools,
- profile-selected retrieval/context calls,
- version-pinned executable skill handlers,
- Hetzner PostgreSQL runtime state,
- Hetzner artifact roots under `/opt/scas/runtime/staging`,
- Cloudflare staging Control Plane resources.

Write-capable execution remains limited to the already governed first slice:
`filesystem-write` with `repository-write` scope, explicit approval policy,
high-risk gating, rollback metadata, relative path enforcement, and
dry-run-by-default behavior.

## Not Allowed

The first productive operation must not:

- run against `prod`,
- process production customer data,
- use dev evidence as staging or production evidence,
- copy raw runtime traces or raw tool outputs from Hetzner into Cloudflare,
  Notion, GitHub comments, or release evidence,
- expose secrets, tokens, private keys, provider credentials, or `.env` values,
- run destructive cleanup, rebuilds, or production writes,
- broaden tools, data scopes, memory scopes, or knowledge scopes outside the
  sealed Runtime Agent Profile,
- claim `production-ready` without a separate `prod` certification run.

## Required Preflight

Before each first-operation run:

1. Confirm the repository commit is the certified commit or run a fresh staging
   certification for the new commit.
2. Confirm the target environment is `staging`.
3. Confirm the task fits one of the allowed task classes.
4. Confirm the task does not require production data or production writes.
5. Confirm any write-capable path is explicitly approved and remains
   dry-run-first.
6. Confirm live evidence is still within the recertification cadence in
   `policies/runtime/production-recertification-policy.json`.
7. Record the operation in the SCAS tracker with owner, purpose, target
   environment, commit, expected task class, and stop conditions.

## Stop Conditions

Stop immediately and keep the operation non-certified when any of these occur:

- a GitHub Actions gate fails,
- Control Plane auth returns `401` or `403`,
- a runtime run stops with anything other than `completed` for expected success,
- handler-binding evidence is missing or not `passed`,
- artifact roots are not under `/opt/scas/runtime/staging`,
- the task asks for unapproved writes, production data, destructive cleanup, or
  capability expansion,
- telemetry or validation reports a critical failure,
- evidence would require storing a secret or raw trace outside Hetzner.

## Operational Path

Use the existing live runtime workflow for the first approved bounded
single-task staging operation. The first real approved SCAS operation task is
versioned at
`operations/staging-tasks/first-productive-scas-operations-review.json`.

```bash
gh workflow run live-runtime-gates.yml \
  -f target_environment=staging \
  -f control_api_url=https://scas-control-api-staging.still-butterfly-bbff.workers.dev \
  -f run_live_dev_e2e=true \
  -f run_postgres_concurrency_smoke=false \
  -f run_live_retrieval_vectorize_smoke=false \
  -f seed_control_plane_dev=false \
  -f live_task_suite=single \
  -f live_task_file=operations/staging-tasks/first-productive-scas-operations-review.json \
  -f confirm_production=false
```

The task file must be committed, non-secret, and approved for staging. Real
productive-operation task files should live under `operations/staging-tasks/`.
`examples/tasks/` remains available for tests, demonstrations, and generic
fixtures. Do not pass private task content through workflow inputs.
Production use of this workflow is fail-closed unless `confirm_production=true`
is supplied and the protected `production` GitHub environment approves the run.
Production Control Plane seeding remains blocked here; use a dedicated
production migration control path instead.

## Dedicated Workflow Decision

No dedicated productive-operation workflow is required before the first
approved staging operation. The existing `live-runtime-gates.yml` path is
already manual, supports `target_environment=staging`, supports
`live_task_suite=single`, requires a committed non-secret task file, runs on
Hetzner, writes staging artifacts under `/opt/scas/runtime/staging`, and
uploads `live-runtime-handler-binding-evidence`.

Create a dedicated manual productive-operation workflow only after a real
staging operation through the existing path proves a concrete operator,
evidence, or safety gap. If that happens, the follow-up workflow must remain
`workflow_dispatch` only, stay restricted to `staging` until `prod` is
separately approved, require committed non-secret task fixtures, upload
non-secret operation evidence, preserve the stop conditions in this runbook,
and update `docs/runbooks/operations-runbook.md`.
