# Runtime Parallel Execution Hardening Definition Of Done

Status: accepted
Version: 2026-07-01
Scope: RPEH-2026 follow-up hardening for the Runtime Run Queue, Worker, API, quota, tenant status, and observability surfaces.

Follow-up audit closure criteria live in
`docs/reference/runtime-parallel-execution-hardening-audit-closure-dod.md`.
When the independent audit prompt is used, the audit-closure DoD is the stricter
closure gate.

## Purpose

This Definition of Done is the closure gate for RPEH-2026. The work is not done
until every criterion below is implemented, documented, and verified by the
listed gates or explicitly recorded as a blocker in SCAS Issues & Open
Questions.

## Done Criteria

### Queue Contract

- `docs/reference/runtime-run-queue-contract.md` defines identities, statuses,
  allowed transitions, retry, cancellation, timeout, idempotency, quota,
  profile sealing, and observability semantics.
- The status set includes `queued`, `claiming`, `running`, `succeeded`,
  `failed`, `cancelled`, `retry_scheduled`, and `dead_lettered`.
- Queue rows never store secrets, live credentials, raw tool outputs, or broad
  customer data.

### Postgres Queue Persistence

- Runtime Plane persistence includes queue, attempt, claim, dead-letter, and
  quota reservation records.
- Worker claim uses `FOR UPDATE SKIP LOCKED` and creates the queue claim bundle
  in one store operation: queue item update, attempt row, and claim row.
- Claim selection has no fixed candidate cap that can starve eligible tenants.
- Global and tenant running limits are checked under database advisory
  transaction locks before a candidate is claimed.
- Heartbeat updates both queue item lease fields and the active claim audit row.
- Stale recovery releases active claim rows with `stale_recovered`.
- Cancel releases active claim rows with `cancelled`.
- Retry and enqueue preserve idempotency keys.

### Worker Runtime

- The worker has a real poll, claim, execute, heartbeat, finalize path.
- One-shot worker processing and long-lived worker-loop operation remain
  separate CLI commands.
- The long-lived worker-loop supports cooperative graceful shutdown through a
  stop predicate and CLI process signal handling.
- Running items are finalized, cancelled, or made recoverable by stale-claim
  recovery; no runtime profile mutation is allowed in the worker.

### Tenant Isolation

- Immediate runtime starts fail closed when server-authoritative tenant status
  is not `setup` or `active`.
- Queue enqueue blocks disabled tenants when tenant authority is available and
  worker configuration blocks disabled tenants at claim time.
- Tenant and area mismatch between task claims and tenant authority is rejected.
- Cross-tenant queue suspicion remains a blocking operational incident.

### Budget And Quotas

- Workers reserve quota before runtime execution.
- Token and tool-call quotas can be configured per tenant and fail closed with
  hard stop reasons.
- Reserved and finalized quota reservations count against the active quota
  window; refunded reservations do not.
- Quota exhaustion emits Flight Recorder evidence and affects retry or
  dead-letter behavior through normal queue finalization.

### Runtime API

- Immediate API start returns persisted run status and runtime result data when
  a minimal loop is requested.
- API result lookup returns persisted response data and response artifact URI.
- Runtime API access remains tenant-scoped through `RuntimeApiPrincipal`.

### Profile Sealing

- Runtime runs persist `profile_artifact_uri`, `profile_sha256`,
  `profile_generation`, and `parent_profile_id`.
- The runtime loop hashes the sealed profile artifact before execution and fails
  closed on mismatch.
- Worker execution does not mutate profile fields, limits, tools, scopes,
  policies, or validators in place.

### Observability And Operations

- Queue metrics expose bounded aggregate queue depth, active claims, retry,
  dead-letter, quota exhaustion, policy denial, claim latency, and run duration
  signals.
- `scas-runtime queue metrics` prints the same aggregate signal shape for local
  operators.
- `docs/runbooks/runtime-queue-operations.md` explains worker start, graceful
  stop, stuck-claim recovery, tenant pause, DLQ triage, quota adjustment,
  metrics, and cross-tenant suspicion response.

### Verification Gates

Before marking the work Done, run and pass:

```powershell
python -m pytest tests/test_runtime_queue_worker.py
python -m pytest
python -m ruff check .
python -m mypy src/skill_centric_agent_system
npm run worker:typecheck
npm run worker:test
npm run worker:check
git diff --check
```

The final handoff must state any gate that could not be run. If any criterion
or gate fails, fix the gap and repeat the DoD check until all criteria pass.
