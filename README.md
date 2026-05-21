# Skill-Centric Agent System

A repository for building a skill-centric, self-composing single-agent runtime.

The product direction is a single runtime agent that assembles a task-specific `Runtime Agent Profile` before execution. Skills, instructions, tools, knowledge, data scopes, memory scopes, policies, and validators are selected through controlled registries, scoring, policy filtering, and validation.

## Current Status

Contract-test and infrastructure-scaffold stage. The repository currently
defines durable architecture, contracts, schemas, ADRs, examples, a
Python-based contract-test harness, and the first Cloudflare Worker shell for
composition-time context.

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
- `docs/infrastructure-boundary.md`: Cloudflare Control Plane, Hetzner Runtime Plane, and memory feedback boundary.
- `docs/cloudflare/control-api.md`: Cloudflare Control API bootstrap, validation, and dev deployment runbook.
- `docs/adr/`: architecture decision records.
- `schemas/module.schema.json`: JSON Schema for selectable module metadata.
- `schemas/runtime-profile.schema.json`: JSON Schema for runtime agent profiles.
- `schemas/composition-context.schema.json`: JSON Schema for `POST /composition/context`.
- `schemas/cloudflare-control-plane.schema.json`: JSON Schema for Cloudflare control-plane storage records.
- `schemas/hetzner-runtime-plane.schema.json`: JSON Schema for Hetzner runtime-plane storage records.
- `migrations/cloudflare/d1/`: Cloudflare D1 SQL migrations for control-plane metadata.
- `migrations/hetzner/postgres/`: PostgreSQL migrations for Hetzner runtime-plane storage.
- `workers/control-api/`: Cloudflare Worker scaffold for the Control API.
- `scripts/cloudflare/`: Cloudflare bootstrap scripts.
- `scripts/hetzner/`: Hetzner bootstrap and maintenance scripts.
- `examples/modules/`: representative selectable module metadata.
- `examples/tasks/`: representative task inputs.
- `examples/profiles/`: representative composed profiles.
- `examples/control-plane/`: representative Cloudflare control-plane storage records.
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
with `deploy_control_api_dev = true` only after the D1 and KV placeholder IDs in
`workers/control-api/wrangler.toml` are replaced with real Cloudflare resource
IDs.

## Build Rules

- Keep the runtime single-agent unless the product direction changes explicitly.
- Do not grant every tool, data source, memory scope, or knowledge source by default.
- Use registries, scoring, policies, and validators for self-assembly.
- Version durable decisions in `docs/adr/`.
- Track repository tasks in Notion through `$notion-repo-work-tracker`.

## Next Steps

1. Replace Cloudflare dev placeholder IDs after running the Control API bootstrap.
2. Implement registry discovery, scoring, filtering, resolution, and graph validation.
3. Implement `POST /composition/context` D1/KV-backed registry queries.
4. Implement task analysis and profile composition against the sample task/profile pair.
