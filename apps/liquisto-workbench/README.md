# Liquisto Workbench

Tenant-specific Next.js workbench for running Liquisto on the existing SCAS
architecture. In product terms, this is the Liquisto SCAS architecture surfaced
as an operations application.

The app is intentionally not a Streamlit replacement. It exposes the SCAS
operating model as a user-facing product surface:

- Cockpit for operational posture and queue pressure
- Tasks, Research, Cases, and Knowledge as business workspaces
- Agent Runs, Approvals, Data Sources, Audit, and Admin as governance surfaces
- Cloudflare Access identity headers for user context
- Cloudflare Control Plane / Hetzner Runtime Plane boundaries as visible product
  constraints

The current implementation is a UI shell with static contract data. Runtime
mutation paths must be wired only after the Liquisto Control API and Hetzner
runtime endpoints are explicitly scoped and validated.

## Local Validation

```powershell
npm --prefix apps/liquisto-workbench run lint
npm --prefix apps/liquisto-workbench run build
```
