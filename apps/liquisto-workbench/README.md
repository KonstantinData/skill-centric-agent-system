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

## Design Surface

The first Cockpit screen is a dense operations workspace, not a marketing page.
It includes:

- Command Center for search and task-oriented entry
- execution phase rail for Intake, Analyze, Compose, Execute, and Validate
- system health tiles for Control API, Runtime Plane, Approvals, and Knowledge
- work queue with owner, due signal, confidence, status, and risk
- Agent Run cards with profile, validator, evidence state, and progress
- Evidence Timeline for audit-friendly review
- Data Source Health table for scope and sync posture

The current implementation uses static contract data. Runtime mutation paths
must be wired only after the Liquisto Control API and Hetzner runtime endpoints
are explicitly scoped and validated.

## Local Validation

```powershell
npm --prefix apps/liquisto-workbench run lint
npm --prefix apps/liquisto-workbench run build
```
