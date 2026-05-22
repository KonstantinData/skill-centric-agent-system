# ADR-0005: Runtime Flight Recorder Observability

## Status

Accepted

## Date

2026-05-22

## Context

The runtime loop needs to be reconstructable after a run finishes or fails. The
existing Hetzner Runtime Plane already stores runs, steps, tool invocations,
validator results, artifacts, and memory candidates, but it does not yet record
why each phase stopped, how budgets were consumed, how retries avoid duplicate
records, or where phase checkpoints live.

The Runtime Agent Profile already defines observability settings and
`redact_sensitive_data`. The storage contract must respect that flag because
runtime event payloads can contain sensitive task, tool, or model data.

## Decision

Use a Flight Recorder pattern inside the Hetzner Runtime Plane.

Runtime metadata remains in Postgres. Large or sensitive payloads are stored in
the Hetzner artifact store and referenced by URI.

Add these durable runtime storage surfaces:

- `runtime_events`: append-only event stream for each run.
- `runtime_checkpoints`: phase boundary snapshots.
- `stop_reason`, token-budget, token-usage, attempt, and idempotency fields on
  runtime run and step records.

`runtime_events` must not store inline JSON payloads for planned actions,
execution details, or results. It stores:

- `planned_action_uri`
- `execution_uri`
- `result_uri`

The URI targets live under the Hetzner runtime artifact root and must follow the
profile's redaction policy before they are written.

`event_type`, `actor_role`, `stop_reason`, and checkpoint `phase` are constrained
enums. This prevents divergent writer vocabulary once multiple runtime
components emit events.

`runtime_checkpoints.step_id` is nullable. Checkpoints may occur between phases,
for example after planning completes but before executor work starts.

## Consequences

Positive:

- Runs can be reconstructed from structured events, steps, checkpoints, and
  artifact URIs.
- Runtime retries can be made idempotent with stable keys.
- Budget exhaustion and policy/validator stop reasons become queryable.
- Large and sensitive payloads stay out of high-growth Postgres rows.

Tradeoffs:

- Runtime writers must produce both Postgres event rows and artifact payloads.
- Retention and redaction policies must cover artifact URIs as well as database
  rows.
- More schema constraints mean tests and fixtures must be updated whenever the
  event vocabulary changes.

## Follow-Up

- Implement the runtime event writer around the Single Agent Runtime loop.
- Add artifact naming conventions for event payloads and checkpoints.
- Add retention jobs for runtime event artifacts.
