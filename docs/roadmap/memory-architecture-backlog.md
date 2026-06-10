# Memory Architecture Backlog

## Purpose

This backlog converts the target architecture in
`docs/reference/memory-architecture.md` into executable repository work.

## Delivery Order

### 1. Contract And Policy Foundation

- Define a machine-readable candidate classification schema with
  `procedural_lesson`, `task_subject_fact`, `runtime_evidence`,
  `knowledge_record_proposal`, and `rejected`.
- Extend the Hetzner Runtime Plane memory candidate contract with candidate
  classification metadata and non-authoritative influence class.
- Update Data Governance and Runtime Contract tests so Agent Memory cannot
  accept task-subject facts.
- Add examples for task-neutral subjects: company research, repository
  diagnosis, document synthesis, and customer-case analysis.

### 2. Post-Run Reflection

- Add a deterministic post-run reflection interface that reads completed
  runtime steps and artifact URIs. (Initial implementation:
  `PostRunReflectionExtractor` emits artifact-backed envelopes.)
- Make reflection emit classified candidate envelopes instead of direct memory
  candidates. (Initial implementation complete for in-process runtime
  reflection; validator and ingestion routing remain later slices.)
- Require evidence URIs, source run/profile/step IDs, sensitivity, retention,
  target scope, and policy ID on every candidate envelope. (Initial schema and
  tests complete.)
- Add negative fixtures for raw tool output, source extracts, customer-specific
  content, and secret-like values. (Initial raw-tool-output and secret-like
  fail-closed checks complete; broader contrastive fixture coverage remains in
  the dedicated evaluation slice.)

### 3. Procedural Memory Validation

- Extend `MemoryCandidateValidator` with a content classifier gate that rejects
  task-subject facts for Agent Memory. (Initial implementation complete for
  deterministic raw/source/customer/private/secret/task-subject and
  authority-language gates.)
- Require procedural candidates to contain a reusable lesson and applicability
  metadata, not only a free-form summary. (Initial implementation complete:
  validators require `applicability`, Hetzner `evidence_uris`,
  `authoritative=false`, non-authoritative `allowed_effects`, and full
  `forbidden_effects` coverage.)
- Keep semantic drift guard checks for authority-changing learned context.
  (Preserved and covered by existing tests with procedural metadata.)
- Add tests proving that procedural lessons can be promoted while factual task
  content is routed to Knowledge or retained as Runtime Evidence. (Validator
  rejection tests are complete; explicit Knowledge routing remains the
  Knowledge Proposal Path slice.)

### 4. Knowledge Proposal Path

- Add a `KnowledgeRecordProposal` path for factual task-subject content that
  may need durable reuse.
- Reuse the knowledge quality policy fields: owner, source URI, sensitivity,
  scope, freshness expectation, confidence tier, validation rules, and
  retention.
- Add policy gates that fail closed when factual content lacks source quality
  metadata.
- Add fixtures proving that reusable factual context uses `POST /knowledge/ingest`.

### 5. Scope And Module Cleanup

- Rename or clarify memory scope descriptions so they refer to procedural
  Agent Memory instead of generic project memory.
- Add selection negative phrases for task-subject fact storage requests.
- Add or update policies that distinguish procedural memory access from
  knowledge access.
- Ensure runtime profiles never select memory scopes as a substitute for
  knowledge scopes.

### 6. Retrieval And Runtime Integration

- Preserve the existing D1 prefilter, Vectorize lookup, and D1 post-validation
  path for both Knowledge and Memory.
- Add retrieval response metadata that identifies whether returned records are
  factual Knowledge Records or procedural Agent Memory.
- Ensure the Runtime Context Manager treats retrieved memory as planning or
  ranking context only. (Initial renderer implementation complete:
  `MemoryRenderer` injects `instruction_status=not_an_instruction`,
  `authoritative=false`, non-authoritative allowed effects, forbidden authority
  effects, and `render_profile=procedural_memory_context_v1` into runtime
  context.)
- Add a post-planning invariant validator for memory-influenced plans. (Initial
  implementation complete: `PostPlanningMemoryInvariantValidator` rejects
  memory-derived authority deltas, tool/scope/policy/validator/budget/failure
  policy changes, runtime profile authority mutations, and memory IDs used as
  authority justification.)
- Add runtime tests for mixed retrieval where Knowledge provides facts and
  Memory provides process lessons.

### 7. Operations And Evidence

- Add a live dev smoke that creates one procedural lesson and one factual
  knowledge proposal from the same run evidence.
- Add aggregate telemetry for candidate classifications and rejection reasons.
- Add retention checks that keep Runtime Evidence cleanup independent from
  Cloudflare Knowledge and Memory retention.
- Update production readiness evidence to include the memory taxonomy gate.

## Acceptance Criteria

- Agent Memory rejects task-subject facts across multiple task classes.
- Task-subject facts can be retained as Runtime Evidence or promoted through
  Knowledge ingestion when explicitly policy-approved.
- Procedural lessons can be promoted only with provenance, scope, sensitivity,
  retention, validation, policy approval, and non-authoritative influence class.
- Semantic retrieval never bypasses scope filtering or D1 post-validation.
- Documentation, schemas, fixtures, and tests describe the same taxonomy.
