# ADR-0001: Self-Composing Single-Agent Runtime

## Status

Accepted

## Date

2026-05-21

## Context

The system needs to adapt to different task types without becoming a loosely controlled collection of agents. The target architecture is a single runtime agent that changes its task-local operating surface through a composed profile.

The system must prevent unrestricted self-assembly. Skills, instructions, tools, knowledge, data, memory, policies, and validators need to be selected through controlled metadata and policy checks.

## Decision

Build the repository around one `Single Agent Runtime` configured by a task-specific `Runtime Agent Profile`.

The profile is produced by an `Agent Composer` after:

1. task intake,
2. task analysis,
3. registry lookup,
4. scoring,
5. policy filtering,
6. profile validation.

The runtime may request recomposition when the task changes materially, but it must not silently grant itself additional capabilities.

## Consequences

Positive:

- Keeps orchestration simple enough to reason about.
- Makes capability selection explicit and testable.
- Allows skills and policies to evolve independently.
- Creates a clear boundary between task tracking, architecture contracts, and runtime execution.

Tradeoffs:

- The Composer and registry contracts become critical infrastructure.
- Early implementation must prioritize schemas and validation before broad runtime features.
- Recomposition needs traceability to avoid hidden permission expansion.

## Follow-Up

- Choose the implementation stack and record it in a separate ADR.
- Add contract tests for `schemas/module.schema.json` and `schemas/runtime-profile.schema.json`.
- Implement the first registry and profile validator.
