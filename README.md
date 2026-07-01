# Skill-Centric Agent System

Most agent runtimes fail by giving a model broad tool access; this project
turns each task into a sealed, validated execution profile before the runtime
agent can act.

SCAS is a skill-centric, self-composing single-agent runtime. It analyzes a task,
discovers candidate capabilities, filters them through policy, validates the
dependency graph, and then executes through one immutable `Runtime Agent Profile`
instead of handing the agent every available skill, tool, data source, memory
scope, and instruction.

## Why It Matters

The differentiator is not "an agent with many tools." The differentiator is a
runtime that can only use the tools, skills, data, knowledge, memory, policies,
validators, and budgets sealed into the profile for that specific task.

That makes the system useful for environments where autonomy is valuable but
unbounded capability drift is unacceptable: code review, controlled repository
work, research synthesis, operational task execution, and future production
workflows that need auditable capability boundaries.

## Core Flow

```text
                task request
                     |
                     v
             +---------------+
             | Task Intake   |
             +-------+-------+
                     |
                     v
             +---------------+
             | Task Analyzer |
             +-------+-------+
                     |
                     v
             +----------------+
             | Agent Composer |
             +-------+--------+
                     |
      registry discovery + scoring + policy filtering
                     |
                     v
       +------------------------------------+
       | Sealed Runtime Agent Profile      |
       | skills, tools, scopes, budgets,   |
       | policies, validators, versions    |
       +----------------+-------------------+
                        |
                        v
              +----------------------+
              | Single Agent Runtime |
              +----+--------+--------+
                   |        |
                   v        v
          Context/Planner  Tool Gateway
                   |        |
                   v        v
             Executor -> Validator -> Runtime Output
```

Recomposition does not mutate the active profile. If a run needs different
capabilities, the current run stops with `needs_recomposition`, the Composer
creates a new immutable profile generation, and execution continues through a
new run attempt.

## Key Design Decisions

- **Single runtime agent, not a multi-agent swarm.** The architecture keeps one
  runtime loop and moves capability selection into explicit composition.
- **Profile sealing before execution.** The `Runtime Agent Profile` is the
  immutable execution contract. Unknown skills, handler version mismatches,
  unselected scopes, exhausted budgets, and failed validators fail closed.
- **Tool Gateway as the enforcement point.** Tool calls pass through profile
  allowlists, data-scope checks, risk gates, blocked argument checks, timeouts,
  output limits, approval requirements, and audit events.
- **Cloudflare Control Plane, Hetzner Runtime Plane.** Cloudflare owns control
  metadata, module discovery, ingestion metadata, retrieval, Vectorize indexes,
  and AI Gateway routing. Hetzner owns runtime execution, PostgreSQL run state,
  raw runtime artifacts, and execution traces.
- **Memory Feedback Pipeline.** Runtime output can produce memory candidates,
  but only validated, scoped, sensitivity-checked, provenance-bearing records
  are submitted back to the Control Plane.
- **Production claims require evidence.** The repository has a formal
  production-readiness gate instead of relying on aspirational status language.

The durable rationale is versioned in `docs/adr/`, especially:

- `docs/adr/0001-self-composing-single-agent-runtime.md`
- `docs/adr/0004-cloudflare-control-plane-hetzner-runtime-plane.md`
- `docs/adr/0006-formal-safety-guarantees-profile-sealing.md`

## Current Implementation

The repository is past pure design work. It currently includes:

- Python Task Analyzer and Runtime Profile Composer.
- Local deterministic registry implementation.
- JSON Schemas for module metadata, runtime profiles, runtime API payloads,
  runtime outputs, write approvals, control-plane records, runtime-plane
  records, environment manifests, telemetry, and production evidence.
- Cloudflare Control API Worker with composition context, ingestion, retrieval,
  queue-backed embedding updates, Vectorize bindings, bearer authentication,
  endpoint-scoped authorization, and fail-closed AI Gateway routing.
- Hetzner Runtime Plane contracts with PostgreSQL-backed runtime storage,
  artifact persistence, Flight Recorder events, checkpoints, stop reasons,
  token budgets, idempotency keys, and retention cleanup planning.
- Minimal runtime loop with context, planner, executor, validator, controlled
  recomposition, profile enforcement, and profile-scoped Tool Gateway execution.
- Controlled write adapter `filesystem-write` with profile-selected
  `repository-write` scope, approval policy, high-risk gating, rollback
  metadata, relative path enforcement, and dry-run-by-default behavior.
- Executable skill handlers for the first production-required runtime slice,
  with a committed coverage manifest and CI gate.
- Analyzer, scoring, controlled-learning, security-governance, runtime,
  Worker, and production-readiness tests.

## Production Status

This repository remains `not-production-ready` for a full `prod` launch.

Staging has passed certification for the first bounded productive runtime core
at commit `5bf301b8c0fdfe6d547c50890c72bbd6a0bf7648`. That means supervised
staging operations may start under
`docs/runbooks/first-productive-agent-operation.md`; it does not certify
production traffic or production data handling.

A `production-ready` claim still requires the release evidence gate in
`docs/policies/production-readiness.md` against `prod`, including target
environment certification, operational telemetry, security closure evidence,
and an owner-approved release decision.

Current production-readiness boundaries are tracked in:

- `docs/policies/production-readiness.md`
- `docs/roadmap/production-readiness-backlog.md`
- `docs/runbooks/first-productive-agent-operation.md`
- `docs/policies/environment-separation.md`
- `docs/policies/infrastructure-boundary.md`
- `docs/policies/threat-model.md`
- `docs/policies/review-gates.md`

## Project Guide

The README is the entry point, not the operations manual. The main project
surfaces are:

- `src/skill_centric_agent_system/`: Python composition, registries, runtime,
  profile enforcement, Tool Gateway, storage, recomposition, and skill handlers.
- `workers/control-api/`: Cloudflare Control API for composition, ingestion,
  retrieval, indexing, authentication, and AI Gateway routing.
- `registry/`: governed source of truth for selectable modules, environment
  allowlists, and reproducible registry lockfiles.
- `schemas/` and `examples/`: machine-readable contracts and representative
  tasks, profiles, API payloads, infrastructure records, generated seeds, and
  runtime fixtures. `examples/` is not the active module registry.
- `template/`: curated SCAS-native skill and instruction templates for future
  registry/module authoring. Templates are not active runtime modules until they
  are migrated into `registry/modules/**` with validated `module.json`
  metadata.
- `docs/reference/architecture.md`: system architecture and implemented runtime
  surfaces.
- `docs/policies/runtime-contract.md`: profile sealing, Tool Gateway rules,
  controlled writes, validators, skill handler coverage, and runtime contracts.
- `docs/reference/runtime-api.md`: runtime CLI/API, PostgreSQL mode,
  recomposition, result payloads, and retention commands.
- `docs/reference/runtime-run-queue-contract.md`: durable queue states,
  transitions, claims, retries, cancellation, quota, and profile-sealing rules.
- `docs/reference/runtime-parallel-execution-hardening-dod.md`: RPEH-2026
  closure criteria and required verification gates.
- `docs/reference/runtime-parallel-execution-hardening-audit-closure-dod.md`:
  strict audit-closure criteria for the RPEH-2026 follow-up findings.
- `docs/reference/cloudflare/control-api.md`: Cloudflare endpoints, D1 seed
  generation, Worker deployment, retrieval, ingestion, AI Gateway, and live
  smoke commands.
- `docs/runbooks/operations-runbook.md`: migrations, live gates, retention
  cleanup, diagnostics, disable paths, and GitHub Actions operations.
- `docs/runbooks/first-productive-agent-operation.md`: controlled staging
  operation rules after staging certification and before production launch.
- `docs/policies/environment-separation.md` and
  `docs/policies/infrastructure-boundary.md`: staging/prod separation and
  Cloudflare/Hetzner ownership boundaries.
- `docs/policies/production-readiness.md` and
  `docs/roadmap/production-readiness-backlog.md`: release evidence,
  certification, telemetry, security closure, and remaining production work.
- `docs/README.md`: full documentation index.
- `docs/runbooks/notion-issue-tracking.md`, `SECURITY.md`, and `AGENTS.md`:
  repository governance, security, and autonomous-agent work rules.

## License

This repository is licensed under the PolyForm Noncommercial License 1.0.0.
You may clone, use, copy, modify, and distribute the software for
noncommercial purposes under the terms in `LICENSE`.

Commercial use is not permitted under the noncommercial license. Commercial
use requires a separate written commercial license from the licensor.

## Try It Locally

Install development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run a fixture-backed Analyzer -> Composer -> Runtime path without external
services:

```powershell
scas-runtime-start `
  --task-file examples\tasks\code-review-task.json `
  --composition-context-file examples\control-api\composition-context-response.json `
  --artifact-root .scas-runtime `
  --repository-root . `
  --run-minimal-loop
```

Full validation, Worker checks, security/governance gates, live runtime gates,
retention cleanup, AI Gateway smoke tests, and production certification commands
live in:

- `docs/reference/runtime-api.md`
- `docs/reference/runtime-run-queue-contract.md`
- `docs/reference/runtime-parallel-execution-hardening-dod.md`
- `docs/reference/runtime-parallel-execution-hardening-audit-closure-dod.md`
- `docs/runbooks/runtime-live-dev-e2e.md`
- `docs/runbooks/operations-runbook.md`
- `docs/reference/cloudflare/control-api.md`
- `docs/policies/production-readiness.md`

## Build Rules

- Keep the runtime single-agent unless product direction changes explicitly.
- Do not grant every tool, data source, memory scope, or knowledge source by
  default.
- Use registries, scoring, policies, validators, and immutable profiles for
  runtime self-assembly.
- Version durable architecture decisions in `docs/adr/`.
- Track repository tasks in Notion through `$notion-repo-work-tracker`.
- Follow `AGENTS.md`, `SECURITY.md`, `docs/policies/data-governance.md`, and
  `docs/policies/review-gates.md` for autonomous repository changes.

## What This Demonstrates

SCAS demonstrates the hard part of agent engineering: not calling tools, but
controlling when tools may exist in the runtime at all.

The current split between `staging-ready` and `not-production-ready` for `prod`
is part of that demonstration. It shows that the project distinguishes a
working certified staging core from a production system with production
environment evidence, telemetry, security closure, rollback paths, and an
owner-approved release decision. That discipline is the point of the
architecture.
