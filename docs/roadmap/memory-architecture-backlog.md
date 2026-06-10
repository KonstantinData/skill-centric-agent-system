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
  fail-closed checks complete; broader contrastive fixture coverage is covered
  by the Contrastive memory safety fixtures slice.)

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
  may need durable reuse. (Initial implementation complete:
  `KnowledgeRecordProposalBuilder` emits artifact-backed proposal records and
  `schemas/knowledge-record-proposal.schema.json` defines the contract.)
- Reuse the knowledge quality policy fields: owner, source URI, sensitivity,
  scope, freshness expectation, confidence tier, validation rules, and
  retention. (Initial implementation complete for proposal validation and
  optional `POST /knowledge/ingest` proposal metadata.)
- Add policy gates that fail closed when factual content lacks source quality
  metadata. (Initial implementation complete for owner, source URI,
  non-secret sensitivity, scope, Hetzner evidence, freshness, confidence,
  validation rules, and retention.)
- Add fixtures proving that reusable factual context uses `POST /knowledge/ingest`.
  (Initial fixture complete:
  `examples/control-api/knowledge-ingest-from-proposal-request.json`.)

### 5. Scope And Module Cleanup

- Rename or clarify memory scope descriptions so they refer to procedural
  Agent Memory instead of generic project memory. (Initial implementation
  complete for the `project-memory` module and Control Plane seed metadata.)
- Add selection negative phrases for task-subject fact storage requests.
  (Initial implementation complete for customer records, durable facts,
  factual knowledge, source extracts, raw traces, credentials, and
  task-subject facts.)
- Add or update policies that distinguish procedural memory access from
  knowledge access. (Initial implementation complete through module metadata
  and composer fail-closed checks; broader policy ledger work remains in the
  dedicated denial-ledger slice.)
- Ensure runtime profiles never select memory scopes as a substitute for
  knowledge scopes. (Initial implementation complete: research/retrieval
  composition fails closed when only memory scopes are returned.)

### 6. Retrieval And Runtime Integration

- Preserve the existing D1 prefilter, Vectorize lookup, and D1 post-validation
  path for both Knowledge and Memory.
- Add retrieval response metadata that identifies whether returned records are
  factual Knowledge Records or procedural Agent Memory. (Initial implementation
  complete: `POST /retrieval/context` emits `record_kind=knowledge_record` /
  `context_kind=factual_knowledge` for knowledge chunks and
  `record_kind=procedural_agent_memory` plus non-authoritative metadata for
  memory records.)
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
- Add planner lesson conflict and selection records. (Initial implementation
  complete: `PlannerMemorySelectionRecord` captures used/ignored memory IDs,
  non-authoritative effect, structured selection reason, empty
  `authority_delta`, plan change, validator-visible authority impact, and
  explicit conflict sets without chain-of-thought.)
- Add runtime tests for mixed retrieval where Knowledge provides facts and
  Memory provides process lessons. (Initial schema, Worker, and Runtime Context
  Manager tests cover metadata separation and fail-closed metadata validation.)

### 6a. Policy Denial Ledger And Scope Closure

- Add versioned policy denial records with deterministic denial fingerprints.
  (Initial implementation complete: `PolicyDenialLedger` deduplicates active
  denial records by fingerprint.)
- Add approved scope/policy closure metadata for scope-DAG subsumption checks.
  (Initial implementation complete: `ScopePolicyClosure` can subsume child
  data, knowledge, or memory scopes only under the same policy and closure
  version.)
- Keep denial records and closure entries metadata-only and non-authoritative.
  (Initial implementation complete: records are `deny_only`, closure entries
  are `reachability_only`, and validators reject authority-grant fields.)
- Document that lesson relationship graphs remain separate from scope closure.
  (Initial implementation complete in ADR-0010 and memory architecture docs.)

### 6b. Contrastive Memory Safety Fixtures

- Add executable positive and negative fixture cases for tool grants, scope
  grants, policy overrides, validator overrides, task-subject facts as memory,
  environment generalization, risk-level generalization, secret or sensitive
  content, and conflicting lessons. (Initial implementation complete:
  `examples/evaluations/contrastive-memory-safety-fixtures.json`.)
- Add metrics for false negatives, false positives, abstention/review rate, and
  required failure-class coverage. (Initial implementation complete:
  `evaluate_memory_safety_fixture`.)
- Keep the fixture wired to the existing memory candidate validator, semantic
  drift guard, and post-planning invariant validator rather than adding a second
  authority model. (Initial implementation complete.)

### 6c. Lesson Attribution And Ranking Feedback Gate

- Add Lesson Attribution Records for selected procedural lessons with outcome,
  context fingerprint, success/failure criteria, and error classification
  linkage. (Initial implementation complete:
  `schemas/lesson-attribution-record.schema.json` and
  `examples/evaluations/lesson-attribution-record.json`.)
- Gate ranking feedback so it is context-bound, non-authoritative, bounded by
  safe weight deltas, and limited to selected or ignored lesson IDs from the
  source selection record. (Initial implementation complete:
  `build_lesson_ranking_feedback_gate`.)
- Keep attribution feedback separate from authority changes. (Initial
  implementation complete: attribution records and feedback gates require
  `authority_delta=[]`.)

### 6d. Non-Authoritative Lesson Relationship Graph

- Add lesson edge records for `reinforces`, `contradicts`, `supersedes`,
  `refines`, and `duplicates`. (Initial implementation complete:
  `schemas/lesson-relationship-graph.schema.json` and
  `examples/evaluations/lesson-relationship-graph.json`.)
- Emit graph ranking hints for conflict display, supersession, dedupe, and
  related-lesson ranking without granting authority. (Initial implementation
  complete: `build_lesson_relationship_graph`.)
- Keep lesson relationships separate from scope closure and denial-ledger
  reachability metadata. (Initial implementation complete: graph and edges
  require `authority_delta=[]` and `non_authoritative=true`.)

### 7. Operations And Evidence

- Add a live dev smoke that creates one procedural lesson and one factual
  knowledge proposal from the same run evidence. (Initial aggregate evidence
  contract complete in `examples/operations/memory-operations-evidence.json`.)
- Add aggregate telemetry for candidate classifications and rejection reasons.
  (Initial implementation complete:
  `schemas/memory-operations-evidence.schema.json`.)
- Add retention checks that keep Runtime Evidence cleanup independent from
  Cloudflare Knowledge and Memory retention. (Initial implementation complete
  through the `retention_separation` evidence gate.)
- Update production readiness evidence to include the memory taxonomy gate.
  (Initial implementation complete: `Memory taxonomy operations evidence` gate
  added to production readiness evidence.)

### 7a. Operations Telemetry And Evidence Gates

- Add aggregate gates for contrastive false negatives/positives,
  abstention/review rate, post-planning invariant violations, Top-K memory
  load, retrieval cache hit rate, renderer behavior, denial-ledger outcomes,
  relationship graph authority deltas, and retention separation. (Initial
  implementation complete: `evaluate_memory_operations_evidence`.)
- Keep evidence secret-free and aggregate-only. (Initial implementation
  complete: `raw_data_policy=aggregate_metadata_only`.)

## Acceptance Criteria

- Agent Memory rejects task-subject facts across multiple task classes.
- Task-subject facts can be retained as Runtime Evidence or promoted through
  Knowledge ingestion when explicitly policy-approved.
- Procedural lessons can be promoted only with provenance, scope, sensitivity,
  retention, validation, policy approval, and non-authoritative influence class.
- Semantic retrieval never bypasses scope filtering or D1 post-validation.
- Documentation, schemas, fixtures, and tests describe the same taxonomy.
