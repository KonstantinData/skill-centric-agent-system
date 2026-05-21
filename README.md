# Skill-Centric Agent System

A repository for building a skill-centric, self-composing single-agent runtime.

The product direction is a single runtime agent that assembles a task-specific `Runtime Agent Profile` before execution. Skills, instructions, tools, knowledge, data scopes, memory scopes, policies, and validators are selected through controlled registries, scoring, policy filtering, and validation.

## Current Status

Contract-test stage. The repository currently defines durable architecture, contracts, schemas, ADRs, examples, and a Python-based contract-test harness before runtime code is added.

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
- `docs/adr/`: architecture decision records.
- `schemas/module.schema.json`: JSON Schema for selectable module metadata.
- `schemas/runtime-profile.schema.json`: JSON Schema for runtime agent profiles.
- `schemas/cloudflare-control-plane.schema.json`: JSON Schema for Cloudflare control-plane storage records.
- `schemas/hetzner-runtime-plane.schema.json`: JSON Schema for Hetzner runtime-plane storage records.
- `examples/modules/`: representative selectable module metadata.
- `examples/tasks/`: representative task inputs.
- `examples/profiles/`: representative composed profiles.
- `examples/control-plane/`: representative Cloudflare control-plane storage records.
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

## Build Rules

- Keep the runtime single-agent unless the product direction changes explicitly.
- Do not grant every tool, data source, memory scope, or knowledge source by default.
- Use registries, scoring, policies, and validators for self-assembly.
- Version durable decisions in `docs/adr/`.
- Track repository tasks in Notion through `$notion-repo-work-tracker`.

## Next Steps

1. Add CI for the contract-test command.
2. Implement registry discovery, scoring, filtering, resolution, and graph validation.
3. Implement task analysis and profile composition against the sample task/profile pair.
