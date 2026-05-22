# Runtime Preflight Gate

## Purpose

This document defines the entry gate before productive Runtime Phase work. The
goal is not to specialize the agent for one task type. The goal is to make the
generic runtime primitives stable enough that every task can be composed into a
task-local Runtime Agent Profile and executed without capability drift.

Productive Runtime Phase means:

- real Hetzner runtime storage, not only in-memory fixtures,
- real Cloudflare Control API calls for composition and retrieval,
- reproducible run state with persisted events, checkpoints, tool invocations,
  validation results, and artifact URIs,
- hard enforcement of Runtime Agent Profile boundaries,
- observable failure modes with constrained stop reasons,
- no public production launch commitment unless a separate release gate says so.

## Phase 0 Order

The Feature Backlog order for Phase 0 is:

1. `P0.01 Runtime Preflight Gate: Synchronize Backlog and Roadmap`
2. `P0.02 Runtime Preflight Gate: Finalize Terms and Naming`
3. `P0.03 Runtime Preflight Gate: Define Productive Runtime Phase`
4. `P0.04 Runtime Preflight Gate: Verify Dev Infrastructure Status`
5. `P0.05 Runtime Preflight Gate: Define Runtime Entry Criteria`
6. `P0.06 Runtime Preflight Gate: Define Generic Validation Scenarios`
7. `P0.07 Runtime Preflight Gate: Define Risk Boundaries`

Phase 1 must not start until the Phase 0 checklist below is satisfied or each
exception is tracked as an explicit backlog item.

## Naming Rules

Composition and runtime identifiers use kebab-case unless a third-party API
requires another format.

Required conventions:

- `task_type`: kebab-case, for example `code-review`, `research`, `task-execution`.
- `capability_class`: schema-defined snake-case enum where already established,
  for example `tool_access`, `memory_access`, and `knowledge_access`.
- module IDs: kebab-case, for example `git-diff-analysis`.
- scope IDs: kebab-case, for example `repository-readonly`.
- tool IDs: kebab-case, for example `filesystem-read`.
- scoring signals: `type:value`, where the value follows the target field's
  convention, for example `task_type:code-review`.

Do not mix equivalent identifiers such as `code-review` and `code_review`.
Python function names may use snake_case when they are code symbols, but JSON
contracts, examples, seeds, docs, and runtime profile values must use the
identifier convention above.

## Dev Infrastructure Verification

Before Phase 1 begins, verify and record the current dev state:

- Cloudflare Worker `scas-control-api-dev` is reachable.
- D1 database `scas-control-dev` has the expected migrations and registry seed.
- R2 buckets `scas-knowledge-dev` and `scas-memory-dev` exist.
- Vectorize bindings `SCAS_KNOWLEDGE_INDEX` and `SCAS_MEMORY_INDEX` exist.
- Hetzner PostgreSQL database `scas_runtime` is reachable.
- Hetzner artifact root `/opt/scas/runtime` exists and is writable by the
  runtime role.
- GitHub Actions secrets are present without exposing secret values.
- CI is green for Python tests, linting, JSON validation, Worker tests, Worker
  type checks, and Worker dry-run deploy checks.

Recommended local checks:

```powershell
python -m pytest
python -m ruff check .
npm run worker:typecheck
npm run worker:test
npm run worker:check
```

Recommended remote checks:

```powershell
npm run worker:deploy:dev
curl -s -X POST https://scas-control-api-dev.still-butterfly-bbff.workers.dev/composition/context `
  -H "content-type: application/json" `
  --data-binary @examples/control-api/composition-context-request.json
```

Run the manual GitHub Actions infrastructure smoke workflow when secret and SSH
reachability need to be verified from CI.

## Entry Criteria

Phase 1 productive runtime implementation may start when:

- tests and lint checks are green,
- Cloudflare and Hetzner migration state is known,
- dev Control API Worker is reachable,
- Hetzner Runtime DB is reachable,
- no open contract contradictions remain,
- runtime data stays on Hetzner,
- Cloudflare receives only Control Plane data and validated memory records,
- risk boundaries below are accepted for the first productive runtime slice.

If any criterion is not met, create or update a Feature Backlog item before
starting the dependent Phase 1 task.

## Generic Validation Scenarios

These scenarios validate generic runtime primitives. They are not separate
agents and must not hardcode role-specific behavior into the runtime.

| Scenario | Purpose | Expected Runtime Behavior |
| --- | --- | --- |
| Research-like task | Validate retrieval, scoped knowledge, synthesis, and output validation | Compose retrieval/context capabilities, load only allowed knowledge/memory, emit validation result |
| Code-review-like task | Validate repository read tools, diff analysis, findings contract | Use profile-allowed read tools, persist tool invocations, validate file-referenced findings |
| Task-execution-like task | Validate planner/executor sequencing and risk gating | Execute only allowed actions, deny write/destructive actions unless explicitly composed and authorized |
| Missing capability task | Validate recomposition without self-granting | Stop with `needs_recomposition` or request a new profile with parent traceability |

## Risk Boundaries

First productive runtime slice:

- read-only repository tools are allowed when the profile grants them,
- write-capable tools require explicit policy, risk, and authorization gates,
- destructive commands are forbidden unless a later ADR and profile policy allow
  them,
- shell execution must stay behind constrained adapters; free-form shell strings
  are forbidden,
- secrets must not be written into artifacts, events, docs, examples, or logs,
- tool output must be bounded by per-tool output limits,
- long-running work must respect duration and token budgets,
- raw runtime traces and raw tool outputs must not cross from Hetzner into
  Cloudflare.

## Phase 1 Order

After Phase 0 is satisfied, implement Phase 1 in this order:

1. `P1.01 Finalize Generic Runtime Contract`
2. `P1.02 Define Runtime API/CLI Contract`
3. `P1.03 Wire Real Hetzner Runtime Storage`
4. `P1.04 Complete Profile Enforcement`
5. `P1.05 Harden Tool Gateway for Productive Runtime Use`
6. `P1.06 Bind Context Manager to Control API Retrieval`
7. `P1.07 Make Validator Framework Generic`
8. `P1.08 Implement Controlled Recomposition Path`
9. `P1.09 Build Live Dev E2E Gate`
10. `P1.10 Establish Operations Baseline`

The existing follow-up items for async indexing, AI Gateway live secret rollout,
runtime expansion beyond the initial fixture, and retention cleanup remain
backlog work after the Phase 1 core runtime gate unless explicitly pulled
forward by a failing entry criterion.
