# ADR-0013: Runtime Parallel Execution Hardening

## Status

Accepted

## Date

2026-07-01

## Context

SCAS is a single-agent runtime system, but production use requires many isolated
task runs to execute in parallel across tenants. The existing runtime already
has immutable runtime profiles, Flight Recorder storage, profile enforcement,
tenant authority validation, and run/step/event persistence. It did not yet
have a first-class runtime task queue or worker claim model for production-grade
parallel execution.

Cloudflare Queues already support asynchronous Control Plane ingestion work,
especially embedding updates. Runtime task execution is different: raw runtime
traces, tool outputs, tenant customer data, and execution artifacts belong on
the Hetzner Runtime Plane. Runtime run queueing must therefore stay coupled to
Hetzner runtime storage and tenant-local execution controls.

## Decision

RPEH-2026 introduces a Postgres-backed Hetzner Runtime Queue for runtime task
execution.

The runtime queue stores task-local execution requests as metadata rows plus
artifact URIs. Queue rows do not inline task payloads or composition context.
They reference Hetzner runtime artifacts and track:

- task, tenant, and area identity;
- queue status and priority;
- schedule time, attempts, and maximum attempts;
- worker claim owner, claim time, heartbeat, and claim expiry;
- environment and queue name;
- attempt ID;
- task payload and optional composition context artifact URIs;
- resulting runtime run ID when execution begins;
- idempotency key and last error.

Workers claim queue rows through the runtime store. The PostgreSQL adapter uses
`FOR UPDATE SKIP LOCKED` to allow concurrent workers without double-claiming the
same row. Claiming is tenant-aware: global, per-tenant, environment, queue,
allowlist, and disabled-tenant filters are checked before a queued item is
moved to `claiming`.

Runtime workers execute claimed items through the existing single-agent path:

```text
Runtime Queue Item
-> RuntimeEntryPoint
-> Runtime Agent Profile
-> MinimalRuntimeLoop
-> Flight Recorder / Runtime Store
```

The worker must not mutate the active profile. Recomposition, retry, and
dead-letter behavior create new queue/run attempts or terminal queue states
instead of editing sealed profiles in place.

Cloudflare Queues remain the Control Plane ingestion queue for knowledge and
memory embedding updates. They are not the authority for runtime task execution.

## Consequences

Positive:

- SCAS can model many parallel runtime runs while preserving the single-agent
  architecture.
- Runtime queue state, run attempts, worker claims, dead letters, quota
  reservations, and tenant limits are stored in the Hetzner Runtime Plane next
  to run evidence.
- Concurrent workers can safely claim work without sharing mutable agent state.
- Tenant concurrency becomes an explicit execution control rather than an
  operational convention.
- Retry and dead-letter behavior have durable state and idempotency keys.

Costs:

- Runtime storage and schemas now include queue-specific tables and recordset
  fields.
- Worker operations require runbooks, metrics, and production gates before
  claiming high-throughput production readiness.

Non-goals:

- This does not introduce a multi-agent system.
- This does not move raw runtime traces or tool outputs into Cloudflare.
- This does not use Cloudflare Queues for tenant runtime execution.
- This does not authorize direct tenant-user grants or cross-tenant execution.

## Acceptance Criteria

- Runtime queue rows are represented in the Hetzner Runtime Plane schema.
- Postgres migrations create the runtime queue, attempts, claims, dead-letter,
  quota reservation, and profile-sealing fields and indexes.
- In-memory and Postgres runtime stores expose queue enqueue, update, and claim
  operations plus heartbeat and stale-claim recovery.
- Queue claims are tenant-aware and support global and per-tenant running
  limits.
- The Runtime Queue Worker can process a queued task through `RuntimeEntryPoint`
  and `MinimalRuntimeLoop`, write attempts and claims, reserve quota, and run as
  a long-lived worker process.
- Failed work either schedules a retry or moves to a dead-letter state.
- Tests cover successful processing, idempotent enqueue, tenant concurrency
  limits, dead-letter behavior, cancellation, stale-claim recovery, tenant API
  scoping, quota exhaustion, profile sealing, and Postgres `SKIP LOCKED`
  claiming.
