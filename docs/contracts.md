# Contracts

## Contract Boundary

The system is allowed to assemble a task-local agent profile, but it is not allowed to invent capabilities freely. Selection must pass through:

1. task analysis,
2. registry discovery,
3. scoring,
4. policy filtering,
5. graph validation,
6. profile validation.

The schema `$id` values use stable URNs during local development. A deployment that publishes schemas externally must map them to stable public URIs without changing the contract meaning.

## Task Analyzer Contract

`Task Analyzer` turns normalized task intake into structured task signals for the Composer. The first implementation may combine rules and LLM classification, but its output must be explicit and testable.

Minimum analyzer output:

- `task_type`: normalized task class, for example `code-review`.
- `risk_level`: `low`, `medium`, `high`, or `critical`.
- `domains`: domain tags such as `software-engineering`, `git`, or `notion`.
- `required_inputs`: inputs the runtime needs before execution.
- `available_inputs`: inputs already present in the task envelope.
- `capability_hints`: requested capability classes such as `analysis`, `retrieval`, or `execution`.
- `constraints`: write access, destructive action allowance, privacy, environment, and time constraints.
- `missing_information`: blockers that should trigger clarification before composition.
- `auth_claims`: submitter identity and roles available for authorization checks.

If required inputs or auth claims are missing, the Composer must fail closed or request clarification instead of composing a broad profile.

## Module Metadata

Selectable modules are the system's composition units. A module can represent a skill, instruction, tool, knowledge scope, data scope, policy, validator, or memory scope.

Every selectable module must be:

- versioned,
- discoverable through a registry,
- scoreable against structured task signals,
- filterable by policy,
- graph-validatable,
- testable or otherwise verifiable.

The machine-readable contract lives in `schemas/module.schema.json`.

`triggers` are weak human-readable hints. They may improve recall, but they are never sufficient for selection. Structured fields such as `capability_class`, `domain_tags`, `task_signals`, and `selection.score_modifiers` are the scoring surface.

## Registry Query Semantics

Each registry must expose structured operations with deterministic outputs:

- `discover(query)`: return candidate modules by kind, capability class, domain, task type, and required inputs.
- `score(candidate, task_signals)`: return numeric score, matched signals, negative signals, and explanation.
- `filter(candidate, policy_context)`: apply policy and authz rules; return allow, deny, or needs clarification.
- `resolve(candidate)`: load the pinned module version and dependency references.
- `validate_graph(profile_candidates)`: reject missing references, unsupported versions, circular dependencies, conflicts, and unauthorized transitive capabilities.

Graph validation must cover references from `required_tools`, `optional_tools`, `knowledge_scopes`, `data_scopes`, `policies`, and `validators`. A highly scored module can still be rejected if its dependency graph is invalid.

## Scoring Rules

Scoring combines positive and negative evidence:

- task type match,
- domain tag match,
- required input availability,
- risk-level compatibility,
- capability class fit,
- explicit user constraints,
- negative phrases or denied capability hints,
- policy preconditions.

Keyword or phrase matches alone must not select a module. The Composer should use thresholds and tie-breaks that are deterministic and covered by tests once implementation begins.

## Runtime Agent Profile

The runtime profile is the Composer's output and the Agent Runtime's input. It describes the exact execution surface for one execution attempt.

The machine-readable contract lives in `schemas/runtime-profile.schema.json`.

Required profile concerns:

- task identity and objective,
- profile version and generation,
- parent profile and recomposition reason,
- risk level,
- authorization context,
- selected instructions and skills,
- allowed tools,
- scoped knowledge, data, and memory access,
- applicable policies,
- required validators,
- pinned versions for every selected module,
- execution limits,
- failure policy,
- observability settings.

Instructions, policies, and validators are non-empty because every execution needs baseline behavior, guardrails, and completion checks. Skills may be empty when a task can be handled by instructions, scoped knowledge, and tools without a specialized skill.

## Version Pinning

Profile arrays reference selected module names. `module_versions` pins every selected instruction, skill, tool, scope, policy, validator, and memory module to an exact semantic version.

The profile validator must reject a profile when:

- a selected module is missing from `module_versions`,
- `module_versions` contains a module not selected or required transitively,
- a pinned version is unavailable,
- a module dependency resolves to an unpinned version.

## Auth And Authorization

Task submission and capability requests require explicit authorization context. The profile must include the principal, roles, and authorization policies that were used during composition.

Policies must be able to deny:

- task submission,
- write access,
- destructive actions,
- data-scope access,
- memory-scope access,
- tool invocation,
- requested recomposition.

Denied authorization must fail closed unless the failure policy explicitly allows clarification.

## Recomposition

If the runtime discovers that the task was misclassified or needs additional capability, it must request a new profile composition step instead of silently expanding its own permissions.

The new profile must set:

- `profile_generation` to the next generation,
- `parent_profile_id` to the previous profile,
- `recomposition_reason` to the reason for the new composition.

Recomposition must respect `limits.max_recompositions` and must run the same registry, scoring, policy, graph, and profile validation pipeline as the first composition.

## Failure Semantics

The Composer and runtime must fail closed for unsafe ambiguity.

Minimum behavior:

- Composer cannot build a valid profile: return a structured error or request clarification.
- Policy denies a candidate: remove the candidate or return a policy denial if the task cannot be completed.
- Graph validation fails: reject the profile and report the invalid dependency path.
- Profile validation fails: do not execute the runtime.
- Runtime exceeds limits: stop execution according to `failure_policy.on_budget_exhausted`.
- Output validator fails: either recompose once when permitted or return a validation failure.

## Observability

Observability begins before runtime hardening. At minimum, each composed profile defines trace settings and event capture.

Minimum events:

- task intake normalized,
- task analyzed,
- candidates discovered,
- candidates scored,
- policies evaluated,
- graph validated,
- profile emitted,
- profile validated,
- runtime started,
- tool or data access attempted,
- validator executed,
- runtime completed or failed.

Trace data must redact sensitive task content when `observability.redact_sensitive_data` is true.

## Anti-Patterns

- grant all tools for every task,
- load the whole knowledge base by default,
- select skills only by keyword matching,
- bypass policies because a prompt says a capability is useful,
- let runtime code call `self.grant_tool()` or equivalent hidden expansion,
- keep durable architecture contracts only in chat or Notion.
