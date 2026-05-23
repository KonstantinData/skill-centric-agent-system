# Skill-Centric Agent System

A repository for building a skill-centric, self-composing single-agent runtime.

The product direction is a single runtime agent that assembles a task-specific `Runtime Agent Profile` before execution. Skills, instructions, tools, knowledge, data scopes, memory scopes, policies, and validators are selected through controlled registries, scoring, policy filtering, and validation.

## Current Status

Initial composition implementation stage. The repository currently defines
durable architecture, contracts, schemas, ADRs, examples, a Python-based
contract-test harness, a local registry implementation, a deployed Cloudflare
Control API Worker, D1 migrations, generated dev registry seed data, and the
first Task Analyzer/Profile Composer implementation. The Hetzner Runtime Plane
also has an initial Flight Recorder storage contract for runtime events,
checkpoints, stop reasons, token budgets, idempotency keys, and atomic
run-local event indexing. The first runtime entry point can now start a run
from task intake, compose the runtime profile, emit Flight Recorder events,
write artifact-backed trace payloads, and run the first minimal
context/planner/executor/validator loop through a
profile-scoped Tool Gateway. The runtime CLI can now use either in-memory
storage for local fixtures or PostgreSQL storage for the Hetzner Runtime Plane
through `SCAS_RUNTIME_DATABASE_URL`. Runtime profile enforcement now fail-closes
unselected tools/scopes and exhausted tool, token, duration, data-read,
memory-op, and recomposition budgets. The Tool Gateway now applies per-tool
allowlists, risk gating, blocked argument checks, timeouts, output limits, and
access audit events. The Runtime Context Manager now calls the Control API
retrieval endpoint for profile-bounded knowledge/memory context and rejects
scope-expanded responses. The Validator phase now runs the validator IDs
selected by the active profile and fail-closes unknown or failed validators.
Controlled recomposition requests now emit `recomposition_requested` and stop
the current run with `needs_recomposition` instead of mutating the active
profile. A manual live dev E2E gate now exists for the Cloudflare-to-Hetzner
runtime path, and the operations runbook defines migrations, smoke tests,
diagnostics, and disable paths. Runtime artifact writes now honor the profile's
`observability.redact_sensitive_data` flag and expose a retention planner for
runtime artifact cleanup jobs. The Cloudflare Control API also exposes initial
knowledge and validated-memory ingestion endpoints that write R2 objects, D1
metadata, ingestion jobs, and audit events. It now also exposes a
D1-gated `POST /retrieval/context` endpoint with Vectorize bindings and
post-validation, plus a fail-closed AI Gateway route for OpenAI chat
completions. Every non-health Control API route now requires bearer
authentication and supports endpoint-scoped authorization tokens. Hetzner can
now extract memory candidates from completed runtime steps, validate their
scope/sensitivity/provenance/policy status, and submit only approved candidates
through the Memory Feedback Pipeline client. Analyzer and composition-scoring
evaluation fixtures now cover code-review, research, task-execution, general
tasks, and positive/negative scoring evidence. Runtime artifact persistence now
chunks large string payloads into manifest-referenced text chunks.

The current dev Control Plane can answer `POST /composition/context` with real
D1-backed module candidates such as `git-diff-analysis`. The Python composer can
consume that Control Plane response and emit a version-pinned runtime profile.
Live recomposition continuation, richer tool execution, async indexing workers,
remote live Hetzner E2E evidence, live Postgres concurrency evidence, and
production-scale deployment hardening remain follow-up implementation work.

## Core Flow

```text
UI/API -> Task Intake -> Task Analyzer -> Agent Composer
Agent Composer -> Runtime Agent Profile
Runtime Agent Profile -> Single Agent Runtime
Single Agent Runtime -> Context Manager / Planner / Executor / Validator
Executor -> Selected Skills / Allowed Tools / Scoped Data / Retrieved Knowledge
```

## Repository Map

- `docs/architecture.md`: system architecture and component responsibilities.
- `docs/contracts.md`: durable contracts for modules and runtime profiles.
- `docs/module-contracts.md`: detailed field semantics for selectable module metadata.
- `docs/infrastructure-boundary.md`: Cloudflare Control Plane, Hetzner Runtime Plane, and memory feedback boundary.
- `docs/runtime-preflight.md`: productive Runtime Phase entry gate, naming rules, validation scenarios, risk boundaries, and Phase 1 implementation order.
- `docs/runtime-contract.md`: generic runtime lifecycle, failure, observability, result, and recomposition contract.
- `docs/runtime-api.md`: runtime start/status/result/cancel/retry API and CLI contract.
- `docs/runtime-live-dev-e2e.md`: manual live dev E2E gate for Cloudflare and Hetzner.
- `docs/operations-runbook.md`: operations baseline for migrations, smoke tests, diagnostics, and disable paths.
- `docs/registries.md`: registry implementation semantics for discovery, scoring, filtering, resolution, and graph validation.
- `docs/cloudflare/control-api.md`: Cloudflare Control API bootstrap, validation, and dev deployment runbook.
- `docs/adr/`: architecture decision records.
- `schemas/module.schema.json`: JSON Schema for selectable module metadata.
- `schemas/runtime-profile.schema.json`: JSON Schema for runtime agent profiles.
- `schemas/runtime-api.schema.json`: JSON Schema for runtime API request and response examples.
- `schemas/composition-context.schema.json`: JSON Schema for `POST /composition/context`.
- `schemas/retrieval-context.schema.json`: JSON Schema for `POST /retrieval/context`.
- `schemas/cloudflare-control-plane.schema.json`: JSON Schema for Cloudflare control-plane storage records.
- `schemas/hetzner-runtime-plane.schema.json`: JSON Schema for Hetzner runtime-plane storage records.
- `migrations/cloudflare/d1/`: Cloudflare D1 SQL migrations for control-plane metadata.
- `migrations/hetzner/postgres/`: PostgreSQL migrations for Hetzner runtime-plane storage.
- `src/skill_centric_agent_system/composition/`: Task Analyzer, Control Plane client, and Runtime Profile Composer.
- `src/skill_centric_agent_system/runtime/`: Runtime Entry Point, Context Manager, Flight Recorder writer, profile enforcement, runtime storage ports, PostgreSQL storage session, and JSON artifact store.
- `src/skill_centric_agent_system/registries/`: local deterministic registry implementation.
- `src/skill_centric_agent_system/control_plane/`: control-plane seed generation utilities.
- `workers/control-api/`: Cloudflare Control API Worker with composition, ingestion, retrieval, and AI Gateway routes.
- `scripts/cloudflare/`: Cloudflare bootstrap and D1 seed scripts.
- `scripts/hetzner/`: Hetzner bootstrap and maintenance scripts.
- `scripts/runtime/`: live runtime gate scripts.
- `examples/modules/`: representative selectable module metadata.
- `examples/tasks/`: representative task inputs.
- `examples/profiles/`: representative composed profiles.
- `examples/control-plane/`: representative Cloudflare control-plane storage records and generated dev D1 seed SQL.
- `examples/control-api/`: representative Control API request and response payloads.
- `examples/runtime-api/`: representative Runtime API request and response payloads.
- `examples/evaluations/`: analyzer, scoring, and controlled-learning evaluation fixtures.
- `examples/runtime-plane/`: representative Hetzner runtime-plane storage records.
- `tests/`: executable contract tests for schemas, examples, and cross-field invariants.

## Local Validation

Install development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run contract tests:

```powershell
python -m pytest
```

Run linting:

```powershell
python -m ruff check .
```

Start a local fixture-backed runtime run:

```powershell
scas-runtime-start `
  --task-file examples\tasks\code-review-task.json `
  --composition-context-file examples\control-api\composition-context-response.json `
  --artifact-root .scas-runtime `
  --repository-root . `
  --run-minimal-loop
```

The command starts the Analyzer -> Composer -> Runtime Entry Point path without
external services. With `--run-minimal-loop`, it also runs the first
Context/Planner/Executor/Validator loop, invokes only profile-allowed read
tools, writes tool input/output artifacts under the artifact root, and prints
the run/profile summary.

Start the same path against Hetzner PostgreSQL storage when the database URL is
available in the environment:

```powershell
scas-runtime-start `
  --task-file examples\tasks\code-review-task.json `
  --control-plane-url $env:SCAS_CONTROL_API_URL `
  --control-plane-token $env:SCAS_CONTROL_API_TOKEN `
  --artifact-root /opt/scas/runtime `
  --repository-root . `
  --storage-mode postgres `
  --database-url $env:SCAS_RUNTIME_DATABASE_URL `
  --run-minimal-loop
```

Generate the Cloudflare D1 dev seed from module contracts:

```powershell
python scripts\cloudflare\generate_control_plane_seed.py --output examples\control-plane\dev-seed.sql
```

Install Worker dependencies:

```powershell
npm install
```

Run Worker checks:

```powershell
npm run worker:types
npm run worker:typecheck
npm run worker:test
npm run worker:check
```

## GitHub Actions

`.github/workflows/ci.yml` runs contract tests, linting, JSON syntax checks,
Worker type checks, and Worker Vitest tests on pushes to `main` and pull
requests.

The same workflow also has a manual `workflow_dispatch` infrastructure smoke
test. Run it with `run_infra_smoke = true` after the required GitHub Actions
secrets are configured:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ZONE_ID`
- `HETZNER_HOST`
- `HETZNER_SSH_KEY`
- `HETZNER_USER`
- `OPENAI_API_KEY`
- `CONTROL_API_TOKEN`

`CONTROL_API_TOKEN` is used by the manual dev Worker deployment job to
configure the Worker secret. Endpoint-scoped Worker secrets can be configured
manually with Wrangler when the single automation token is too broad.

`HETZNER_SSH_KEY` must contain the complete private OpenSSH key block, including
the `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`
lines. Do not use the public `ssh-ed25519 ...` line or the `SHA256:...`
fingerprint as this secret.

Cloudflare Control API dev deployment is manual in the same workflow. Run it
with `deploy_control_api_dev = true` or locally with `npm run worker:deploy:dev`
when Wrangler is authenticated.

Live runtime gates are manual in `.github/workflows/live-runtime-gates.yml`.
Run the live dev E2E gate with:

```powershell
gh workflow run live-runtime-gates.yml -f run_live_dev_e2e=true
```

The workflow uses GitHub Actions secrets, uploads the checked-out commit to the
Hetzner host, runs `scripts/runtime/live_dev_e2e.py` there, and writes runtime
artifacts below `/opt/scas/runtime/live-dev-gates/<github-run-id>`.

The current dev Worker is:

```text
https://scas-control-api-dev.still-butterfly-bbff.workers.dev
```

## Build Rules

- Keep the runtime single-agent unless the product direction changes explicitly.
- Do not grant every tool, data source, memory scope, or knowledge source by default.
- Use registries, scoring, policies, and validators for self-assembly.
- Version durable decisions in `docs/adr/`.
- Track repository tasks in Notion through `$notion-repo-work-tracker`.

## Next Steps

1. Execute the live dev E2E gate against remote Hetzner with Control API auth configured.
2. Capture live Postgres concurrency evidence after the atomic event-index change.
3. Continue async indexing, AI Gateway live secret rollout, runtime expansion, and retention cleanup as explicit backlog items.
