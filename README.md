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
checkpoints, stop reasons, token budgets, and idempotency keys. The first
runtime entry point can now start a run from task intake, compose the runtime
profile, emit Flight Recorder events, and write artifact-backed trace payloads.

The current dev Control Plane can answer `POST /composition/context` with real
D1-backed module candidates such as `git-diff-analysis`. The Python composer can
consume that Control Plane response and emit a version-pinned runtime profile.
The runtime loop, tool execution, knowledge ingestion, memory ingestion,
Vectorize, and production AI Gateway routing remain follow-up implementation
work.

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
- `docs/registries.md`: registry implementation semantics for discovery, scoring, filtering, resolution, and graph validation.
- `docs/cloudflare/control-api.md`: Cloudflare Control API bootstrap, validation, and dev deployment runbook.
- `docs/adr/`: architecture decision records.
- `schemas/module.schema.json`: JSON Schema for selectable module metadata.
- `schemas/runtime-profile.schema.json`: JSON Schema for runtime agent profiles.
- `schemas/composition-context.schema.json`: JSON Schema for `POST /composition/context`.
- `schemas/cloudflare-control-plane.schema.json`: JSON Schema for Cloudflare control-plane storage records.
- `schemas/hetzner-runtime-plane.schema.json`: JSON Schema for Hetzner runtime-plane storage records.
- `migrations/cloudflare/d1/`: Cloudflare D1 SQL migrations for control-plane metadata.
- `migrations/hetzner/postgres/`: PostgreSQL migrations for Hetzner runtime-plane storage.
- `src/skill_centric_agent_system/composition/`: Task Analyzer, Control Plane client, and Runtime Profile Composer.
- `src/skill_centric_agent_system/runtime/`: Runtime Entry Point, Flight Recorder writer, runtime storage ports, and JSON artifact store.
- `src/skill_centric_agent_system/registries/`: local deterministic registry implementation.
- `src/skill_centric_agent_system/control_plane/`: control-plane seed generation utilities.
- `workers/control-api/`: Cloudflare Control API Worker with `POST /composition/context`.
- `scripts/cloudflare/`: Cloudflare bootstrap and D1 seed scripts.
- `scripts/hetzner/`: Hetzner bootstrap and maintenance scripts.
- `examples/modules/`: representative selectable module metadata.
- `examples/tasks/`: representative task inputs.
- `examples/profiles/`: representative composed profiles.
- `examples/control-plane/`: representative Cloudflare control-plane storage records and generated dev D1 seed SQL.
- `examples/control-api/`: representative Control API request and response payloads.
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
  --artifact-root .scas-runtime
```

The command starts the Analyzer -> Composer -> Runtime Entry Point path without
external services. It writes Flight Recorder event/checkpoint payloads under the
artifact root and prints the run/profile summary.

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

`HETZNER_SSH_KEY` must contain the complete private OpenSSH key block, including
the `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`
lines. Do not use the public `ssh-ed25519 ...` line or the `SHA256:...`
fingerprint as this secret.

Cloudflare Control API dev deployment is manual in the same workflow. Run it
with `deploy_control_api_dev = true` or locally with `npm run worker:deploy:dev`
when Wrangler is authenticated.

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

1. Implement the profile-scoped Tool Gateway.
2. Implement the Single Agent Runtime loop on Hetzner against composed profiles and the Flight Recorder event writer.
3. Add knowledge and memory ingestion flows on top of the Cloudflare control-plane records.
