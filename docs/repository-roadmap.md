# Repository Roadmap

## Phase 1: Foundation

- Define architecture and contracts.
- Add JSON schemas for module metadata and runtime profiles.
- Add representative task and profile examples.
- Record initial architecture decisions.

## Phase 2: Stack Decision

- Choose implementation language and packaging.
- Record the choice in an ADR.
- Add formatter, test runner, and validation commands.

## Phase 3: Registries

- Implement registry interfaces for skills, instructions, tools, knowledge scopes, data scopes, memory scopes, policies, and validators.
- Add fixtures and tests for module discovery.

## Phase 4: Analyzer And Composer

- Implement task classification and risk detection.
- Implement module scoring.
- Implement policy filtering.
- Emit validated runtime profiles.

## Phase 5: Runtime Loop

- Implement context management.
- Implement planning and execution orchestration.
- Implement validation before final response/action.

## Phase 6: Operational Hardening

- Add observability.
- Add evaluation fixtures.
- Add safety tests for permissions and scoped access.
- Add documentation for deployment and operations.
