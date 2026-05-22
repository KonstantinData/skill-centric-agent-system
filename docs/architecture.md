# Architecture

## Product Shape

The system is a skill-centric single-agent runtime. It does not become a multi-agent system by default. Instead, each user task is analyzed and converted into a task-specific `Runtime Agent Profile`.

The profile defines what the runtime may use for that task:

- instructions,
- skills,
- tools,
- knowledge scopes,
- data scopes,
- memory scopes,
- policies,
- validators,
- execution limits,
- failure policy,
- observability settings.

## Canonical Flow

```mermaid
flowchart TD
    UI["UI / API"] --> Intake["Task Intake"]

    Intake --> Analyzer["Task Analyzer"]
    Analyzer --> Composer["Agent Composer"]

    Composer --> InstructionRegistry["Instruction Registry"]
    Composer --> SkillRegistry["Skill Registry"]
    Composer --> ToolRegistry["Tool Registry"]
    Composer --> KnowledgeIndex["Knowledge Index"]
    Composer --> DataRegistry["Data Scope Registry"]
    Composer --> MemoryRegistry["Memory Registry"]
    Composer --> PolicyRegistry["Policy Registry"]
    Composer --> ValidatorRegistry["Validator Registry"]

    Composer --> Profile["Runtime Agent Profile"]

    Profile --> Agent["Single Agent Runtime"]

    Agent --> Context["Context Manager"]
    Agent --> Planner["Planner"]
    Agent --> Executor["Executor"]
    Agent --> Validator["Validator"]

    Context --> LoadedInstructions["Loaded Instructions"]
    Context --> RetrievedKnowledge["Retrieved Knowledge"]
    Context --> RelevantMemory["Relevant Memory"]

    Executor --> SelectedSkills["Selected Skills"]
    Executor --> AllowedTools["Allowed Tools"]
    Executor --> ScopedData["Scoped Data Access"]

    Validator --> Agent
    Agent --> Response["Response / Action"]
```

## Component Responsibilities

`Task Intake` normalizes user/API input, attachments, environment, repository state, explicit constraints, and submitter identity into a task envelope.

`Task Analyzer` converts the task envelope into structured task signals: task type, risk level, domains, required inputs, available inputs, capability hints, constraints, missing information, and auth claims. It may use rules, classifiers, or LLM assistance, but its output must be explicit and testable.

`Agent Composer` queries registries, scores candidate modules, applies policies, validates the dependency graph, pins module versions, and emits a runtime profile. It does not load broad capabilities by default.

`Runtime Agent Profile` is the task-local execution contract. It is immutable for a single execution attempt. Recomposition creates a new profile generation with a parent profile reference and reason.

`Single Agent Runtime` executes the task through context management, planning, execution, validation, and response. It cannot grant itself tools, data, memory, or knowledge outside the profile.

`Context Manager` loads only relevant instructions, knowledge, memory, and prior tool results allowed by the profile.

`Planner` creates and revises the task plan inside profile constraints and budgets.

`Executor` invokes selected skills, allowed tools, and scoped data access. Every invocation must be checked against profile permissions and remaining limits.

`Validator` checks profile integrity before execution, then output contracts, policy compliance, unauthorized access, and task completion before final response or action.

## Composition Pipeline

The Composer is a deterministic pipeline around model-assisted analysis, not a free-form prompt:

1. Read analyzer output and task constraints.
2. Discover candidates from typed registries.
3. Score candidates against structured signals.
4. Remove denied candidates through policy and authz filters.
5. Resolve dependencies and pinned versions.
6. Validate the candidate graph.
7. Emit a runtime profile.
8. Validate the profile schema and cross-field invariants.

The runtime receives only the validated profile. If execution needs a capability that is not present, it requests recomposition instead of expanding permissions locally.

## Core Invariant

Self-assembly is controlled. Capability selection must go through registries, scoring, policies, graph validation, and profile validation. Free-form prompt text may explain behavior, but it must not be the sole authority for granting capabilities.

## Implemented Surfaces

The current repository has implemented the first control-plane slice:

- schema-backed module metadata and runtime profile contracts,
- local deterministic module registry semantics,
- Cloudflare D1 control-plane migrations,
- a Cloudflare Control API Worker with `POST /composition/context`,
- D1-backed candidate scoring, policy binding, scope binding, and graph validation,
- generated dev D1 seed data derived from `examples/modules/*.json`,
- a rule-based Task Analyzer for initial repository code-review tasks,
- a Runtime Profile Composer that consumes Control Plane context responses,
- an optional Python Control Plane client for `POST /composition/context`,
- Hetzner runtime-plane storage contracts and bootstrap scripts,
- a Hetzner Flight Recorder storage contract for runtime events, checkpoints,
  stop reasons, token budgets, and idempotency keys,
- a Runtime Entry Point that starts a run from task intake, composes a runtime
  profile, writes initial Flight Recorder events, and stores event/checkpoint
  payloads as artifact URIs,
- runtime storage ports with an in-memory implementation for tests and a
  Postgres adapter shape for Hetzner integration,
- a profile-scoped Tool Gateway for `git-read`, `filesystem-read`, and
  `test-runner`,
- a minimal Single Agent Runtime loop that executes context, planner, executor,
  and validator phases against the composed profile,
- Cloudflare Control API knowledge and memory ingestion endpoints that write
  R2 objects and D1 metadata,
- `POST /retrieval/context` with D1 scope prefiltering, Vectorize bindings, and
  D1 post-validation of semantic matches,
- fail-closed production OpenAI routing through Cloudflare AI Gateway,
- Memory Candidate Extraction and Validation on the Hetzner Runtime Plane,
  including status/reason updates before Cloudflare ingestion,
- a controlled learning evaluation fixture that proves approved memory can be
  retrieved later while unauthorized retrieval is blocked.

The following architecture components are still pending implementation:

- expanded runtime planning and execution beyond the initial code-review loop,
- async ingestion/indexing workers for knowledge and memory embeddings.

## Operational Baseline

Auth/authz, failure semantics, and observability are part of the architecture from the start:

- Every composition uses an explicit principal, roles, and authorization policies.
- Unsafe ambiguity fails closed or requests clarification.
- Every profile defines trace settings and required event capture.
- Limits cover tool calls, tokens, duration, data reads, memory operations, and recomposition count.
- Runtime events store large planned-action, execution, and result payloads by
  artifact URI rather than inline JSON.
