# Contracts

## Purpose

This file is a meta-index for contract ownership and navigation.
It does not define detailed runtime behavior.

## Normative Contract Sources

Use these files as the authoritative contract documents:

- Runtime behavior, profile enforcement, write gating, recomposition, runtime
  failure semantics, observability, retention:
  `docs/policies/runtime-contract.md`
- Multi-turn intent transitions, capability deltas, evidence spans, unknown
  handling, clarification gates, and transition audit evidence:
  `docs/policies/intent-transition-gates.md`
- Selectable module field semantics and metadata rules:
  `docs/policies/module-contracts.md`
- Machine-readable contracts and validation schemas:
  `schemas/`
- Learned-context authority boundaries and semantic drift guards:
  `docs/policies/semantic-drift-guard.md`

`docs/policies/contracts.md` is intentionally high-level and must only define
cross-document boundaries and invariants.

## Composition Boundary

Profile composition must always pass through this pipeline:

1. task analysis
2. registry discovery
3. scoring
4. policy filtering
5. dependency graph validation
6. runtime profile validation

The runtime must not self-grant tools, scopes, policies, validators, skills, or
instructions outside this control path.

## Runtime Authority Rule

If `contracts.md` and `runtime-contract.md` overlap, the normative source is
always `runtime-contract.md`.
`contracts.md` must be updated to remove overlap instead of duplicating runtime
rules.

## Related Policy References

- Environment and secret naming norms:
  `docs/policies/environment-separation.md`
- Data-plane ownership and storage boundaries:
  `docs/policies/infrastructure-boundary.md`
- Formal profile-sealing invariant catalog:
  `docs/policies/formal-safety-invariants.md`
- Evidence-based intent transition gates:
  `docs/policies/intent-transition-gates.md`
- Machine-readable invariant-to-change-type validator mapping:
  `docs/policies/formal-safety-change-type-matrix.md`
- Learned-context authority boundary and contrastive drift guard:
  `docs/policies/semantic-drift-guard.md`
- Production release gates and evidence requirements:
  `docs/policies/production-readiness.md`

