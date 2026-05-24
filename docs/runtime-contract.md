# Runtime Contract

## Purpose

This document defines the generic Runtime Contract for the productive Runtime
Phase. It is task-neutral by design. The runtime must not encode a fixed agent
role such as reviewer, researcher, or task executor. Those are validation
scenarios produced by task intake, analyzer signals, composition context, and
profile selection.

## Contract Surfaces

The productive runtime path is:

```text
Task Envelope
-> Task Analyzer Output
-> Cloudflare Composition Context
-> Runtime Agent Profile
-> Runtime Run
-> Runtime Steps
-> Runtime Events and Checkpoints
-> Tool Invocations
-> Validation Results
-> Runtime Result
```

Every surface must be explicit, serializable, and reproducible. The runtime may
request recomposition, but it must never mutate the active profile to grant a
new capability.

## Task Envelope

The Task Envelope is the normalized runtime input. It must contain:

- stable task ID,
- objective,
- submitter principal,
- environment,
- available inputs and attachments,
- explicit constraints,
- repository or workspace context when relevant,
- privacy and risk hints.

Task-specific payloads are allowed, but they must remain data. They must not
grant capabilities directly.

## Analyzer Output

Analyzer Output must contain:

- `task_type`,
- `risk_level`,
- `domains`,
- `required_inputs`,
- `available_inputs`,
- `capability_hints`,
- `constraints`,
- `missing_information`,
- `auth_claims`,
- `classification_confidence`,
- `classification_reasons`,
- `ambiguous_task_types`,
- `requires_human_review`.

If required information is missing, the Composer must fail closed or request
clarification instead of composing a broad profile.
If several specialized task classes match, the Analyzer must fall back to
`general-task` with low confidence and mark the task for review. The runtime
must not dispatch to a specialized strategy from ambiguous analyzer output.

## Runtime Agent Profile

The Runtime Agent Profile is the immutable execution contract. It must conform
to `schemas/runtime-profile.schema.json` and include:

- profile version and generation,
- parent profile and recomposition reason,
- auth context,
- selected instructions, skills, tools, knowledge scopes, data scopes, memory
  scopes, policies, and validators,
- exact module version pins,
- execution limits,
- failure policy,
- observability settings.

The runtime must enforce the profile at every access boundary.

## Runtime Profile Enforcement

The runtime must enforce the active profile as executable policy, not as
guidance text.

Hard enforcement covers:

- selected skills,
- selected tools,
- selected knowledge scopes,
- selected data scopes,
- selected memory scopes,
- `limits.max_tool_calls`,
- `limits.max_tokens`,
- `limits.max_duration_seconds`,
- `limits.max_data_reads`,
- `limits.max_memory_ops`,
- `limits.max_recompositions`,
- module version pins for every selected module,
- exact executable handler binding for every selected skill that has a runtime
  handler.

Denied access must emit a Flight Recorder event with a constrained stop reason.
The runtime must fail closed when a limit is exceeded or an unselected scope is
requested. The active profile must never be mutated to resolve the denial.

## Skill Handler Runtime

Executable skills live under the Python runtime implementation path:

```text
src/skill_centric_agent_system/runtime/skill_handlers.py
```

The first production handler slice binds executable code to selected skill
metadata by exact `skill name + module_versions[skill]`. The runtime does not
accept free-form handler entrypoints from task input, prompt text, or runtime
state. A selected skill may execute only when:

- the skill appears in `profile.skills`,
- the skill has an exact version pin in `profile.module_versions`,
- the runtime has a registered executable handler for that exact skill/version,
- the handler emits actions that still pass Tool Gateway enforcement.

Unknown selected skills and mismatched handler versions are policy denials and
fail closed before tool execution. The Planner records the resolved
`skill_handlers` binding in its checkpoint so release evidence can prove which
metadata-backed code path was used.

The repository also maintains a deterministic coverage manifest:

```text
examples/runtime/skill-handler-coverage.json
```

It is generated and checked by:

```text
python scripts/runtime/skill_handler_coverage.py --check
```

The manifest maps each production-required skill module fixture to the exact
handler ID, runtime implementation path, strategy, output contract, module
tests, runtime tests, and handler lifecycle status. CI fails if a
production-required skill lacks a matching executable handler or if the
committed manifest is stale.

Handler upgrades and rollback must follow
`docs/skill-handler-version-policy.md` and the machine-readable policy in
`policies/runtime/skill-handler-version-policy.json`. Upgrades register new
handler versions side by side with previous versions. Rollback composes a new
runtime profile with the previous version pin instead of mutating the active
profile.

Task class still shapes output validation and task-specific result formatting,
but it is no longer the authority that grants executable behavior. Runtime
capabilities continue to come from the immutable profile and the exact
version-pinned skill handler registry.

## Tool Gateway

All tool execution must pass through the Tool Gateway. A productive Tool Gateway
must enforce:

- profile-selected tool allowlists,
- profile-selected data scopes required by each tool,
- per-tool risk gating against the profile risk level,
- fixed command adapters instead of free shell command execution,
- adapter-level timeouts,
- adapter-level output limits,
- allowed and denied access audit events,
- structured tool failure details.

Large tool input/output payloads must be written as artifacts and referenced by
URI from runtime events and `tool_invocations`.
When a single string payload exceeds the artifact store inline threshold, it
must be split into text chunks with a manifest URI stored in the parent JSON
artifact.

## Controlled Write Path

Write-capable runtime execution is disabled unless the active profile selects a
write tool, the matching write data scope, and the required write policy. The
first controlled write adapter is:

```text
filesystem-write
```

It accepts only structured `write_text_file` action plans. It does not execute
free-form shell strings, command arrays, or task-provided scripts.

`filesystem-write` requires:

- `tools` contains `filesystem-write`,
- `data_scopes` contains `repository-write`,
- `policies` contains `write-approval-required`,
- `risk_level` is at least `high`,
- the payload includes approval fields `approval_id`, `approved_by`,
  `approved_at`, and `policy_id`,
- the payload includes rollback metadata.

Dry-run planning is the default when the payload does not set boolean
`apply: true`; non-boolean apply values are rejected. Paths must be relative to
the repository root. New files require rollback strategy `delete_created_file`;
overwrites require rollback strategy `restore_previous_content`. The first
slice records rollback metadata and content hashes, not raw previous content,
to avoid leaking secrets through audit artifacts.

The machine-readable policy is:

```text
policies/runtime/write-approval-required.json
```

The policy contract is:

```text
schemas/write-approval-policy.schema.json
```

The example profile and action plan are:

```text
examples/profiles/controlled-write-profile.json
examples/runtime/controlled-write-action-plan.json
```

## Context Retrieval

The Context Manager must not read knowledge or memory stores directly. It must
build a bounded retrieval request from the active profile and submit it to the
Cloudflare Control API:

```text
POST /retrieval/context
```

The request may include only profile-selected knowledge and memory scopes. The
response must be checked before use; any returned scope outside the active
profile is a policy denial and must fail closed.

## Run Lifecycle

Runtime run statuses are:

- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`

Allowed status transitions:

```text
queued -> running
queued -> cancelled
running -> succeeded
running -> failed
running -> cancelled
running -> queued      # retry creates a new run; the original remains terminal
```

Retry must create a new run ID and preserve parent run traceability in the
runtime result or retry metadata. It must not reopen a terminal run in place.

## Step Lifecycle

Runtime step kinds are:

- `context`
- `planner`
- `executor`
- `validator`

Each step must write:

- stable ID,
- run ID,
- step index,
- kind,
- status,
- start and completion timestamps,
- stop reason,
- token budget and usage,
- idempotency key,
- attempt number.

## Stop Reasons

Stop reasons must be constrained to the runtime vocabulary in
`src/skill_centric_agent_system/runtime/models.py` and the Hetzner schema:

- completed
- max_tokens
- max_duration
- max_tool_calls
- max_data_reads
- max_memory_ops
- max_recompositions
- policy_denied
- validator_failed
- tool_error
- cancelled
- needs_recomposition
- composer_failure
- runtime_error

## Failure Semantics

The runtime fails closed for unsafe ambiguity.

- Composer failure: no runtime execution.
- Profile validation failure: no runtime execution.
- Policy denial: do not execute the denied capability.
- Budget exhaustion: stop according to profile failure policy.
- Tool failure: record event, persist invocation metadata, then fail or
  continue only if the validator/failure policy permits it.
- Validator failure: fail or request recomposition only when profile failure
  policy allows it.

## Validator Framework

The Validator phase must be driven by `profile.validators`. Each selected
validator must produce a `validation_results` row with:

- validator ID,
- status,
- findings artifact URI,
- creation timestamp.

Unknown validators fail closed. The runtime must not silently skip selected
validators, and it must not substitute a task-specific hardcoded validator for
the profile-selected validator set.

The first runtime output validators are task-class aware:

- `review-findings-contract` validates `code-review` output,
- `research-output-contract` validates `research` output,
- `task-execution-output-contract` validates `task-execution` output,
- `general-output-contract` validates `general-task` output.

Each validator checks the `runtime_output` object against the task class chosen
by the active profile. The machine-readable result schema is
`schemas/runtime-output.schema.json`.

## Recomposition

Recomposition is a controlled request to the Composer. It is allowed only when:

- active profile failure policy permits recomposition,
- `limits.max_recompositions` is not exhausted,
- the reason is one of the schema-defined `recomposition_reason` values.

The new profile must set:

- incremented `profile_generation`,
- `parent_profile_id`,
- `recomposition_reason`.

The new profile must also have a distinct profile ID for the new generation so
the parent and child profiles are reproducible independently.

The runtime must not self-grant tools, memory, data, knowledge, skills, or
validators.

When recomposition is needed, the runtime must emit `recomposition_requested`
with:

- task ID,
- parent profile ID,
- requested profile generation,
- schema-defined recomposition reason.

The current run must stop with `needs_recomposition`. A new profile must come
from the Composer; the runtime must not edit the active profile in place. When
continuation is enabled, the runtime starts a new run attempt from the
recomposed profile and records attempt run IDs and recomposed profile IDs in the
runtime result.

## Observability

Every productive run must emit Flight Recorder events and checkpoints to the
Hetzner Runtime Plane. Event payloads use artifact URIs, not inline JSON blobs.
The runtime must honor `observability.redact_sensitive_data` before writing
artifacts.
Run-local event indexes must be allocated atomically by the runtime storage
adapter. The runtime must not derive `event_index` by counting currently visible
events in a way that can race under parallel writers.

## Retention Cleanup

Runtime retention cleanup applies only to artifact files, not runtime metadata
rows, in the first cleanup slice.

The cleanup flow is:

```text
Runtime Plane recordset
-> RuntimeRetentionPlanner
-> RuntimeRetentionPlan
-> RuntimeRetentionExecutor
-> Cleanup report artifact
```

Retention cleanup must obey these rules:

- Dry-run is the default for apply operations.
- Destructive cleanup requires explicit confirmation.
- Only `hetzner://runtime/...` URIs under the configured artifact root can be
  resolved.
- Unknown URI schemes, parent traversal, absolute paths, and directories fail
  closed.
- Missing expired artifacts are reported as `missing` and skipped by default.
- Strict missing mode may return a cleanup error when consistency is more
  important than completing the cleanup pass.
- Cleanup reports are retained under their own `cleanup_report_artifact_days`
  policy so the cleanup mechanism does not create unbounded report artifacts.

## Runtime Result

The runtime result must contain:

- run ID,
- task ID,
- profile ID,
- final status,
- stop reason,
- response or validation failure summary,
- validation result references,
- artifact root URI,
- event/checkpoint references,
- recomposition or retry references when applicable.

The first generic runtime loop resolves deterministic executable handlers from
the active profile's selected skills:

- `git-diff-analysis@0.1.0`: read-only git and filesystem inspection,
- `research-context-synthesis@0.1.0`: profile-bounded retrieval synthesis,
- `task-execution-planning@0.1.0`: conservative read-only repository inspection,
- `general-task-summary@0.1.0`: bounded generic summary.

These handlers run inside the single runtime agent. They are not separate
agents and must not expand the active profile.
