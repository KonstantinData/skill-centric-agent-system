# Liquisto Tenant Workbench

Tenant-specific Next.js workbench for configured Liquisto runtime workflows on
`liquisto.cloud`.

The app must only expose surfaces backed by actual Liquisto tenant
configuration, role grants, validators, or deployment evidence. Do not add
conceptual product areas, demo metrics, or placeholder workflows.

The current visible surface is limited to:

- Research backed by `research-intake`, `research-context-synthesis`, and
  `research-output-contract`
- Admin backed by `tenant-admin`, `user-permission-validator`, and
  `admin-action-validator`
- Isolation evidence for the Liquisto tenant boundary
- Cloudflare Access identity headers for user context
- Cloudflare Control Plane / Hetzner Runtime Plane boundaries as visible product
  constraints

## Design Surface

The first Cockpit screen is a dense runtime configuration workspace, not a marketing page.
It includes:

- Command Center for tenant authority, research scope, and isolation evidence
- execution phase rail for tenant resolution, scope filtering, profile sealing,
  workflow execution, and evidence verification
- configured surfaces for Research, Admin, and Isolation Gate
- system health tiles for Control API, Research, Admin, and Isolation
- configured runtime paths with role and validator evidence
- runtime configuration cards instead of fake agent run cards
- Evidence Timeline for audit-friendly review
- Runtime Evidence table for configuration and isolation signals

The current implementation uses static contract data copied from tenant
fixtures and deployment gates. Runtime mutation paths must be wired only after
the Liquisto Control API and Hetzner runtime endpoints are explicitly scoped and
validated.

## Local Validation

```powershell
npm --prefix apps/liquisto-workbench run lint
npm --prefix apps/liquisto-workbench run build
```
