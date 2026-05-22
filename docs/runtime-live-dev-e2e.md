# Runtime Live Dev E2E Gate

## Purpose

This gate proves the first productive runtime path against live development
infrastructure:

```text
Task Intake
-> Task Analyzer
-> Cloudflare Composition Context
-> Runtime Profile
-> Hetzner PostgreSQL Run
-> Hetzner Artifact Events and Checkpoints
-> Control API Retrieval Context
-> Tool Gateway
-> Validator Framework
-> Runtime Result
```

It is intentionally manual because it requires live Cloudflare and Hetzner
credentials and should not run on every pull request.

## Required Environment

Set these variables on the machine that runs the gate:

```bash
export SCAS_CONTROL_API_URL="https://scas-control-api-dev.still-butterfly-bbff.workers.dev"
export SCAS_RUNTIME_DATABASE_URL="postgresql://..."
export SCAS_RUNTIME_ARTIFACT_ROOT="/opt/scas/runtime"
export SCAS_REPOSITORY_ROOT="/path/to/skill-centric-agent-system"
```

`SCAS_RUNTIME_DATABASE_URL` must point to the Hetzner runtime PostgreSQL
database. Productive runtime artifacts must be written under the Hetzner
artifact root.

## Command

```bash
python scripts/runtime/live_dev_e2e.py \
  --task-file examples/tasks/code-review-task.json
```

The script uses the Cloudflare Control API for both composition and retrieval,
opens the Hetzner PostgreSQL runtime store, writes JSON artifacts to the
configured artifact root, runs the minimal runtime loop, and prints a JSON
summary.

## Passing Criteria

The gate passes when the output includes:

- `status: "passed"`
- `composition_status: "ready"`
- `run_status: "succeeded"`
- `stop_reason: "completed"`
- `event_count` greater than zero
- `checkpoint_count` greater than zero

Any failed composition, retrieval scope expansion, profile enforcement denial,
tool failure, validator failure, or PostgreSQL persistence error fails the gate.
