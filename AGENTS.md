# Agent Governance

This repository builds a skill-centric, self-composing single-agent system. It
must remain a single runtime agent unless the product direction changes
explicitly in a committed architecture decision.

## Required Workflow

- Start repository work with Notion tracking in the SCAS Issues & Open
  Questions database.
- Keep durable architecture, security, data-governance, and release criteria in
  repository files, not only in chat or Notion.
- Before commits or handoff, check whether README, docs, ADRs, schemas,
  examples, runbooks, or roadmap files must be updated.
- Prefer small, testable changes over broad rewrites.

## Composition Rules

The agent may assemble a task-specific runtime profile only through:

1. task analysis,
2. registry discovery,
3. scoring,
4. policy filtering,
5. dependency graph validation,
6. immutable runtime profile validation.

The runtime must not self-grant tools, data scopes, memory scopes, knowledge
scopes, skills, instructions, policies, or validators. Recomposition must create
a new profile through the same control path.

## Security Rules

- Do not commit secrets or `.env` files.
- Do not place live tokens, private keys, provider credentials, raw runtime
  traces, raw tool outputs, or confidential customer data in examples, logs,
  prompts, Notion notes, or release evidence.
- Keep Cloudflare as the Control Plane and Hetzner as the Runtime Plane.
  Runtime artifacts and raw execution traces stay on Hetzner.
- Cloudflare may receive only control metadata, knowledge records, and memory
  records that pass validation and policy gates.
- Unknown or unauthorized tools, scopes, validators, or policies fail closed.

## Review Rules

High-impact paths require code-owner review and passing governance gates:

- `.github/`
- `policies/`
- `schemas/`
- `migrations/`
- `workers/control-api/`
- `src/skill_centric_agent_system/runtime/`
- `src/skill_centric_agent_system/composition/`
- `docs/adr/`
- `docs/*governance*.md`
- `docs/review-gates.md`
- `docs/production-readiness.md`

Review gates should secure and guide autonomous agent work. They should not
block low-risk documentation or fixture changes unless those changes affect
security, data governance, contracts, workflows, or production evidence.

## Test Expectations

Run focused tests for the changed surface. For governance or security changes,
run:

```powershell
python -m pytest tests/test_security_governance.py
python -m ruff check .
```

For broader repository changes, run the full local gate:

```powershell
python -m pytest
python -m ruff check .
npm run worker:typecheck
npm run worker:test
npm run worker:check
```
