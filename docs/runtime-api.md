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

The existing `scas-runtime-start` command remains a compatibility alias for
`start run` until a grouped CLI is introduced.

## Start Run

Input:

- task envelope,
- environment,
- composition context source or Control API URL,
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

Cancellation is allowed only for `queued` or `running` runs.

## Retry Run

Input:

- source run ID,
- reason.

Output:

- source run ID,
- new run request metadata,
- parent traceability reference.

Retry creates a new run. It must not reopen or mutate a terminal source run.

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

## Storage Modes

Supported storage modes:

- `memory`: local tests and fixture-backed dry runs,
- `postgres`: Hetzner Runtime Plane,
- `recordset`: future offline inspection/export mode.

Productive Runtime Phase uses `postgres` with the Hetzner PostgreSQL database
and the Hetzner artifact root, normally `/opt/scas/runtime`.
