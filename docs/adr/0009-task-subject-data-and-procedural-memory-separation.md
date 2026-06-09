# ADR-0009: Task-Subject Data And Procedural Memory Separation

## Status

Accepted

## Date

2026-06-09

## Context

SCAS already separates Cloudflare Control Plane data from Hetzner Runtime Plane
artifacts. It also supports scoped Knowledge Records, scoped Memory Records,
semantic Vectorize lookup, memory candidates, and learned-context authority
guards.

That foundation is necessary but not sufficient. A memory candidate can still
be valid by provenance, sensitivity, policy, and scope while containing facts
about the concrete subject of a task. Company research is one example, but the
same risk exists for people, products, repositories, documents, markets,
customer cases, legal topics, operational incidents, or any future task subject.

The system needs a task-neutral boundary between:

- evidence from a specific run,
- factual subject-matter knowledge,
- reusable procedural lessons for the agent.

## Decision

SCAS adopts the following invariant:

```text
Agent Memory stores reusable process lessons, not task-subject facts.
```

Run evidence remains on the Hetzner Runtime Plane. Task-subject facts may become
durable only through scoped Knowledge Records with source owner, source URI,
sensitivity, quality metadata, retention, and policy approval. Agent Memory may
store only procedural lessons after candidate classification, validation,
policy approval, and learned-authority safety compilation.

Semantic retrieval is an access mechanism, not a memory class. It may rank
Knowledge Records and Procedural Agent Memory only after profile, principal,
scope, and D1 post-validation gates.

## Consequences

- Memory candidate validation must reject task-subject facts for Agent Memory.
- Post-run reflection must classify extracted material before promotion.
- Factual reusable context must use Knowledge ingestion, not Memory ingestion.
- Existing memory scopes should be renamed or described as procedural unless a
  future reviewed decision introduces another memory class.
- Runtime evidence can support reports and later reflection without becoming
  durable Agent Memory.
- Learned procedural memory remains non-authoritative and cannot grant
  capabilities without reviewed policy artifacts.

## Target Artifacts

- `docs/reference/memory-architecture.md`
- `docs/roadmap/memory-architecture-backlog.md`
- `docs/policies/runtime-contract.md`
- `docs/policies/data-governance.md`

## Implementation Requirements

- Add a candidate classification contract for procedural lessons,
  task-subject facts, runtime evidence, knowledge proposals, and rejected
  material.
- Extend memory candidate validation to reject task-subject facts and secret or
  customer-specific content in Agent Memory.
- Add fixtures proving that company research and other task-subject facts stay
  on the Runtime Plane or Knowledge path.
- Add a post-run reflection stage that emits classified candidates with
  evidence URIs.
- Update memory scope modules and retrieval tests so memory records are treated
  as procedural, non-authoritative context.
- Add documentation and CI gates that keep the storage taxonomy from drifting.
