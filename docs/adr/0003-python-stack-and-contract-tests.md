# ADR-0003: Python Stack And Contract-Test Harness

## Status

Accepted

## Date

2026-05-21

## Context

The repository has schema-first contracts for selectable modules and runtime profiles. Before implementing registries, analyzers, composers, or runtime loops, the project needs a concrete implementation stack and executable contract tests.

The immediate needs are:

- JSON Schema validation,
- positive tests for valid examples,
- negative tests for invalid modules and profiles,
- room for later LLM/tooling integrations,
- simple local developer commands.

Python is a strong fit because the expected implementation surface is agent-oriented orchestration, schema validation, registry logic, and later LLM/tool integrations. The ecosystem provides mature packages for JSON Schema validation, test automation, and agent tooling.

## Decision

Use Python as the implementation stack for the first runtime and contract-test harness.

Adopt:

- Python 3.11+,
- `pytest` for tests,
- `jsonschema` for Draft 2020-12 schema validation,
- `ruff` for formatting and linting,
- `pyproject.toml` as the project configuration entrypoint.

Contract tests must include both positive and negative cases. Positive cases validate committed examples. Negative cases prove that known-invalid module metadata and runtime profiles are rejected.

Cross-field invariants that JSON Schema cannot express cleanly should be covered by explicit pytest assertions. The first such invariant is that every selected runtime profile module must have an exact entry in `module_versions`, and unselected direct version pins must be rejected by the contract-test harness.

## Consequences

Positive:

- The implementation stack is explicit before runtime code appears.
- Schema changes are guarded by executable tests.
- Invalid metadata cannot silently become accepted behavior.
- The same test harness can later grow into registry, composer, and runtime contract tests.

Tradeoffs:

- Runtime deployment shape is not optimized for a browser-native TypeScript stack.
- Cross-field validation needs Python test helpers until dedicated validators exist.
- CI setup is still a follow-up task.

## Follow-Up

- Add CI after the first stable test command is accepted.
- Promote cross-field pytest helpers into runtime validators once the validator module exists.
- Add Composer tests for scoring thresholds and keyword-only anti-patterns after registry fixtures exist.
