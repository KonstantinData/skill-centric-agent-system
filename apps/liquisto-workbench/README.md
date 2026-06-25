# Liquisto Business Platform

Tenant-specific Next.js platform for running Liquisto business processes on
`liquisto.cloud`.

The app is intentionally not a Streamlit replacement and not a SCAS-first
console. Its primary product surface is Liquisto's operational business flow:

- Inventory Intake for ERP exports, material lists, and customer context
- Excess & Shortage Analysis for risk, liquidity, and prioritization
- Initiative Management for decisions, owners, and progress
- Monetization for resale candidates, pricing, and commercial readiness
- Repurposing for unused materials and circular-economy initiatives
- Partner Network for customer, buyer, and repurposing collaboration
- SCAS Workbench as one register for Tasks, Research, Cases, Knowledge, Agent
  Runs, Approvals, Data Sources, Audit, and Admin
- Cloudflare Access identity headers for user context
- Cloudflare Control Plane / Hetzner Runtime Plane boundaries as visible product
  constraints

## Design Surface

The first Cockpit screen is a dense business-process workspace, not a marketing page.
It includes:

- Command Center for inventory, initiative, partner, and SCAS evidence search
- execution phase rail for Import, Analyze, Prioritize, Monetize, and Verify
- process tiles for Liquisto's core operating model
- system health tiles for Control API, Runtime Plane, Approvals, and Knowledge
- work queue with owner, due signal, confidence, status, and risk
- SCAS Workbench register summary with Agent Run cards
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
