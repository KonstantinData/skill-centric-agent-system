# Repository Roadmap

## Current Position

The repository has completed the foundation, contract hardening, contract-test
setup, local registry foundation, Cloudflare/Hetzner infrastructure contracts,
Control API Worker scaffold, D1-backed `POST /composition/context`, dev D1
registry seed path, and the first Analyzer/Composer implementation.
The Hetzner Runtime Plane also has the initial Flight Recorder storage contract
for runtime events, checkpoints, stop reasons, token budgets, and idempotency.
The Runtime Entry Point can start a run from task intake, compose the runtime
profile, create the runtime run, and emit initial artifact-backed Flight
Recorder events. The profile-scoped Tool Gateway and first minimal runtime loop
can execute read-only code-review fixture work. Runtime artifact redaction and
retention planning are implemented for the Flight Recorder artifact path. The
Control API also has knowledge/memory ingestion, a D1-gated
`POST /retrieval/context` endpoint with Vectorize bindings and post-validation,
and a fail-closed AI Gateway route for OpenAI chat completions. The Runtime
Plane can extract and validate memory candidates from completed runtime steps
before submitting approved candidates to Cloudflare durable memory.

The next main implementation block is the Runtime Preflight Gate in
`docs/runtime-preflight.md`, followed by the productive runtime core. Async
indexing, AI Gateway live secret rollout, broader runtime expansion, and
retention cleanup remain explicit backlog items and must not obscure the
runtime entry gate.

## Phase 0: Runtime Preflight Gate

- Synchronize the Notion Feature Backlog, this roadmap, `docs/architecture.md`,
  and `docs/infrastructure-boundary.md`.
- Finalize naming rules for `task_type`, `capability_class`, module IDs, scope
  IDs, tool IDs, and scoring signal values.
- Define what productive Runtime Phase means for this repository.
- Verify current dev infrastructure state across Cloudflare, Hetzner, secrets,
  and CI.
- Define entry criteria for productive runtime work.
- Define generic validation scenarios without turning them into separate agent
  roles.
- Define first-slice risk boundaries for tools, approvals, writes, destructive
  actions, secrets, and runtime artifacts.
- Seed the first project memory scope and make memory ingestion fail closed when
  a request references an unknown memory scope.

Status: active. The durable gate is documented in `docs/runtime-preflight.md`.

## Phase 1: Foundation

- Define architecture and contracts.
- Add JSON schemas for module metadata and runtime profiles.
- Add representative task and profile examples.
- Record initial architecture decisions.

Status: complete.

## Phase 2: Contract Hardening

- Specify Task Analyzer output and failure behavior.
- Define registry query semantics: discover, score, filter, resolve, graph validation.
- Add structured scoring metadata to module contracts.
- Add runtime profile version pinning and recomposition traceability.
- Expand execution limits beyond tool calls.
- Define auth/authz, failure policy, and observability baseline.

Status: complete at contract level; implementation enforcement continues in
later phases.

## Phase 3: Stack Decision And Contract Tests

- Choose implementation language and packaging.
- Record the choice in an ADR.
- Add formatter, test runner, schema validation, and contract-test commands.
- Add fixture tests for module metadata and runtime profile examples.
- Add negative tests for invalid modules and runtime profiles.
- Add cross-field tests for invariants that JSON Schema cannot express.

Status: complete for the current contract surface.

## Phase 4A: Control Plane And Runtime Plane Contracts

- Define the Cloudflare Control Plane and Hetzner Runtime Plane boundary.
- Define the memory feedback loop from Hetzner runtime storage to Cloudflare consolidated memory.
- Define D1 constraints, audit retention, Vectorize filtering boundaries, and AI Gateway usage.
- Define initial Cloudflare resource names and Hetzner runtime storage responsibilities.

Status: complete at contract and scaffold level.

## Phase 4B: Registries

- Implement registry interfaces for skills, instructions, tools, knowledge scopes, data scopes, memory scopes, policies, and validators. (Initial local implementation complete.)
- Implement deterministic registry discovery and query semantics. (Initial local implementation complete.)
- Add graph validation for missing references, circular dependencies, conflicts, and unauthorized transitive capabilities. (Initial local implementation complete.)
- Add fixtures and tests for module discovery and dependency resolution. (Initial local fixtures and tests complete.)

Status: initial implementation complete.

## Phase 4C: Infrastructure Scaffolding

- Add Cloudflare D1 schema contracts for control metadata.
- Derive executable Cloudflare D1 migrations from the control-plane contract.
- Add Hetzner runtime storage schema contracts.
- Derive executable Hetzner PostgreSQL migrations and server bootstrap scripts.
- Add positive and negative storage contract fixtures.
- Add GitHub Actions validation and manual infrastructure smoke checks.
- Add Wrangler configuration after resource names and bindings are documented.
- Add the Cloudflare Control API Worker scaffold and `POST /composition/context` contract.
- Implement D1/KV-backed `POST /composition/context` registry queries. (Initial dev implementation complete.)
- Add D1 seed tooling that derives registry records from module contracts. (Initial dev implementation complete.)
- Add deployment workflows after local infrastructure validation commands exist.
- Add Hetzner Runtime Flight Recorder storage contracts and migration. (Initial implementation complete.)

Status: initial control-plane implementation complete. Runtime Entry Point and
Flight Recorder writer are implemented for the first composition path.
Knowledge ingestion, memory ingestion, Vectorize-ready retrieval, and
AI Gateway routing are implemented at Worker/API level; async indexing workers
and remote index population remain pending.

## Phase 5: Analyzer And Composer

- Implement task classification and risk detection. (Initial rule-based implementation complete.)
- Consume Control Plane candidate scoring, policy decisions, scope grants, and graph validation. (Initial implementation complete.)
- Emit validated, version-pinned runtime profiles. (Initial implementation complete.)
- Add recomposition tests with parent profile traceability. (Initial implementation complete.)
- Add runtime entrypoint wiring from task intake to Control API client to composed profile. (Initial implementation complete.)
- Expand analyzer coverage beyond code-review fixtures.

Status: initial implementation complete; broader task coverage remains.

## Phase 6: Runtime Loop

- Implement context management.
- Implement planning and execution orchestration.
- Enforce tool, token, duration, data-read, memory, and recomposition limits.
- Emit Flight Recorder runtime events and checkpoints. (Initial writer complete.)
- Implement profile-scoped Tool Gateway.
- Implement validation before final response/action.

Status: storage contracts, initial run start path, profile-scoped Tool Gateway,
and minimal runtime loop complete for the current code-review fixture.

## Phase 6B: Productive Runtime Core

Implement this phase only after the Runtime Preflight Gate is satisfied:

1. Finalize the generic runtime contract. (Initial docs and schema complete.)
2. Define the Runtime API/CLI contract. (Initial docs and examples complete.)
3. Wire runtime execution to real Hetzner PostgreSQL and artifact storage.
4. Enforce all Runtime Agent Profile limits and access boundaries.
5. Harden the Tool Gateway for productive execution.
6. Bind Context Manager retrieval to `POST /retrieval/context`.
7. Make validation profile- and task-contract driven.
8. Implement controlled recomposition without runtime self-granting.
9. Add a live dev end-to-end gate across Cloudflare and Hetzner.
10. Add the operations baseline and runbooks.

Status: queued behind Phase 0.

## Phase 7: Operational Hardening

- Expand observability and trace export.
- Plan and enforce runtime artifact retention. (Initial planner complete.)
- Add evaluation fixtures.
- Add safety tests for permissions and scoped access.
- Add documentation for deployment and operations.

Status: initial runtime redaction and retention planning complete; Cloudflare
knowledge and memory ingestion endpoints are implemented; the Hetzner memory
feedback client exists; Control API retrieval and AI Gateway routes are
implemented; memory candidate extraction/validation and the controlled learning
fixture exist; operational cleanup jobs, async indexing, and broader telemetry
remain pending.
