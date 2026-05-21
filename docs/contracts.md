# Contracts

## Module Metadata

Selectable modules are the system's composition units. A module can represent a skill, instruction, tool, knowledge scope, data scope, policy, validator, or memory scope.

Every selectable module must be:

- versioned,
- discoverable through a registry,
- scoreable against task signals,
- filterable by policy,
- testable or otherwise verifiable.

The machine-readable contract lives in `schemas/module.schema.json`.

## Runtime Agent Profile

The runtime profile is the Composer's output and the Agent Runtime's input. It must describe the exact execution surface for a task.

The machine-readable contract lives in `schemas/runtime-profile.schema.json`.

Required profile concerns:

- task identity and objective,
- risk level,
- selected instructions and skills,
- allowed tools,
- scoped knowledge, data, and memory access,
- applicable policies,
- required validators,
- execution limits.

## Selection Rules

1. Candidate modules are discovered through registries.
2. Candidates are scored against task signals.
3. Policies may deny candidates even when they score highly.
4. The Composer emits a profile with explicit module references.
5. Validators check profile integrity before execution.

## Recomposition

If the runtime discovers that the task was misclassified or needs additional capability, it must request a new profile composition step instead of silently expanding its own permissions.

The new profile should preserve traceability to the prior profile through a parent/profile version field once that field exists in implementation.

## Anti-Patterns

- grant all tools for every task,
- load the whole knowledge base by default,
- select skills only by keyword matching,
- bypass policies because a prompt says a capability is useful,
- keep durable architecture contracts only in chat or Notion.
