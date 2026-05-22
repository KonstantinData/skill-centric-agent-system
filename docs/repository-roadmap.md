# Repository Roadmap

## Current Position

The repository has completed the foundation, contract hardening, contract-test
setup, local registry foundation, Cloudflare/Hetzner infrastructure contracts,
Control API Worker scaffold, D1-backed `POST /composition/context`, dev D1
registry seed path, and the first Analyzer/Composer implementation.
The Hetzner Runtime Plane also has the initial Flight Recorder storage contract
for runtime events, checkpoints, stop reasons, token budgets, and idempotency.

The next main implementation block is wiring the composed profile into the
runtime entrypoint and beginning Phase 6. Infrastructure follow-up work remains
for knowledge ingestion, memory ingestion, Vectorize, AI Gateway, and the
Hetzner runtime loop.

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

Status: initial control-plane implementation complete. Knowledge ingestion,
memory ingestion, Runtime Flight Recorder writer implementation, Vectorize, and
AI Gateway integration remain pending.

## Phase 5: Analyzer And Composer

- Implement task classification and risk detection. (Initial rule-based implementation complete.)
- Consume Control Plane candidate scoring, policy decisions, scope grants, and graph validation. (Initial implementation complete.)
- Emit validated, version-pinned runtime profiles. (Initial implementation complete.)
- Add recomposition tests with parent profile traceability. (Initial implementation complete.)
- Add runtime entrypoint wiring from task intake to Control API client to composed profile.
- Expand analyzer coverage beyond code-review fixtures.

Status: initial implementation complete; runtime wiring and broader task coverage remain.

## Phase 6: Runtime Loop

- Implement context management.
- Implement planning and execution orchestration.
- Enforce tool, token, duration, data-read, memory, and recomposition limits.
- Emit Flight Recorder runtime events and checkpoints.
- Implement validation before final response/action.

Status: storage contracts complete; runtime implementation pending.

## Phase 7: Operational Hardening

- Expand observability and trace export.
- Add evaluation fixtures.
- Add safety tests for permissions and scoped access.
- Add documentation for deployment and operations.

Status: pending.
