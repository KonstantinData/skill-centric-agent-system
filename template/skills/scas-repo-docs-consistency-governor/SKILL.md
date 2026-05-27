---
name: scas-repo-docs-consistency-governor
description: Ensure SCAS repository documentation stays consistent with code, tests, contracts, and governance changes before commit and PR merge.
---

# SCAS Repo Docs Consistency Governor

## Outcome

Prevent documentation drift in SCAS.

## Mandatory Gate

Run this gate:
- before commit,
- before PR creation/update,
- before merge readiness confirmation.

## Check Scope

- `README.md`
- `docs/`
- `schemas/`
- `policies/`
- `migrations/`
- runtime/composition contract docs and runbooks

## Decision

- If code behavior changed, either update docs or record explicit rationale why docs are unchanged.
- Missing docs updates must be handled before completion.