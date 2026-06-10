# ADR-0010: Policy Denial Ledger And Scope Closure

## Status

Accepted

## Date

2026-06-10

## Context

Runtime policy denials can repeat when the same task, profile, principal, or
scope request is retried. Without a durable denial ledger, the runtime can waste
cycles rediscovering known denials or trigger redundant recomposition attempts.
At the same time, denial evidence must not become an authority source. Scope
closure metadata can identify already-approved reachability, but it must never
encode semantic lesson authority or grant permissions.

## Decision

SCAS records policy denials in a versioned, metadata-only Policy Denial Ledger.
Each denial has a deterministic fingerprint over the profile, principal,
predicate, requested authority, policy, and closure version. A request can be
short-circuited when an active record has the same fingerprint.

SCAS also permits scope/policy closure tables for approved reachability among
data, knowledge, and memory scopes. Closure entries are non-authoritative and
`reachability_only`; they can prove that a requested child scope is already
subsumed by an active denied ancestor scope under the same policy, principal,
profile, and closure version. They cannot grant scopes, tools, policies,
validators, budgets, failure behavior, or runtime profile changes.

## Consequences

- Denial deduplication is an enforcement optimization, not a learning or
  promotion path.
- Denial records use `authority_effect=deny_only` and
  `non_authoritative=true`.
- Closure entries use `authority_effect=reachability_only` and
  `non_authoritative=true`.
- Stale closure versions do not subsume new requests.
- Scope closure is separate from the lesson relationship graph; lessons cannot
  inherit permissions through closure metadata.

## Target Artifacts

- `src/skill_centric_agent_system/runtime/policy_denials.py`
- `schemas/policy-denial-ledger.schema.json`
- `docs/reference/memory-architecture.md`
- `docs/policies/runtime-contract.md`
- `docs/roadmap/memory-architecture-backlog.md`
