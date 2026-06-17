# Registries

## Purpose

Registries are the controlled selection layer between task analysis and runtime
profile composition. They prevent the Agent from inventing capabilities at
runtime by selecting only known, versioned, policy-filtered modules.

The first implementation is local and deterministic:

- module metadata is loaded from `registry/modules/**/module.json` records that
  conform to `schemas/module.schema.json`,
- discovery uses structured fields, not keyword-only matching,
- direct modules are scored with explicit `selection.base_score` and
  `selection.score_modifiers`,
- dependency-only modules are excluded from direct discovery and can enter a
  runtime profile only through graph validation,
- scoring can apply taxonomy feedback penalties from recent F1/F2/R8 outcomes
  through `TaskSignals.error_feedback`,
- policy filtering fails closed when required policies are missing,
- graph validation checks transitive module references before profile assembly.

## Implementation

The in-memory registry lives in:

```text
src/skill_centric_agent_system/registries/modules.py
```

It exposes:

- `discover(query)`: filter by kind, capability class, domain, task type, and
  available inputs.
- `score(module, task_signals)`: return score, matched signals, negative
  signals, and explanations.
- `filter_candidate(module, policy_context)`: return `allow`, `deny`, or
  `needs_clarification`.
- `resolve(name, version)`: resolve exact pinned versions, or latest local
  version when no version is supplied.
- `validate_graph(selected_module_names)`: validate references, expected
  module kinds, circular dependencies, and denied transitive capabilities.

## Boundary

`POST /composition/context` now calls equivalent registry operations against
Cloudflare-backed metadata:

- D1 tables store active module versions, structured selection metadata,
  dependencies, policy bindings, and principal scope bindings.
- KV is read only for `registry:version`; it is not used for policy-sensitive
  decisions.
- The endpoint returns scored candidates, applicable policies, allowed scopes,
  policy decisions, and graph-validation output.

The local registry is still useful now because it locks the semantics and test
behavior before storage-specific query code is added.

The detailed module metadata contract is documented in
`docs/policies/module-contracts.md`. That policy also defines the SOTA 2026
provenance, selection-mode, and fixture-evidence contract that registry schema
and validator migrations must enforce before registry evidence is considered
complete.

## Source Of Truth

`registry/` is the durable repository source for module metadata. `examples/`
contains fixtures, generated examples, and API payload samples only.

Skill modules have two layers:

- `module.json`: machine-readable selection, dependency, policy, version,
  environment, runtime role, runtime contract, provenance, and fixture evidence
  metadata.
- `SKILL.md`: agent-readable execution guidance loaded only after a sealed
  runtime profile selects the skill.

The state flow is one-way:

```text
registry/modules/**/module.json
  -> registry validation
  -> registry/versions/lockfile.json
  -> generated Control Plane seed SQL
  -> deployed Control Plane state
```

Control Plane state can drift operationally, but deploys are reproduced from the
registry source and lockfile. Do not edit generated seed SQL as the source of
truth.

## Cloudflare Seed

The dev D1 registry seed is generated from `registry/modules/**/module.json`:

```text
python scripts/cloudflare/generate_control_plane_seed.py --output examples/control-plane/dev-seed.sql
```

The generator writes idempotent upserts for `modules`, `module_versions`,
`module_selection_metadata`, `module_dependencies`, `policy_bindings`, and
`scope_bindings`. Referenced tools, scopes, policies, and validators are now
first-class registry modules instead of generated source-of-truth stubs.
The current seed includes first-slice skill modules for `code-review`,
`research`, `task-execution`, and `general-task`, plus the tool, scope, policy,
and validator dependencies needed by those modules.

`examples/control-plane/cloudflare-control-plane.json` remains a storage
contract fixture for the broader Cloudflare record model, including knowledge
and memory records. `examples/control-plane/dev-seed.sql` is the operational dev
registry seed used by the current Worker smoke test.

