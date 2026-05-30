# Formal Safety Change-Type Matrix

## Purpose

This document links change types to mandatory invariants and validator gates.
The machine-readable source is
`policies/runtime/formal-safety-change-type-matrix.json`.

## Change-Type Matrix Contract

- Schema:
  `schemas/formal-safety-change-type-matrix.schema.json`
- Policy:
  `policies/runtime/formal-safety-change-type-matrix.json`
- Invariant source:
  `docs/policies/formal-safety-invariants.md`
- Validation command:
  `python scripts/runtime/validate_formal_safety_change_type_matrix.py`

## Covered Change Types

1. `contract-change`
2. `runtime-logic`
3. `governance-doc`
4. `security-gate`
5. `scope-or-policy-change`

## Enforcement Rule

For each change type entry:

1. all listed invariants are mandatory,
2. all listed runtime validators are mandatory,
3. all listed repository validators are mandatory, and
4. all listed CI checks are blocking.
