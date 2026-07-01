# Runtime Run Queue Contract

Status: accepted  
Version: 2026-07-01  
Owner plane: Hetzner Runtime Plane

## Purpose

The Runtime Run Queue is the durable execution contract for productive parallel
SCAS runs. It coordinates one single-agent runtime across many independent
tasks without creating a multi-agent architecture.

## Identity Model

- `task_id`: stable user or system task identifier.
- `queue_id`: durable scheduling envelope for one queued execution request.
- `attempt_id`: durable record for one worker execution attempt of a queue item.
- `run_id`: Flight Recorder run created by one attempt after profile composition.
- `profile_id`: immutable runtime profile identity.
- `profile_generation`: profile generation for initial composition or
  recomposition.
- `profile_sha256`: SHA-256 of the exact sealed runtime profile artifact.

Terminal runs and attempts are never reopened. Retry creates new queued work or
a new attempt.

## Queue Statuses

Allowed statuses:

- `queued`
- `claiming`
- `running`
- `succeeded`
- `failed`
- `cancelled`
- `retry_scheduled`
- `dead_lettered`

Allowed transitions:

```text
queued -> claiming
retry_scheduled -> claiming
claiming -> running
claiming -> retry_scheduled
claiming -> dead_lettered
claiming -> cancelled
running -> succeeded
running -> retry_scheduled
running -> dead_lettered
running -> cancelled
```

Unknown statuses fail closed.

## Persistence

The queue contract is implemented through these Runtime Plane records:

- `runtime_queue_items`
- `runtime_run_attempts`
- `runtime_run_claims`
- `runtime_dead_letters`
- `runtime_quota_reservations`

Queue payloads are Hetzner artifact references. Queue rows must not contain
secrets, live tokens, provider credentials, raw tool outputs, or broad customer
data.

## Claiming

Workers claim with PostgreSQL `FOR UPDATE SKIP LOCKED`. A claim moves a queue
item to `claiming`, increments attempts, sets `claimed_by`, `claimed_at`,
`claimed_until`, `heartbeat_at`, `attempt_id`, and `run_id`, and writes the
matching `runtime_run_attempts` and `runtime_run_claims` rows in the same claim
operation.

Workers may claim only items matching their configured environment, queue name,
tenant allowlist, and disabled-tenant denylist.

Long-lived worker loops must commit successful PostgreSQL work and roll back
unhandled failures after each poll/execute iteration. A worker process must not
hold one uncommitted claim transaction for its entire lifetime.

Global and tenant running limits are evaluated under database advisory
transaction locks before the queue row is updated. Claim selection must not use
a fixed candidate cap that can starve eligible tenants behind ineligible locked
or saturated tenants.

## Heartbeat And Recovery

Workers refresh `heartbeat_at` and `claimed_until`. Stale `claiming` or
`running` items whose `claimed_until` is in the past are recovered to
`retry_scheduled`, their queue claim fields are cleared, and any active
`runtime_run_claims` row is released with reason `stale_recovered`.

## Retry And DLQ

Automatic retry uses exponential backoff with optional jitter. Non-retryable or
exhausted work moves to `dead_lettered` and writes `runtime_dead_letters`.
Manual retry replays the original task payload and composition context through a
new queue item. It never mutates a terminal run or attempt.

## Cancellation

Queued or claiming work is cancelled by queue state. Running work uses
cooperative cancellation checkpoints before every runtime phase and before each
planned tool action. Cancellation completes the run with status and stop reason
`cancelled`. Cancel operations clear queue claim fields and release active
claim audit rows with reason `cancelled`.

## Quotas

Before execution, the worker reserves tenant quota in
`runtime_quota_reservations`. Token and tool-call quota breaches emit
Flight Recorder `quota_exhausted` events and fail closed with the matching hard
stop reason. Reserved and finalized reservations both count against the current
quota window; refunded reservations do not.

Data-read, memory-operation, duration, tag, and longer rolling-window quota
dimensions require authoritative runtime counters before they can be claimed as
implemented. They are production-readiness extensions unless backed by
migrations, counters, tests, and release evidence.

## Profile Sealing

Every runtime run stores:

- `profile_artifact_uri`
- `profile_sha256`
- `profile_generation`
- `parent_profile_id`

Workers must execute the sealed profile emitted by the composer. Profile fields,
limits, tools, scopes, policies, and validators must not be mutated in place.
The runtime loop re-hashes the stored profile artifact before executing any
runtime phase and fails closed on mismatch.

## Observability

Runtime queue operations must preserve the profile `observability.trace_id`
across Control Plane context retrieval, Runtime Worker execution, Tool Gateway
calls, and Flight Recorder events. Production telemetry must expose aggregate
signals for queue depth, claim latency, run duration, tenant saturation, retry
rate, DLQ rate, quota exhaustion, and policy denials. Logs must not contain raw
tool outputs, secrets, provider payloads, or raw customer data.

The local operator surface exposes the same aggregate signal shape through:

```bash
scas-runtime queue metrics --storage-mode postgres --database-url "$SCAS_RUNTIME_DATABASE_URL"
```

## Tenant Runtime Evidence

Every `setup` or `active` tenant must have a sanitized Tenant Runtime Evidence
record before tenant runtime readiness can be claimed. The machine-readable
contract is `schemas/tenant-runtime-evidence.schema.json`; fixture examples
live in `examples/runtime-evidence/`.

Each record must prove, per tenant:

- queue status coverage,
- worker claim and release coverage,
- token/tool-call quota reservation coverage,
- DLQ coverage, including an explicit zero count when no dead letters exist,
- stale-claim recovery coverage, including an explicit zero count when no
  stale claim exists,
- tenant-registry match and cross-tenant contamination checks,
- runtime profile, Runtime API queue summary, and Hetzner Runtime Plane schema
  compatibility,
- sanitization: no raw traces, raw tool outputs, secrets, or personal data.

Dev fixtures use `evidence_scope = "fixture"` and
`certification_level = "dev-fixture"`. They prove the repository contract and
test gate only. Staging and production evidence must use
`evidence_scope = "target-environment"` and must reference real
target-environment Hetzner Runtime Plane evidence artifacts.
