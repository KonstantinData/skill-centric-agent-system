# Liquisto Tenant Workbench

Tenant-specific Next.js workbench for configured Liquisto runtime workflows on
`liquisto.cloud`.

The app must only expose surfaces backed by actual Liquisto tenant
configuration, role grants, validators, or deployment evidence. Do not add
conceptual product areas, demo metrics, or placeholder workflows.

`liquisto.cloud` is an application platform, not a documentation platform.
The Cockpit must stay focused on user actions and must not show audit evidence,
runtime configuration, validator details, deployment evidence, or governance
notes as page content.

The current visible workflow surface is limited to:

- Research backed by `research-intake`, `research-context-synthesis`, and
  `research-output-contract`
- Admin backed by `tenant-admin`, `user-permission-validator`, and
  `admin-action-validator`
- Cloudflare Access identity headers for user context
- Cloudflare Control Plane / Hetzner Runtime Plane boundaries as visible product
  constraints

## Design Surface

The first Cockpit screen is an application start surface. It includes:

- Command Center for research tasks and admin settings
- direct Research and Admin entry points
- no fake operational counters, fake queues, fake runs, or evidence panels

The current implementation uses static contract data copied from tenant
fixtures and deployment gates. Runtime mutation paths must be wired only after
the Liquisto Control API and Hetzner runtime endpoints are explicitly scoped and
validated.

## Local Validation

```powershell
npm --prefix apps/liquisto-workbench run lint
npm --prefix apps/liquisto-workbench run build
```
