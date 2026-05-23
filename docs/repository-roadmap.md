# Repository Roadmap

## Current Position

The repository has completed the foundation, contract hardening, contract-test
setup, local registry foundation, Cloudflare/Hetzner infrastructure contracts,
Control API Worker scaffold, D1-backed `POST /composition/context`, dev D1
registry seed path, and the first Analyzer/Composer implementation.
The Hetzner Runtime Plane also has the initial Flight Recorder storage contract
for runtime events, checkpoints, stop reasons, token budgets, idempotency, and
atomic run-local event indexing.
The Runtime Entry Point can start a run from task intake, compose the runtime
profile, create the runtime run, and emit initial artifact-backed Flight
Recorder events. The profile-scoped Tool Gateway and first minimal runtime loop
can execute read-only code-review fixture work, with fail-closed Runtime Profile
enforcement for tools, scopes, budgets, duration, data reads, memory operations,
and recomposition count. The Tool Gateway now enforces per-tool allowlists,
risk gating, blocked argument checks, timeouts, output limits, and access audit
events. The Runtime Context Manager now calls the bounded Control API retrieval
endpoint and rejects retrieval responses containing scopes outside the active
profile. The Validator phase now runs the validators selected by the active
profile and fail-closes unknown or failed validators. Controlled recomposition
now emits `recomposition_requested`, stops the current run with
`needs_recomposition`, composes a new immutable profile generation, and
continues through a new run attempt without mutating the active profile. A
manual live dev E2E gate script now covers the Cloudflare-to-Hetzner runtime
path. Runtime
operations now have a baseline runbook for migrations, smoke tests,
diagnostics, and disable paths. Runtime artifact redaction and retention
planning are implemented for the Flight Recorder artifact path. The Control API
also has knowledge/memory ingestion, a D1-gated
`POST /retrieval/context` endpoint with Vectorize bindings and post-validation,
and a fail-closed AI Gateway route for OpenAI chat completions. The Runtime
Plane can extract and validate memory candidates from completed runtime steps
before submitting approved candidates to Cloudflare durable memory. The Control
API now requires bearer authentication for every non-health route and supports
endpoint-scoped tokens. The Task Analyzer has evaluation coverage for
code-review, research, task-execution, and general tasks. Composition scoring
has positive and negative evaluation fixtures, and runtime artifacts chunk large
string payloads into manifest-referenced text chunks.

The Runtime Preflight Gate is complete. The initial productive runtime core is
implemented. Queue-backed Cloudflare embedding indexing is implemented. Broader
runtime expansion and retention cleanup remain explicit backlog items and must
not obscure the runtime entry gate.

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

Status: complete. The durable gate is documented in `docs/runtime-preflight.md`.

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
Knowledge ingestion, memory ingestion, Vectorize-ready retrieval,
AI Gateway routing, queue-backed embedding updates, and scoped Vectorize
population are implemented at Worker/API level.

## Phase 5: Analyzer And Composer

- Implement task classification and risk detection. (Initial rule-based implementation complete.)
- Consume Control Plane candidate scoring, policy decisions, scope grants, and graph validation. (Initial implementation complete.)
- Emit validated, version-pinned runtime profiles. (Initial implementation complete.)
- Add recomposition tests with parent profile traceability. (Initial implementation complete.)
- Add runtime entrypoint wiring from task intake to Control API client to composed profile. (Initial implementation complete.)
- Expand analyzer coverage beyond code-review fixtures. (Initial evaluation
  coverage complete.)

Status: initial implementation complete. Broader task coverage should now grow
through evaluation fixtures before classifier or LLM-assisted analysis is
introduced.

## Phase 6: Runtime Loop

- Implement context management.
- Implement planning and execution orchestration.
- Enforce tool, token, duration, data-read, memory, and recomposition limits.
- Emit Flight Recorder runtime events and checkpoints. (Initial writer complete.)
- Implement profile-scoped Tool Gateway.
- Implement validation before final response/action.

Status: storage contracts, initial run start path, profile-scoped Tool Gateway,
fail-closed profile enforcement, and minimal runtime loop complete for the
current code-review fixture.

## Phase 6B: Productive Runtime Core

Implement this phase only after the Runtime Preflight Gate is satisfied:

1. Finalize the generic runtime contract. (Initial docs and schema complete.)
2. Define the Runtime API/CLI contract. (Initial docs and examples complete.)
3. Wire runtime execution to real Hetzner PostgreSQL and artifact storage. (Initial CLI storage session complete.)
4. Enforce all Runtime Agent Profile limits and access boundaries. (Initial fail-closed enforcer complete.)
5. Harden the Tool Gateway for productive execution. (Initial hardening complete.)
6. Bind Context Manager retrieval to `POST /retrieval/context`. (Initial binding complete.)
7. Make validation profile- and task-contract driven. (Initial framework complete.)
8. Implement controlled recomposition without runtime self-granting. (Initial continuation path complete.)
9. Add a live dev end-to-end gate across Cloudflare and Hetzner. (Manual gate script complete.)
10. Add the operations baseline and runbooks. (Initial runbook complete.)

Status: initial implementation complete. Steps 1-10 have initial implementations.
Controlled recomposition can now continue through a newly composed profile and
new run attempt.

## Phase 7: Operational Hardening

- Expand observability and trace export.
- Plan and enforce runtime artifact retention. (Initial planner complete.)
- Add analyzer and composition-scoring evaluation fixtures. (Initial fixtures complete.)
- Add safety tests for permissions and scoped access.
- Add documentation for deployment and operations.

Status: initial runtime redaction and retention planning complete; Cloudflare
knowledge and memory ingestion endpoints are implemented; the Hetzner memory
feedback client exists; Control API retrieval and AI Gateway routes are
implemented; memory candidate extraction/validation and the controlled learning
fixture exist; Control API auth, atomic event indexing, chunked artifact
persistence, live Hetzner E2E evidence, and live Postgres concurrency evidence
are implemented; the AI Gateway secret rollout and live LLM smoke workflow is
implemented, with live execution gated by Cloudflare Worker script permissions,
OpenAI provider auth, and optional Authenticated Gateway auth; queue-backed
embedding indexing is implemented;
operational cleanup jobs and broader telemetry remain pending.
