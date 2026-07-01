# Runtime Parallel Execution Hardening Audit Closure Definition Of Done

Status: accepted
Version: 2026-07-01
Scope: strict audit closure for RPEH-2026 after the independent audit findings.

## Purpose

This Definition of Done closes the audit gap between "local gates passed" and
"the RPEH audit can only report Done." It supersedes any narrower interpretation
of RPEH completion for audit handoff. The work is Done only when every criterion
below is implemented, documented, and verified.

## Audit Closure Criteria

### P1 Findings Must Be Closed

- The long-lived PostgreSQL worker loop must not hold one uncommitted
  transaction for the lifetime of the process. Each worker-loop iteration must
  commit on success and roll back on unhandled failure.
- Runtime start and queue enqueue paths must reject server-authoritative
  `tenant_authority` tenant or area mismatches before a run or queue item is
  persisted.
- Tests must prove both behaviors directly.

### Queue And Claim Integrity

- Claiming must use `FOR UPDATE SKIP LOCKED`.
- Claiming must create the queue item update, attempt row, and claim row in one
  store operation.
- Claim selection must not use a fixed candidate cap that can starve eligible
  tenants.
- Heartbeat, cancel, and stale recovery must update both queue state and active
  claim audit rows.

### Tenant Isolation

- Disabled or archived tenant authority blocks immediate runtime starts.
- Disabled or archived tenant authority blocks queue enqueue when tenant
  authority is present.
- Tenant and area mismatches between task claims and server authority fail
  closed.
- Queue/API tenant-scoped read and write operations reject foreign tenant or
  area access.

### Budget And Quota Closure Scope

- RPEH audit closure requires executable tenant token and tool-call quota
  reservation, exhaustion, refund, and finalization behavior.
- Broader quota dimensions such as data-read, memory-operation, duration, tag,
  and longer rolling-window policies are production-readiness extensions until
  the runtime exposes authoritative counters for those dimensions.
- A production-ready claim must not imply those broader dimensions are
  implemented unless migrations, runtime counters, tests, and release evidence
  exist.

### Observability Closure Scope

- RPEH audit closure requires bounded local queue metrics for queue depth,
  active claims, retry, dead-letter, quota exhaustion, policy denial, claim
  latency, and run duration signals.
- Production dashboards and alerts remain production-readiness evidence. A
  production-ready claim must not be made without dashboard or alert evidence
  for the target environment.

### Documentation And Release Claims

- `docs/reference/runtime-run-queue-contract.md`,
  `docs/runbooks/runtime-queue-operations.md`, and this audit-closure DoD must
  agree.
- `docs/policies/production-readiness.md` remains the authority for staging and
  production evidence. Dev/local green gates do not certify production.
- Any audit output must distinguish:
  - `DoD Done`: every RPEH audit-closure criterion passes locally.
  - `Production Readiness Pending`: target-environment evidence is not part of
    local RPEH audit closure.

## Verification Gates

Before reporting DoD Done, run and pass:

```powershell
python -m pytest tests/test_runtime_queue_worker.py tests/test_tenant_runtime_e2e.py
python -m pytest
python -m ruff check .
python -m mypy src/skill_centric_agent_system
npm run worker:typecheck
npm run worker:test
npm run worker:check
git diff --check
```

If any gate fails or any criterion is not met, the audit-closure DoD is not
Done.
