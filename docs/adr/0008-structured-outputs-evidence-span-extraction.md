# ADR 0008: Structured Outputs for EvidenceSpan Extraction

## Status

Deferred for runtime adoption.

## Context

ITG-07 evaluated whether provider-level Structured Outputs should be used before
local validation for `EvidenceSpan` extraction. Official OpenAI documentation
states that Structured Outputs can enforce schema-shaped JSON output, but strict
mode supports only a subset of JSON Schema and provider output remains model
extraction output, not an authorization decision.

The authoritative local contract remains
`schemas/transition-evidence.schema.json`, validated by
`scripts/runtime/validate_transition_evidence.py`. Critical signal coverage
remains deterministic through `scripts/runtime/scan_transition_signals.py`.

## Decision

Do not adopt Structured Outputs directly for production transition authority at
this stage.

SCAS may later add a reduced provider-facing extraction schema as an
optimization, but only if:

- deterministic scanners remain authoritative,
- local schema validation remains authoritative,
- hash and offset verification still run locally,
- scanner coverage remains required,
- provider errors, refusals, unsupported schema errors, or incomplete outputs
  fail closed,
- provider output cannot grant tools, scopes, policies, validators, or runtime
  authority.

The versioned decision record is
`policies/runtime/structured-evidence-extraction-decision.json`.

## Consequences

Structured Outputs is treated as a format-quality optimization, not as a safety
boundary. It can reduce malformed JSON and missing required fields, but it does
not replace semantic evidence coverage, local validation, or the
`unknown behaves like not authorized` policy.

Future work may introduce a provider-subset extraction schema and latency
benchmarks. That work must not remove the local TransitionEvidence validator or
scanner coverage gate.
