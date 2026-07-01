# Runtime Queue Operations Runbook

## Start Workers

Run one queue item:

```bash
scas-runtime queue worker-once \
  --storage-mode postgres \
  --database-url "$SCAS_RUNTIME_DATABASE_URL" \
  --artifact-root /opt/scas/runtime \
  --repository-root /srv/scas/runtime-workspaces/default \
  --worker-id runtime-worker-1 \
  --queue-name default \
  --tenant-running-limit daskuechenhaus=2
```

Run as a long-lived worker:

```bash
scas-runtime queue worker-loop \
  --storage-mode postgres \
  --database-url "$SCAS_RUNTIME_DATABASE_URL" \
  --artifact-root /opt/scas/runtime \
  --repository-root /srv/scas/runtime-workspaces/default \
  --worker-id runtime-worker-1 \
  --queue-name default \
  --poll-interval-seconds 1
```

## Stop Workers

Use normal process supervision shutdown. A worker must release claims by
finalizing the run, marking it cancelled, or letting stale-claim recovery move
expired work back to `retry_scheduled`.

## Stuck Claims

1. Inspect `runtime.runtime_queue_items` where `status in ('claiming', 'running')`.
2. Check `claimed_until` and `heartbeat_at`.
3. Run stale-claim recovery through the runtime queue manager or the equivalent
   operator command.
4. Confirm recovered work moved to `retry_scheduled`.

## Tenant Pause

Add the tenant to the worker disabled-tenant configuration:

```bash
--disabled-tenant-id daskuechenhaus
```

Disabled tenants cannot be claimed by workers configured with that denylist.
Control Plane tenant status must also block new starts for disabled or archived
tenants.

## DLQ Triage

1. Inspect `runtime.runtime_dead_letters` by tenant and `created_at`.
2. Read `error_type` and `error_message`.
3. Confirm the task payload artifact is safe to replay.
4. Use `scas-runtime queue retry --queue-id <queue-id>` only after confirming
   the root cause is resolved.

## Quota Adjustment

Adjust worker flags for tenant limits:

- `--tenant-running-limit TENANT_ID=LIMIT`
- `--tenant-token-limit-per-minute TENANT_ID=LIMIT`
- `--tenant-tool-call-limit-per-minute TENANT_ID=LIMIT`

Production quota changes require release evidence because they alter tenant
isolation behavior.

## Cross-Tenant Suspicion

Treat suspected cross-tenant queue reads or claims as a blocking incident:

1. Stop affected workers.
2. Capture `runtime_queue_items`, `runtime_run_claims`, and `runtime_events`
   metadata without raw tool outputs.
3. Verify tenant IDs, area IDs, worker allowlists, and disabled tenant config.
4. Do not replay affected work until tenant isolation tests pass.

## Required Metrics

Runtime operations dashboards must track:

- queue depth by tenant/status,
- claim latency,
- run duration,
- tenant saturation,
- policy denials,
- retry rate,
- dead-letter rate,
- quota exhaustion events.
