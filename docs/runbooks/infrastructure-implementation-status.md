# Infrastructure Implementation Status

## Purpose

This runbook tracks implementation status and sequencing for infrastructure work.
Normative data-plane boundaries remain in
`docs/policies/infrastructure-boundary.md`.

## Implemented

- ADR-0004 records the Cloudflare/Hetzner boundary.
- ADR-0005 records the Runtime Flight Recorder decision.
- Cloudflare D1 schema contract and migrations exist.
- Hetzner runtime storage schema contract, PostgreSQL migration, and bootstrap
  script exist.
- Wrangler configuration exists for the dev Control API Worker.
- `POST /composition/context` is implemented in `workers/control-api/`.
- Control API bearer authentication and endpoint-scoped authorization are
  implemented.
- Runtime entry point, profile enforcement, tool gateway hardening, and
  validator framework are implemented.
- Runtime context retrieval via `POST /retrieval/context` is implemented with
  scope validation.
- Controlled recomposition continuation path is implemented.
- Runtime retention planning, cleanup execution, and dry-run-first automation
  are implemented.
- Knowledge/memory ingestion, queue-backed embedding updates, and Vectorize
  post-validation path are implemented.
- Production skill handler runtime first slice and handler coverage manifest
  gates are implemented.
- Production release evidence workflow exists with external run metadata
  validation.

## Not Yet Implemented

- Provision and validation of staging/prod Cloudflare and Hetzner resources
  from the environment manifest.
- Final production certification run against staging and production live
  infrastructure.
- Broader production skill handler coverage beyond current manifest-covered
  fixture set.

## Current Next Order

1. Provision and validate staging/prod resources from the environment manifest.
2. Expand production skill handler coverage.
3. Run final production-readiness certification after live infrastructure and
   coverage gates are complete.
