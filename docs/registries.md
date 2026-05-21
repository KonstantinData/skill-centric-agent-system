# Registries

## Purpose

Registries are the controlled selection layer between task analysis and runtime
profile composition. They prevent the Agent from inventing capabilities at
runtime by selecting only known, versioned, policy-filtered modules.

The first implementation is local and deterministic:

- module metadata is loaded from JSON records that conform to
  `schemas/module.schema.json`,
- discovery uses structured fields, not keyword-only matching,
- scoring applies explicit `selection.base_score` and
  `selection.score_modifiers`,
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
