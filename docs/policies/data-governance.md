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
| `confidential` | Sensitive customer, operational, or private context. | Hetzner tenant PostgreSQL databases or Hetzner runtime artifacts by default; Cloudflare only with explicit policy approval. |
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
candidate class, classification reason, validator status, policy status, and
recorded reasons. The memory candidate classification envelope is a closed
schema; unknown fields, raw traces, raw tool outputs, and customer-specific
extension payloads must fail before Cloudflare memory or knowledge ingestion.

## Audit Minimization

Audit data must explain decisions and failures without collecting unnecessary
content. Prefer IDs, content URIs, status metadata, source URLs, checksums,
validation reasons, and policy decisions over full copied payloads.

Runtime artifacts may contain task-local execution data on Hetzner. Cloudflare
must not receive raw runtime traces, raw tool outputs, or run logs. The Control
Plane may receive validated knowledge records, policy-approved memory records,
scope metadata, ingestion jobs, and audit events.

Tenant customer and operational business data must remain in tenant-local
PostgreSQL databases on Hetzner unless a separate policy explicitly approves a
bounded metadata projection. Cloudflare D1 is not an operational customer data
store; it may hold tenant authority and data-source registration metadata, but
not Daskuechenhaus customer cases, customer records, order state, email
communication bodies, calendar contents, invoice-relevant state, or aftersales
case content.

## Tenant Context Separation

Tenant-local code, fixtures, scripts, migrations, workflow inputs, runtime
profiles, knowledge scopes, and memory scopes must not be reused across tenants
as product context.

For Liquisto tenant work, `apps/dkh-crm/`,
`migrations/hetzner/tenants/daskuechenhaus/`, Daskuechenhaus workflows,
Daskuechenhaus scripts, and Daskuechenhaus customer or CRM data are foreign
tenant context. They must be ignored as implementation sources unless the task
is explicitly an isolation audit, release gate, rollback check, or deployment
guard proving that the foreign tenant is rejected or absent.

Any runtime profile, role bundle, data-source grant, UI route, import path, or
knowledge/memory retrieval result that mixes Liquisto with Daskuechenhaus scope
must fail closed.

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
Runtime-created factual proposals use
`schemas/knowledge-record-proposal.schema.json` and must carry source
provenance, owner, source URI, scope, freshness, confidence, validation rules,
retention, and Hetzner Runtime evidence before `POST /knowledge/ingest` may
accept them as durable Knowledge input.

Quality controls must fail closed for missing required metadata, invalid
sensitivity, unknown source type, missing owner, or attempts to ingest secret
content into Cloudflare. Lower-confidence sources may remain usable, but their
confidence must be visible to scoring, validation, or review.

## Task-Subject Data And Agent Memory

Task-subject data is factual content about the concrete subject of a task. It
includes facts about companies, people, products, repositories, documents,
markets, customer cases, legal topics, operational incidents, or any other
task-specific target.

Task-subject data must not be stored as Agent Memory. It remains Runtime Plane
evidence during the run unless a separate, policy-approved Knowledge Record
promotion is required for durable factual reuse.

Memory candidates classified as `task_subject_fact`, `runtime_evidence`,
`knowledge_record_proposal`, or `rejected` are not eligible for Agent Memory
promotion. Only `procedural_lesson` candidates may enter the Cloudflare memory
ingestion path.

Agent Memory is limited to procedural lessons: reusable process knowledge about
how to perform tasks, what sequence worked, which approach failed, which source
or tool pattern should be preferred or avoided, and which non-authoritative
planning hints are supported by evidence.

Semantic retrieval is an access mechanism for scoped Knowledge Records and
procedural Agent Memory. It is not permission to merge task-subject facts into
Agent Memory.

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
- task-subject facts promoted into Agent Memory,
- unauthorized scope expansion,
- failed required validators,
- missing release evidence for production-ready claims.
