# Intent Transition Gates

## Purpose

This policy defines how SCAS handles multi-turn intent changes that may widen
runtime authority. It covers the boundary between a previous task/profile and a
new task envelope. The goal is to prevent dialog state, compressed context, or
ambiguous references from silently granting write-capable or higher-risk
capabilities.

This policy is normative for intent-transition decisions. The detailed runtime
execution contract remains `docs/policies/runtime-contract.md`.

## Transition Boundary

Each user turn that introduces a materially different action request must create
a new task envelope. The runtime must not mutate an active profile to add
skills, tools, data scopes, knowledge scopes, memory scopes, policies,
validators, or broader execution limits.

Capability escalation requires recomposition through the normal control path:

```text
Task Intake
-> Task Analyzer
-> Transition Gate
-> Agent Composer
-> Policy Filtering
-> Dependency Graph Validation
-> Runtime Profile Validation
```

If a previous profile was `research`, read-only, non-repository-bound, or
human-review-required, a later write-capable request does not inherit authority
from the earlier turn. It must present its own evidence.

## Transition Evidence Contract

Transition decisions must be based on a compact, machine-readable evidence
object rather than a free-form summary of the full dialog. The evidence object
must include:

- `previous_task_type`,
- `current_task_type`,
- `previous_profile_id` when a previous profile exists,
- `previous_profile_capabilities`,
- `current_requested_capabilities`,
- `capability_delta`,
- `repository_bound`,
- `explicit_write_intent`,
- `explicit_destructive_intent`,
- `mentioned_paths`,
- `protected_path_reference`,
- `classification_confidence`,
- `requires_recomposition`,
- `requires_human_review`,
- `transition_reason`.

Critical fields must be backed by evidence spans or set to `unknown`.
The machine-readable schema is
`schemas/transition-evidence.schema.json`; the repository validator is
`python scripts/runtime/validate_transition_evidence.py --check`.
Deterministic critical-signal scanners are implemented in
`scripts/runtime/scan_transition_signals.py` and must run before the evidence
validator decides whether extracted evidence covers all critical scanner
findings.

## Evidence Spans

An `EvidenceSpan` references exact text in an immutable raw-turn artifact. It is
not a paraphrase. Each span must include:

- `artifact_id`,
- `artifact_hash`,
- `span`,
- `offset_start`,
- `offset_end`,
- scanner or extractor version metadata.

Validators must be able to verify that:

```text
raw_artifact[offset_start:offset_end] == span
```

If the raw artifact is unavailable, truncated, hash-mismatched, or only
partially scanned, the transition gate must fail closed for capability
escalation.

## Unknown Handling

`unknown` is a first-class state. It must not be coerced to `true`, `false`, or
an inferred default.

For capability escalation, `unknown` behaves like not authorized. The gate must
request clarification, require human review, or deny the transition when any of
these values are unknown:

- repository binding,
- explicit write intent,
- protected-path reference,
- destructive intent,
- scan coverage,
- raw-artifact hash verification,
- previous profile authority.

## Capability Delta Rules

The gate evaluates capability deltas, not skill-to-skill pairs. At minimum:

- `research -> research` is allowed when no new write, repository, protected
  path, production, or destructive capability is requested.
- `research -> task-execution` requires explicit write intent, repository
  binding, transition evidence, and recomposition.
- `read-only -> repo-write` requires explicit write intent, repository binding,
  evidence spans, and recomposition.
- `repo-write -> protected-path-write` requires protected-path evidence,
  governance-aware review gates, and recomposition.
- `protected-path-write -> production-change` requires production-readiness
  gates, required checks, and applicable approval gates.
- Any transition involving secrets, credentials, destructive operations, or
  unknown tools fails closed unless a more specific policy explicitly allows it.

The gate must evaluate the delta between the previous profile authority and the
new requested authority. A target skill is not safe merely because it has been
used before; the requested capability delta still controls.

## Clarification Gate

The gate must request clarification instead of composing a broader profile when
the current turn asks for write-capable behavior but lacks sufficient binding
evidence.

Examples:

- A previous turn was `research`, not repository-bound, and the current turn says
  `Apply the fix`.
- The current turn says `change that file` but no file can be resolved from
  validated evidence.
- A path-like token is present in raw text but absent from `mentioned_paths`.
- Scanner coverage is partial for a long turn.

Clarification must ask for the missing binding, not suggest that the system has
inferred it.

## Human Review Gate

Human review is required when the transition evidence is contradictory,
destructive, production-affecting, protected-path-affecting without complete
evidence, or cannot be made safe through clarification alone.

A human-review-required transition must not select specialized write-capable
skills, tools, knowledge scopes, data scopes, or memory scopes before approval.
Any approved continuation must create a new composed profile through the same
control path.

## Structured Extraction Boundary

Model-assisted extraction may be used only to produce typed transition evidence
that is validated before routing. Strict provider-level structured outputs can
reduce malformed extraction output, but they do not replace deterministic
scanners, raw-artifact hash checks, or fail-closed validation.

Critical scanner findings must be covered by extracted evidence:

```text
scanner_critical_signals <= extracted_critical_signals
```

If a scanner finds a critical path, write intent, destructive intent,
repository reference, branch, PR, commit, or protected-path reference that the
extractor omits, the evidence object is incomplete and must not authorize
capability escalation.

## Audit Requirements

Every transition gate decision must emit structured evidence that records:

- decision,
- previous and current task types,
- capability delta,
- required gates,
- missing evidence,
- clarification or review requirement,
- evidence span references,
- scanner coverage,
- raw-artifact verification status.

This audit record is the feedback object for future transition-evaluation
fixtures and shadow evaluation. It must avoid raw secrets, raw tool outputs, and
unredacted confidential data.
