# Repository Roadmap

## Phase 1: Foundation

- Define architecture and contracts.
- Add JSON schemas for module metadata and runtime profiles.
- Add representative task and profile examples.
- Record initial architecture decisions.

## Phase 2: Contract Hardening

- Specify Task Analyzer output and failure behavior.
- Define registry query semantics: discover, score, filter, resolve, graph validation.
- Add structured scoring metadata to module contracts.
- Add runtime profile version pinning and recomposition traceability.
- Expand execution limits beyond tool calls.
- Define auth/authz, failure policy, and observability baseline.

## Phase 3: Stack Decision And Contract Tests

- Choose implementation language and packaging.
- Record the choice in an ADR.
- Add formatter, test runner, schema validation, and contract-test commands.
- Add fixture tests for module metadata and runtime profile examples.

## Phase 4: Registries

- Implement registry interfaces for skills, instructions, tools, knowledge scopes, data scopes, memory scopes, policies, and validators.
- Implement deterministic registry discovery and query semantics.
- Add graph validation for missing references, circular dependencies, conflicts, and unauthorized transitive capabilities.
- Add fixtures and tests for module discovery and dependency resolution.

## Phase 5: Analyzer And Composer

- Implement task classification and risk detection.
- Implement module scoring with thresholds, negative signals, and deterministic tie-breaks.
- Implement policy and authorization filtering.
- Emit validated, version-pinned runtime profiles.
- Add recomposition tests with parent profile traceability.

## Phase 6: Runtime Loop

- Implement context management.
- Implement planning and execution orchestration.
- Enforce tool, token, duration, data-read, memory, and recomposition limits.
- Implement validation before final response/action.

## Phase 7: Operational Hardening

- Expand observability and trace export.
- Add evaluation fixtures.
- Add safety tests for permissions and scoped access.
- Add documentation for deployment and operations.
