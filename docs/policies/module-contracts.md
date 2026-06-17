# Module Contracts

Use this reference when defining selectable modules. All fields must conform to
`schemas/module.schema.json`. A module that fails schema validation will be
rejected by the registry before it can be selected.

The governed source of truth is `registry/modules/**/module.json`. For skill
modules, `SKILL.md` is an agent-readable entrypoint loaded only after the
Composer selects the skill through a sealed runtime profile. The Composer must
not parse `SKILL.md` for selection metadata.

## Required Metadata

```json
{
  "$schema": "../../../../schemas/module.schema.json",
  "schema_version": "0.1.0",
  "name": "module-name",
  "version": "0.1.0",
  "status": "active",
  "kind": "skill|instruction|tool|knowledge_scope|data_scope|policy|validator|memory_scope",
  "description": "What this module provides and when to select it.",
  "runtime_roles": {
    "default": "runtime",
    "allowed": ["runtime"]
  },
  "capability_class": "analysis|planning|execution|retrieval|validation|policy|instruction|tool_access|knowledge_access|data_access|memory_access|context",
  "environments": ["dev", "staging", "prod"],
  "entrypoint": {
    "type": "skill_folder",
    "path": "SKILL.md"
  },
  "runtime_contract": {
    "profile_sealable": true,
    "requires_version_pin": true,
    "requires_handler_binding": true
  },
  "domain_tags": ["domain-a", "domain-b"],
  "task_signals": {
    "task_types": ["code-review"],
    "risk_levels": ["low", "medium"],
    "domains": ["software-engineering"],
    "required_inputs": ["repository"],
    "phrases": ["review", "analyze"],
    "negative_phrases": ["deploy", "delete"]
  },
  "triggers": ["review", "analyze"],
  "inputs": ["input-name"],
  "outputs": ["output-name"],
  "required_tools": ["tool-name"],
  "optional_tools": ["tool-name"],
  "knowledge_scopes": ["scope-name"],
  "data_scopes": ["scope-name"],
  "policies": ["policy-name"],
  "validators": ["validator-name"],
  "provenance": {
    "owner": {
      "type": "person",
      "name": "Module Owner"
    },
    "problem_statement": "The concrete task or platform problem this module solves.",
    "acceptance_criteria": [
      "The module has positive and negative selection evidence."
    ],
    "source_of_truth": [
      {
        "type": "repo_path",
        "ref": "docs/policies/module-contracts.md",
        "reason": "Defines the governed module contract."
      }
    ],
    "rationale": "Why this module is directly selectable or dependency-only.",
    "requirement_id": "REQ-SCAS-REGISTRY-EXAMPLE"
  },
  "selection": {
    "mode": "direct",
    "base_score": 0.5,
    "score_modifiers": [
      {
        "signal": "task_type:code-review",
        "weight": 0.2,
        "reason": "Why this signal increases or decreases the score."
      }
    ],
    "requires_all_policies": true
  },
  "selection_evidence": {
    "positive_selection": [
      {
        "fixture": "examples/registry/selection-evidence/example-module.json",
        "expectation": "selected",
        "reason": "The positive fixture matches this module's task boundary."
      }
    ],
    "negative_selection": [
      {
        "fixture": "examples/registry/selection-evidence/example-module.json",
        "expectation": "rejected",
        "reason": "The negative fixture proves the module is not a catch-all."
      }
    ]
  },
  "tests": {
    "contract": ["tests/contract/module-contract.json"],
    "runtime": ["tests/test_runtime_skill_handlers.py::test_example"],
    "fixtures": ["examples/registry/selection-evidence/example-module.json"]
  }
}
```

## Field Reference

### Identity

`name` - Lowercase, hyphen-separated identifier. Must be unique within the
registry. Pattern: `^[a-z][a-z0-9-]*$`.

`version` - Semantic version (`MAJOR.MINOR.PATCH`). Increment when the module
contract changes. The registry uses this for version pinning in runtime profiles.
For `skill` modules that have executable runtime behavior, the runtime handler
registry binds code by the exact `name@version` pair selected in
`profile.skills` and `profile.module_versions`. Unknown or mismatched handler
versions fail closed before tool execution.

`kind` - The composition role of the module. Determines which registry slot the
module occupies and which profile fields it populates.

| kind | Populates profile field |
| --- | --- |
| `skill` | `skills` |
| `instruction` | `instructions` |
| `tool` | `tools` |
| `knowledge_scope` | `knowledge_scopes` |
| `data_scope` | `data_scopes` |
| `memory_scope` | `memory_scopes` |
| `policy` | `policies` |
| `validator` | `validators` |

`description` - One or two sentences. State what the module does and the
condition under which the Composer should select it. This text is not used for
scoring; it is for human reviewers and auditors.

`status` - Lifecycle status. `active` modules can be selected in environments
that allow them. `draft`, `deprecated`, and `disabled` are environment-gated and
must not become production selectable unless the environment allowlist permits
that status.

`environments` - Explicit environment allowlist. New modules do not inherit
staging or production access. Environment policy files under
`registry/environments/` must also allow the module status and capability class.

`runtime_roles` - Static module capability declaration. `default` is the role
the Composer should assign unless task-specific policy narrows it; `allowed`
lists every role the module may take. The final concrete role is stored in the
runtime profile. This mirrors the distinction between `profile_sealable` as a
module capability and `sealed` as a profile artifact state.

`entrypoint` - Required for `skill` modules. `entrypoint.path` is relative to the
module folder and must resolve to the local `SKILL.md`. Non-skill modules do not
define `entrypoint` in v0.1.0.

`runtime_contract` - Declares whether the module can participate in sealed
runtime profiles, requires exact version pins, and requires executable handler
binding. This is capability metadata, not profile state.

### Capability Classification

`capability_class` - Typed classification of the module's primary capability.
Used by the Composer to match capability hints from the Task Analyzer.

| class | Typical kind |
| --- | --- |
| `analysis` | skill |
| `planning` | skill |
| `execution` | skill, tool |
| `retrieval` | skill, knowledge_scope |
| `validation` | validator |
| `policy` | policy |
| `instruction` | instruction |
| `tool_access` | tool |
| `knowledge_access` | knowledge_scope |
| `data_access` | data_scope |
| `memory_access` | memory_scope |
| `context` | instruction, memory_scope |

`domain_tags` - String array of domain labels. Used during registry discovery to
narrow candidates before scoring. Examples: `software-engineering`, `git`,
`notion`, `finance`, `legal`.

### Task Signals

`task_signals` is a structured object. It is the primary scoring surface. Phrase
or keyword matches alone must never select a module. All sub-fields are arrays
and may be empty when the module applies broadly.

`task_signals.task_types` - Normalized task classes the module targets, for
example `code-review`, `research`, `task-execution`, `data-export`,
`document-summary`.

`task_signals.risk_levels` - Risk levels at which the module is applicable.
A module restricted to `low` and `medium` will not be selected for `high` or
`critical` tasks.

`task_signals.domains` - Domain overlap with `domain_tags`. Repeated here to
allow the scoring layer to weight domain match separately from the discovery
filter.

`task_signals.required_inputs` - Inputs that must be present before the module
is useful. A module with `required_inputs: ["diff"]` should not be selected if
no diff is available.

`task_signals.phrases` - Positive phrases that weakly increase recall during
candidate discovery. Not sufficient for selection on their own.

`task_signals.negative_phrases` - Phrases that signal the module is not
appropriate. A skill scoped to read-only analysis should list `deploy`,
`delete`, or `apply changes` here.

`triggers` - Kept for backwards compatibility and human readability. They are
weak hints and carry less weight than `task_signals`. Do not rely on triggers
alone for accurate selection.

### Capability Surface

`inputs` - Named inputs the module consumes. Used by the graph validator to
check that required inputs are available in the task envelope or from a prior
module output.

`outputs` - Named outputs the module produces. Used by the graph validator and
downstream module dependency resolution.

`required_tools` - Tools the module cannot function without. The Composer must
grant every required tool before selecting the module, or reject the module.

`optional_tools` - Tools the module uses when available. Their absence does not
block selection but may reduce effectiveness.

`knowledge_scopes` - Knowledge bases the module needs read access to. These are
validated against the profile's `knowledge_scopes` allowlist.

`memory_scope` modules are procedural Agent Memory scopes. They must not be
described or scored as factual Knowledge stores, and their negative selection
signals should penalize task-subject fact storage requests.

`data_scopes` - Data access scopes. Validated against the profile's
`data_scopes` allowlist and the principal's authorization claims.

`policies` - Policies that apply when this module is active. Referenced by name;
must exist in the policy registry.

`validators` - Validators that check this module's output contract. Referenced
by name; must exist in the validator registry.

### Selection Scoring

`selection` controls whether the Composer may score the module against task
signals.

`selection.mode` - `direct` modules can be discovered and scored from task
signals. `dependency_only` modules cannot be directly discovered or scored and
can only be included through graph validation from another selected module.

For `direct` modules, `selection.base_score` is the starting score between
`0.0` and `1.0` before any modifiers are applied. It represents the module's
general fit absent specific evidence.

For `direct` modules, `selection.score_modifiers` is the ordered list of
signal-weight pairs applied on top of the base score. Each modifier has:

- `signal` - The condition being evaluated. Format: `type:value`, for example
  `task_type:code-review`, `input:diff`, `phrase:deploy`, `risk_level:critical`.
- `weight` - A value between `-1.0` and `1.0`. Positive weights increase the
  score; negative weights decrease it.
- `reason` - A human-readable explanation of why this signal affects the score.
  Required. Auditors and tests use this to verify that scoring logic is
  intentional.

`selection.requires_all_policies` - When `true`, the Composer must confirm that
every policy in `policies` passes before the module can be selected. When
`false`, the module may be selected if at least one policy allows it, and
remaining policies are evaluated at runtime.

`dependency_only` modules must not define `base_score` or `score_modifiers`.

## SOTA 2026 Provenance And Selection Evidence Contract

The SOTA 2026 registry contract makes every production-selectable module answer
three audit questions before it can participate in composition:

1. Who owns the requirement and why does the module exist?
2. Can the module be selected directly from task signals, or only as a
   dependency of another selected module?
3. Which real fixtures prove the intended positive and negative selection
   behavior?

This section defines the target contract for registry modules. Existing schema,
validator, and module records must be migrated to this contract before the
Composer treats SOTA 2026 registry evidence as complete.

### Provenance

Every active module must define a `provenance` object with explicit requirement
ownership and source evidence:

```json
{
  "provenance": {
    "owner": {
      "type": "person",
      "name": "Module Owner"
    },
    "problem_statement": "The concrete task or platform problem this module solves.",
    "acceptance_criteria": [
      "A measurable condition that proves the module is needed and works."
    ],
    "source_of_truth": [
      {
        "type": "repo_path",
        "ref": "docs/policies/module-contracts.md",
        "reason": "Durable policy contract for module selection behavior."
      }
    ],
    "rationale": "Why this module should be directly selectable or dependency-only.",
    "requirement_id": "REQ-SCAS-REGISTRY-EXAMPLE"
  }
}
```

`owner` identifies a responsible person, not a generic team alias. The owner is
accountable for changing the requirement and for accepting deprecation,
merge, or deletion decisions.

`problem_statement` states the task gap or platform risk. It must not repeat the
module description.

`acceptance_criteria` is a non-empty list of measurable criteria. Criteria must
be testable by schema validation, registry validation, runtime tests, fixture
evidence, documentation review, or a named release gate.

`source_of_truth` is a non-empty list of durable references. Production modules
must include at least one `repo_path` entry. Repository paths are relative to
the repository root and must resolve to existing files. Notion pages, issues,
external standards, or vendor docs can provide context, but they cannot be the
only source of truth for executable registry behavior.

`rationale` explains the module's selection boundary. It must say why the
module is `direct` or `dependency_only`.

`requirement_id` is optional during early migration and should become stable
when a module maps to an ADR, policy requirement, tenant requirement, or release
gate.

### Selection Modes

`selection.mode` is required and is a closed enum:

| Mode | Meaning | Valid when |
| --- | --- | --- |
| `direct` | The module can be selected from task analysis and scored against task signals. | The module has a task-facing capability, non-empty provenance, direct scoring metadata, and positive plus negative selection fixtures. |
| `dependency_only` | The module cannot be selected from task analysis alone. It can only be included because a directly selected module depends on it. | The module represents a required tool, scope, policy, validator, context, or support capability and has dependency-inclusion plus no-direct-selection evidence. |

Unknown modes fail closed. `legacy`, `implicit`, `always_on`, or omitted modes
are not valid production states. Deprecated, disabled, or postponed modules must
not use a selection mode to remain selectable.

For `direct` modules, `selection.base_score` and
`selection.score_modifiers` remain required. A direct module must have at least
one positive score modifier and one negative or exclusion signal so the Composer
can prove both selection and rejection behavior.

For `dependency_only` modules, direct scoring fields are not allowed in the
target schema. The module may keep dependency metadata and policy bindings, but
it must not define `base_score`, direct scoring modifiers, direct triggers, or
task phrases that would let the Composer select it from the task envelope
alone. During migration, validators should treat any non-zero direct score or
direct-selection fixture on a `dependency_only` module as a contract failure.

### Fixture Evidence

Fixture evidence must use real registry fixtures, not synthetic prose. Every
fixture path must exist and must be listed under `tests.fixtures` or a typed
fixture-evidence object introduced by the schema migration.

Direct modules must provide:

- Positive selection evidence: at least one fixture where task signals select
  the module above threshold after policy filtering.
- Negative selection evidence: at least one fixture where similar or tempting
  task signals do not select the module because of missing inputs, excluded
  domain, risk mismatch, negative phrases, policy denial, or lower-ranked fit.

Dependency-only modules must provide:

- Dependency inclusion evidence: at least one fixture where a valid directly
  selected module includes the dependency through graph validation.
- No-direct-selection evidence: at least one fixture where task signals that
  mention the dependency's capability do not select it directly.

Evidence fixtures must record the selected module set, rejected module set,
matched signals, negative signals, policy result, graph-validation result, and
the reason the expectation is correct. Raw runtime traces, provider outputs,
customer data, and secrets are not acceptable fixture evidence.

### Schema Acceptance Rules

The module schema migration must enforce these acceptance rules:

- `provenance` is required for every `active`, `deprecated`, or production
  allowlisted module.
- `provenance.owner.type` must be `person`, and `provenance.owner.name` must be
  non-empty.
- `provenance.problem_statement`, `provenance.acceptance_criteria`,
  `provenance.source_of_truth`, and `provenance.rationale` must be non-empty.
- `selection.mode` is required and limited to `direct` or `dependency_only`.
- `direct` selection requires scoring metadata, task-signal evidence, and
  positive plus negative fixture evidence.
- `dependency_only` selection forbids direct scoring metadata and requires
  dependency-inclusion plus no-direct-selection fixture evidence.
- `tests.fixtures` or the future typed evidence field must be non-empty for
  active modules.
- `additionalProperties` must remain closed for new contract objects so
  unsupported provenance or evidence fields cannot bypass review.

### Validator Acceptance Rules

The registry validator must fail closed when:

- required provenance is missing or incomplete,
- a `repo_path` source of truth does not resolve under the repository root,
- a production module has no repository source of truth,
- a fixture path is missing, points outside the repository, or is not referenced
  by the module's evidence contract,
- a `direct` module lacks both positive and negative selection evidence,
- a `dependency_only` module has direct scoring metadata or lacks
  dependency-inclusion and no-direct-selection evidence,
- selected and rejected module sets in fixture evidence do not match the
  registry scorer, policy filter, and graph validator output,
- an unknown selection mode, unknown source type, or unknown evidence type is
  encountered.

The validator may warn during an explicit migration phase, but production
validation must treat the same conditions as hard failures.

### Classification Rubric

Use this rubric before backfilling or deleting modules:

| Classification | Use when | Required action |
| --- | --- | --- |
| Keep active | The module solves a current task-facing requirement and has direct fixture evidence. | Migrate as `direct`, add provenance, and keep scoring metadata. |
| Dependency-only | The module is needed only because another selected module requires it. | Migrate as `dependency_only`, remove direct scoring, and add dependency evidence. |
| Postpone | The requirement is plausible but not needed for the current release or lacks evidence. | Keep out of production environments until provenance and fixtures exist. |
| Delete | No owner, source of truth, acceptance criteria, or consuming dependency exists. | Remove the module and update dependents or fixtures. |
| Merge | Two modules represent the same requirement or capability boundary. | Keep one owner and source of truth, migrate evidence to the survivor, and remove the duplicate. |

### Implementation Handoff

The parent implementation task must update, at minimum:

- `schemas/module.schema.json` with provenance, `selection.mode`, and evidence
  constraints.
- `scripts/registry/validate_registry.py` with source-of-truth path checks,
  fixture existence checks, mode-specific scoring checks, and fail-closed
  evidence validation.
- `registry/modules/**/module.json` records with real provenance and fixture
  evidence.
- Registry fixture files with positive, negative, dependency-inclusion, and
  no-direct-selection cases.
- CI or local gates so schema validation and registry validation enforce the
  migrated contract.

Documentation is complete only when this policy, registry reference docs, and
the implementation tests describe the same contract.

### Tests

`tests` - Typed test references. `contract` contains schema-backed contract test
fixtures, `runtime` contains pytest node IDs or named runtime validation cases,
and `fixtures` contains example fixture paths. Contract and runtime entries are
gates; fixtures are consistency checks.

## Selection Flow

The Composer applies the following steps in order. A module is rejected as soon
as any step fails.

```text
1. discover   - filter by kind, capability_class, domain_tags, task_signals
2. score      - apply base_score and score_modifiers; reject below threshold
3. filter     - evaluate policies; deny overrides any score
4. resolve    - load pinned version and dependency graph
5. validate   - check graph for missing references, conflicts, unauthorized transitive capabilities
```

A module that scores highly can still be denied at the filter step. This is
intentional. Policies are a separate enforcement layer, not an input to scoring.

## Complete Example

```json
{
  "$schema": "../../../../schemas/module.schema.json",
  "schema_version": "0.1.0",
  "name": "git-diff-analysis",
  "version": "0.1.0",
  "kind": "skill",
  "status": "active",
  "description": "Analyze git diffs for behavioral changes, regressions, and review-relevant risks.",
  "runtime_role": "runtime",
  "runtime_roles": {
    "default": "runtime",
    "allowed": ["runtime"]
  },
  "capability_class": "analysis",
  "environments": ["dev", "staging", "prod"],
  "entrypoint": {
    "type": "skill_folder",
    "path": "SKILL.md"
  },
  "runtime_contract": {
    "profile_sealable": true,
    "requires_version_pin": true,
    "requires_handler_binding": true
  },
  "domain_tags": [
    "software-engineering",
    "git",
    "code-review"
  ],
  "task_signals": {
    "task_types": ["code-review"],
    "risk_levels": ["low", "medium"],
    "domains": ["software-engineering", "git"],
    "required_inputs": ["repository", "diff"],
    "phrases": ["review", "diff", "commit", "pull request"],
    "negative_phrases": ["deploy", "apply changes", "delete"]
  },
  "triggers": ["review", "diff", "commit", "pull request"],
  "inputs": ["repository", "diff"],
  "outputs": ["findings", "review-summary"],
  "required_tools": ["git-read", "filesystem-read"],
  "optional_tools": ["test-runner"],
  "knowledge_scopes": ["architecture-docs", "coding-guidelines"],
  "data_scopes": ["repository-readonly"],
  "policies": ["no-destructive-commands", "require-file-references"],
  "validators": ["review-findings-contract"],
  "provenance": {
    "owner": {
      "type": "person",
      "name": "Module Owner"
    },
    "problem_statement": "Code-review tasks need a bounded review skill that reads repository diffs without gaining mutation capability.",
    "acceptance_criteria": [
      "The module is selected for code-review tasks with repository and diff inputs.",
      "The module is rejected or ranked away for deployment and mutation requests.",
      "Graph validation includes only the declared tools, scopes, policies, and validators."
    ],
    "source_of_truth": [
      {
        "type": "repo_path",
        "ref": "docs/policies/module-contracts.md",
        "reason": "Defines the governed module contract."
      },
      {
        "type": "repo_path",
        "ref": "registry/modules/skills/git-diff-analysis/module.json",
        "reason": "Durable machine-readable module definition."
      }
    ],
    "rationale": "This module is directly selectable because code-review task signals map to its primary capability.",
    "requirement_id": "REQ-SCAS-REGISTRY-GIT_DIFF_ANALYSIS"
  },
  "selection": {
    "mode": "direct",
    "base_score": 0.74,
    "score_modifiers": [
      {
        "signal": "task_type:code-review",
        "weight": 0.18,
        "reason": "Code review tasks require diff-oriented change analysis."
      },
      {
        "signal": "input:diff",
        "weight": 0.08,
        "reason": "The module is more reliable when a concrete diff is available."
      },
      {
        "signal": "phrase:deploy",
        "weight": -0.25,
        "reason": "Deployment requests should not select review-only analysis as an execution capability."
      }
    ],
    "requires_all_policies": true
  },
  "selection_evidence": {
    "positive_selection": [
      {
        "fixture": "examples/registry/selection-evidence/git-diff-analysis.json",
        "expectation": "selected",
        "reason": "The positive fixture contains code-review task signals with repository and diff inputs."
      }
    ],
    "negative_selection": [
      {
        "fixture": "examples/registry/selection-evidence/git-diff-analysis.json",
        "expectation": "rejected",
        "reason": "The negative fixture contains deployment language that should not select review-only capability."
      }
    ]
  },
  "tests": {
    "contract": [],
    "runtime": [
      "detects-risky-diff-fixture",
      "requires-file-line-references"
    ],
    "fixtures": ["examples/registry/selection-evidence/git-diff-analysis.json"]
  }
}
```

## Validation

Validate a module definition against the schema before committing:

```bash
python -m pytest tests/test_contract_schemas.py -k module
python scripts/registry/validate_registry.py --phase 3a
python scripts/registry/validate_registry.py --phase 3b
```

The CI pipeline runs this check on every push. A module that does not pass
schema validation will not be accepted into the registry.

## Anti-Patterns

- Define `triggers` only and omit `task_signals` - triggers are weak hints, not
  the scoring surface.
- Treat support modules as `direct` because they are useful dependencies -
  tools, scopes, policies, and validators should normally be `dependency_only`.
- Set `base_score` to `1.0` - this bypasses meaningful scoring and pushes every
  Composer toward the module regardless of task fit.
- Omit `negative_phrases` - without them, the module can be selected for tasks
  where it should be denied.
- Put `base_score` or `score_modifiers` on a `dependency_only` module - this
  reopens direct selection.
- List every tool in `required_tools` as a precaution - only list tools the
  module cannot function without.
- Set `requires_all_policies: false` without a documented reason - this weakens
  the policy enforcement guarantee.
- Rely on `description` for selection logic - description is for humans, not the
  Composer.
- Skip `tests` - untested modules cannot be trusted in a registry that gates on
  validation.
- Put active modules under `examples/` - examples are fixtures only, not source
  of truth.
