# Module Contracts

Use this reference when defining selectable modules. All fields must conform to
`schemas/module.schema.json`. A module that fails schema validation will be
rejected by the registry before it can be selected.

## Required Metadata

```json
{
  "name": "module-name",
  "version": "0.1.0",
  "kind": "skill|instruction|tool|knowledge_scope|data_scope|policy|validator|memory_scope",
  "description": "What this module provides and when to select it.",
  "capability_class": "analysis|planning|execution|retrieval|validation|policy|instruction|tool_access|knowledge_access|data_access|memory_access|context",
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
  "selection": {
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
  "tests": ["fixture-name"]
}
```

## Field Reference

### Identity

`name` - Lowercase, hyphen-separated identifier. Must be unique within the
registry. Pattern: `^[a-z][a-z0-9-]*$`.

`version` - Semantic version (`MAJOR.MINOR.PATCH`). Increment when the module
contract changes. The registry uses this for version pinning in runtime profiles.

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

`data_scopes` - Data access scopes. Validated against the profile's
`data_scopes` allowlist and the principal's authorization claims.

`policies` - Policies that apply when this module is active. Referenced by name;
must exist in the policy registry.

`validators` - Validators that check this module's output contract. Referenced
by name; must exist in the validator registry.

### Selection Scoring

`selection` controls how the Composer scores the module against task signals.

`selection.base_score` - Starting score between `0.0` and `1.0` before any
modifiers are applied. Represents the module's general fit absent specific
evidence.

`selection.score_modifiers` - Ordered list of signal-weight pairs applied on
top of the base score. Each modifier has:

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

### Tests

`tests` - Names of test fixtures or validation cases that verify the module
behaves as specified. At minimum, include one positive fixture where the module
should be selected and one negative fixture where it should not.

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
  "name": "git-diff-analysis",
  "version": "0.1.0",
  "kind": "skill",
  "description": "Analyze git diffs for behavioral changes, regressions, and review-relevant risks.",
  "capability_class": "analysis",
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
  "selection": {
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
  "tests": [
    "detects-risky-diff-fixture",
    "requires-file-line-references"
  ]
}
```

## Validation

Validate a module definition against the schema before committing:

```bash
python -m pytest tests/test_contract_schemas.py -k module
```

The CI pipeline runs this check on every push. A module that does not pass
schema validation will not be accepted into the registry.

## Anti-Patterns

- Define `triggers` only and omit `task_signals` - triggers are weak hints, not
  the scoring surface.
- Set `base_score` to `1.0` - this bypasses meaningful scoring and forces every
  Composer to select the module regardless of task fit.
- Omit `negative_phrases` - without them, the module can be selected for tasks
  where it should be denied.
- List every tool in `required_tools` as a precaution - only list tools the
  module cannot function without.
- Set `requires_all_policies: false` without a documented reason - this weakens
  the policy enforcement guarantee.
- Rely on `description` for selection logic - description is for humans, not the
  Composer.
- Skip `tests` - untested modules cannot be trusted in a registry that gates on
  validation.
