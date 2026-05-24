# Data Governance

## Purpose

This document defines the repository rules for data classification, data
quality, model privacy, audit minimization, and knowledge or memory ingestion.
The rules are designed to guide autonomous agent work without blocking it unless
there is a concrete security, privacy, governance, or quality risk.

## Data Classification

| Classification | Meaning | Allowed Store |
| --- | --- | --- |
| `public` | Published or intentionally shareable information. | Cloudflare knowledge, Cloudflare memory, Hetzner runtime artifacts. |
| `internal` | Repository, operations, or project context that is not secret. | Cloudflare knowledge or memory when scoped and policy-approved. |
| `confidential` | Sensitive customer, operational, or private context. | Hetzner runtime artifacts by default; Cloudflare only with explicit policy approval. |
| `secret` | Credentials, bearer tokens, private keys, cookies, auth headers, provider keys, or equivalent values. | No persistent content store; only platform secret stores or environment variables. |

Secrets must not appear in prompts, runtime outputs, tool artifacts, Notion
task notes, examples, logs, CI artifacts, SBOMs, AI-BOMs, or production
readiness evidence.

## Model Privacy

Model inputs should include only the task objective, selected profile
instructions, scoped context, minimal source snippets, and required tool
results. They should not include unrelated runtime artifacts, full raw logs,
unselected knowledge or memory scopes, secrets, or data outside the active
profile.

Model outputs are not durable truth until they pass the selected validators and
the relevant policy gates. Durable memory promotion must go through memory
candidates with source run, source profile, sensitivity, retention policy,
validator status, policy status, and recorded reasons.

## Audit Minimization

Audit data must explain decisions and failures without collecting unnecessary
content. Prefer IDs, content URIs, status metadata, source URLs, checksums,
validation reasons, and policy decisions over full copied payloads.

Runtime artifacts may contain task-local execution data on Hetzner. Cloudflare
must not receive raw runtime traces, raw tool outputs, or run logs. The Control
Plane may receive validated knowledge records, policy-approved memory records,
scope metadata, ingestion jobs, and audit events.

## Knowledge And Data Quality

Every production knowledge or data source must define:

- source owner,
- source type,
- URI or durable source reference,
- sensitivity,
- allowed scopes,
- freshness or review expectation,
- confidence weight or quality tier,
- required metadata,
- validation rules,
- retention or archive expectation.

The generic machine-readable policy shape lives in
`schemas/knowledge-quality-policy.schema.json`. Example policy data lives in
`examples/governance/knowledge-quality-policy.json`.

Quality controls must fail closed for missing required metadata, invalid
sensitivity, unknown source type, missing owner, or attempts to ingest secret
content into Cloudflare. Lower-confidence sources may remain usable, but their
confidence must be visible to scoring, validation, or review.

## Agent Autonomy Boundary

Supportive guardrails:

- structured quality metadata,
- source confidence scoring,
- warning-level review triggers for stale or low-confidence sources,
- explicit validation reasons,
- non-secret evidence artifacts.

Mandatory blockers:

- secret content in prompts, logs, examples, CI artifacts, or Cloudflare
  ingestion,
- unscoped data or memory access,
- missing owner/sensitivity for production sources,
- unauthorized scope expansion,
- failed required validators,
- missing release evidence for production-ready claims.
