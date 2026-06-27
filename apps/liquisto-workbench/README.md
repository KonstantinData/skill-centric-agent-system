# Liquisto Workbench

Next.js workbench for configured Liquisto capabilities on `liquisto.cloud`.

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

- direct Research and Admin entry points
- no fake operational counters, fake queues, fake runs, or evidence panels

The current implementation uses static contract data copied from tenant
fixtures and deployment gates. Runtime mutation paths must be wired only after
the Liquisto Control API and Hetzner runtime endpoints are explicitly scoped and
validated.

## Product Language Boundary

The Workbench UI must describe user-facing Liquisto capabilities, goals, inputs,
and outputs. It must not expose internal SCAS architecture terms, tenant model
details, runtime profile composition, validator names, policy gates, tool
selection, or isolation mechanics.

Users must not see or infer that other tenants exist. Visible copy should use
product language such as Research, Company Intelligence, Meeting Brief, Market
Signals, Buyer Segments, Evidence, Confidence, and CRM Fields.

Feature cards should describe target use, not internal execution flow. For
example, a Research card may link to a Research page where a pre-meeting
intelligence brief capability explains the intended business use, required
company input, and expected output without naming selected skills, tools,
policies, validators, runtime profiles, or tenant boundaries.

## Local Validation

```powershell
npm --prefix apps/liquisto-workbench run lint
npm --prefix apps/liquisto-workbench run build
```
