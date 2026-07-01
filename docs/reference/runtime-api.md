# Runtime API and CLI Contract

## Purpose

This document defines the runtime invocation and inspection surface for the
productive Runtime Phase. The CLI and any future HTTP API must use the same
semantics even when their transport formats differ.

The machine-readable example contract lives in `schemas/runtime-api.schema.json`
and `examples/runtime-api/`.

## Commands

The runtime surface has five commands:

```text
start run
get status
get result
cancel run
retry run
```

The direct `scas-runtime-start` command remains a compatibility alias for
immediate fixture-backed `start run`. Queue-backed production operation uses the
grouped runtime CLI.

The transport-neutral service implementation is
`src/skill_centric_agent_system/runtime/api.py`. HTTP deployments must expose
the same semantics:

- `POST /runtime/runs`
- `GET /runtime/runs/{id}`
- `GET /runtime/runs/{id}/result`
- `POST /runtime/runs/{id}/cancel`
- `POST /runtime/runs/{id}/retry`

Every read and write is tenant-scoped. Tenant context is derived from the
authenticated API principal and checked against the task or queue record; prompt
text and client-provided body fields cannot widen tenant authority.

## Start Run

Input:

- task envelope,
- environment,
- composition context source or Control API URL,
- Control API bearer token when live Control API calls are used,
- artifact root,
- storage mode,
- repository root when repository tools are allowed,
- optional `run_minimal_loop` flag for local dev execution.

For CLI execution, productive storage is selected with:

```text
--storage-mode postgres --database-url "$SCAS_RUNTIME_DATABASE_URL"
```

The `--database-url` flag may be omitted when `SCAS_RUNTIME_DATABASE_URL` is set
in the process environment. API-shaped requests must reference a secret or
environment variable, not include a literal connection string.

Live Control API calls require:

```text
--control-plane-url "$SCAS_CONTROL_API_URL" --control-plane-token "$SCAS_CONTROL_API_TOKEN"
```

The token flag may be omitted when `SCAS_CONTROL_API_TOKEN` is set in the
process environment.

Output:

- run ID,
- task ID,
- profile ID,
- profile version,
- status,
- stop reason,
- artifact root URI,
- runtime response when execution runs immediately.

The command must fail before execution when no Control Plane client or explicit
composition context response is available.

For production use, `start run` may enqueue a runtime queue item instead of
executing immediately. When `run_immediately=false`, the response identifies the
queue item and the initial status is `queued`; a worker later claims the item
and creates the concrete runtime run attempt. Queue payloads are artifact
references in the Hetzner Runtime Plane and must not inline secrets or raw
provider credentials.

CLI:

```bash
scas-runtime queue enqueue \
  --storage-mode postgres \
  --database-url "$SCAS_RUNTIME_DATABASE_URL" \
  --artifact-root /opt/scas/runtime \
  --task-file task.json \
  --idempotency-key tenant-task-2026-07-01
```

Workers process queued execution with tenant limits:

```bash
scas-runtime queue worker-once \
  --storage-mode postgres \
  --database-url "$SCAS_RUNTIME_DATABASE_URL" \
  --artifact-root /opt/scas/runtime \
  --repository-root /srv/scas/workspaces/runtime \
  --worker-id runtime-worker-1 \
  --tenant-running-limit daskuechenhaus=2
```

When the minimal loop is enabled, the runtime dispatches a deterministic
strategy from `profile.task_type`. The supported first-slice strategies are
`code-review`, `research`, `task-execution`, and `general-task`. The response
contains `runtime_output`, which conforms to `schemas/runtime-output.schema.json`.

When runtime execution continues after a controlled recomposition request, the
result must expose the attempted run IDs and recomposed profile IDs. The
original run remains terminal with `needs_recomposition`; the continued attempt
uses a new run ID and a new immutable profile generation.

## Get Status

Input:

- run ID.

Output:

- run ID,
- task ID,
- profile ID,
- status,
- stop reason,
- timestamps,
- token budget and usage,
- last checkpoint phase when available.

## Get Result

Input:

- run ID.

Output:

- final run status,
- stop reason,
- validation result references,
- runtime response summary,
- attempt run IDs,
- recomposed profile IDs,
- artifact references,
- event and checkpoint counts.

If the run is not terminal, the result command must return a structured
non-terminal response instead of fabricating a result.

## Cancel Run

Input:

- run ID,
- reason.

Output:

- run ID,
- previous status,
- new status,
- stop reason `cancelled`,
- event reference for the cancellation.

Cancellation is allowed only for queued, claiming, or running work. Queue
cancellation marks a non-terminal queue item `cancelled`; when a runtime run
already exists, the run is also completed with status and stop reason
`cancelled`. Running execution checks cooperative cancellation before each
runtime phase and before each planned tool action.

CLI:

```bash
scas-runtime queue cancel \
  --storage-mode postgres \
  --database-url "$SCAS_RUNTIME_DATABASE_URL" \
  --artifact-root /opt/scas/runtime \
  --queue-id queue-example
```

## Retry Run

Input:

- source run ID,
- reason.

Output:

- source run ID,
- new run request metadata,
- parent traceability reference.

Retry creates new queued work or a new run. It must not reopen or mutate a
terminal source run. Automatic queue retry moves failed work to
`retry_scheduled` until `max_attempts` is exhausted, then to `dead_lettered`.
Manual replay of cancelled, failed, or dead-lettered work creates a new queue
item from the original task payload and composition context artifacts.

CLI:

```bash
scas-runtime queue retry \
  --storage-mode postgres \
  --database-url "$SCAS_RUNTIME_DATABASE_URL" \
  --artifact-root /opt/scas/runtime \
  --queue-id queue-example
```

## Error Response

Every command returns structured errors:

```json
{
  "error": {
    "code": "runtime_run_not_found",
    "message": "Runtime run was not found."
  }
}
```

Error codes are stable identifiers. Error messages are for operators.

## Retention CLI

Runtime retention cleanup is exposed through the shared runtime CLI:

```bash
scas-runtime retention plan \
  --storage-mode postgres \
  --database-url "$SCAS_RUNTIME_DATABASE_URL" \
  --artifact-root /opt/scas/runtime
```

`retention plan` reads runtime metadata and returns expired and retained run
and artifact references without touching the filesystem.

```bash
scas-runtime retention apply \
  --storage-mode postgres \
  --database-url "$SCAS_RUNTIME_DATABASE_URL" \
  --artifact-root /opt/scas/runtime
```

`retention apply` is still a dry-run unless `--confirm` is present. Dry-run
apply resolves artifact URIs, records missing or unsafe entries, writes a
cleanup report, and keeps artifacts in place.

```bash
scas-runtime retention apply \
  --storage-mode postgres \
  --database-url "$SCAS_RUNTIME_DATABASE_URL" \
  --artifact-root /opt/scas/runtime \
  --confirm
```

Confirmed apply deletes only expired artifact files that resolve under the
configured artifact root. It never deletes runtime metadata rows in the first
cleanup slice.

The same CLI path is scheduled through
`.github/workflows/runtime-retention-cleanup.yml`. Scheduled runs are dry-run
only and upload non-secret cleanup evidence. Manual workflow dispatch can run a
confirmed delete after the dry-run report is reviewed. Production workflow
dispatches, including dry-runs, require `confirm_production=true` and the
protected `production` GitHub environment before touching production retention
paths.

## Storage Modes

Supported storage modes:

- `memory`: local tests and fixture-backed dry runs,
- `postgres`: Hetzner Runtime Plane,
- `recordset`: future offline inspection/export mode.

Productive Runtime Phase uses `postgres` with the Hetzner PostgreSQL database
and the Hetzner artifact root, normally `/opt/scas/runtime`.
