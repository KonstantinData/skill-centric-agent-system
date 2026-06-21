# SOTA 2026 Tenant CRM Web App Standard

## Purpose

This document defines the non-negotiable product and UX baseline for SCAS
tenant CRM and operations web apps.

The standard applies to every tenant-specific CRM UI, including
`es-daskuechenhaus.de`. Tenant-specific branding, terminology, workflows, and
skill packages may differ, but the quality bar does not.

## Product Principles

### Outcome-first cockpit

The first screen must answer operational control questions before it shows raw
data:

- What is critical now?
- What blocks revenue, service, delivery, or customer trust?
- What needs a decision today?
- Which work has no owner, next step, or customer/case assignment?

The cockpit must not be a broad report page or a repository documentation
surface. It should show a small number of prioritized, clickable operational
signals and route detail work to dedicated workspaces.

### SCAS-native controlled assistance

AI-native behavior is provided by SCAS, not by an unbounded generic assistant.

For a CRM task, SCAS must follow the normal control path:

```text
task analysis
-> registry discovery
-> scoring
-> policy filtering
-> dependency graph validation
-> immutable runtime profile validation
-> execution with validators and audit evidence
```

The UI may surface recommendations, proposed next steps, classifications, or
draft actions only when the user can see the status, reason, and confirmation
path. The user must be able to accept, edit, reject, or inspect SCAS-supported
actions before they create tenant-side effects unless a narrower tenant policy
explicitly allows automation.

### Command center

Modern CRM work is driven by fast commands and scoped search, not only by
static navigation. A tenant CRM UI should provide:

- role-derived navigation,
- global search or scoped search entry points,
- quick actions,
- notifications or work queues,
- saved views where they materially reduce repeated filtering,
- command entries for SCAS-supported workflows.

### Dense, calm enterprise UI

The interface should be dense enough for repeated operational work and calm
enough for fast scanning:

- stable side navigation,
- compact status and risk bands,
- lists, tables, drawers, and detail pages for work surfaces,
- inline actions for common operations,
- empty states that guide the next valid action,
- visible audit/history surfaces where business state changes.

Avoid marketing-style heroes, decorative card-heavy layouts, demo panels,
documentation hints, and one-off tenant UI copy embedded in generic runtime
code.

### Tenant-specific design system

Every tenant must have its own explicit UI profile. A tenant may share runtime
components with other tenants, but it must not inherit another tenant's brand,
assets, terminology, navigation, or skill package bindings.

The tenant UI profile must declare:

- active experience standard,
- tenant-owned brand assets,
- tenant theme tokens,
- role-filtered workspace/navigation areas,
- command center surfaces,
- tenant CRM terminology,
- SCAS skill package bindings.

CRM skill packages must follow
`docs/policies/scas-crm-skill-pack-contract.md`. A UI binding may expose a
package in the command center, but it must not grant runtime authority outside
the normal SCAS composition path.

Missing tenant assets, skill package bindings, or workspace definitions must
fail closed or degrade to a neutral, explicitly unbranded state. They must not
fall back to another tenant.

### Auditability and isolation

Customer, email, calendar, task, and case runtime data remains tenant-local.
Cloudflare is the access/control plane; production CRM runtime data remains on
the tenant's runtime plane, such as Hetzner PostgreSQL for Daskuechenhaus.

Every side-effecting SCAS-supported CRM action must be attributable to tenant,
principal, role/membership context, source task, selected skill package, and
validated action result.

## Acceptance Criteria

A tenant CRM web app is SOTA 2026 compliant when:

1. The tenant registry `ui_profile.experience_standard` is
   `sota-2026-tenant-crm`.
2. Tenant assets and theme tokens are loaded only from the active tenant
   profile.
3. Workspace visibility and admin access derive from tenant-local roles.
4. The cockpit is outcome-first and routes detail work to workspaces.
5. Command center surfaces exist for search, quick actions, notifications or
   work queues, and SCAS-supported CRM actions when the tenant enables them.
6. SCAS skill packages are declared per tenant and selected through the normal
   registry/composer control path.
7. Recommendations and automated actions expose human-visible status, reason,
   and audit evidence.
8. Tests cover tenant profile schema, fixture examples, and fail-closed
   isolation for UI profiles, assets, data scopes, and skill packages.

## Definition of Done

The SOTA 2026 tenant CRM tool work is done only when all parent and subtask
outcomes are complete:

1. The SOTA CRM web app standard is versioned in the repository and referenced
   by tenant registry examples.
2. Each tenant has an explicit `ui_profile` for assets, theme, navigation,
   command center surfaces, terminology, and SCAS skill package bindings.
3. Tenant-owned assets are loaded through a tenant-scoped path and never fall
   back to another tenant.
4. The tenant app shell is a professional CRM command center with outcome-first
   cockpit, role-filtered navigation, search or command entry points, work
   queues, quick actions, and detail workspaces.
5. SCAS CRM skill packages are defined per tenant and selected only through
   registry discovery, scoring, policy filtering, dependency validation, and
   immutable runtime profile validation.
6. Side-effecting CRM actions expose status, reason, confirmation path, and
   audit evidence before or after execution according to tenant policy.
7. Visual, responsive, accessibility, schema, contract, isolation, and security
   gates pass for the changed tenant surfaces.
8. Documentation, examples, tests, and Notion task tracking are reconciled
   before handoff or merge.

## Non-goals

- Build a separate multi-agent CRM runtime.
- Let a tenant UI self-grant skills, tools, data scopes, policies, validators,
  memory scopes, or knowledge scopes.
- Treat `es-daskuechenhaus.de` as a simplified exception to the CRM standard.
- Store live CRM runtime records in Cloudflare D1.
