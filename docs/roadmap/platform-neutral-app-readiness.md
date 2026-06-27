# Platform-Neutral App Readiness Backlog

## Purpose

This backlog converts the KHH workbench scope change into a delivery plan. The
goal is to prevent a future rewrite when a native iOS/Android app is introduced.

The target is platform-neutral readiness, not immediate native app shipment.

## Scope Baseline

Current state:

- `apps/khh-workbench` is a responsive Next.js web shell consuming shared KHH
  domain, client, and UI view-model contracts.
- `apps/khh-mobile-proof` is a minimal Expo/iOS proof shell consuming the same
  shared contracts.
- `packages/tenant-workbench-domain`, `packages/tenant-workbench-client`, and
  `packages/tenant-workbench-ui` provide the first shared package boundary.
- KHH tenant identity, deployment, and privacy boundaries are versioned.
- UI copy and feature structure are no longer owned directly by Next.js
  components, but deeper shared UI component migration and real API adapters
  remain open.

Required target state:

- shared tenant workbench domain package;
- shared API/state client;
- shared UI primitives and feature components usable by web and native shells;
- documented native auth, navigation, offline, push, and permission contracts;
- web shell migrated to consume the shared packages.

## Estimation Model

Use implementation days as planning units. One implementation day means one
focused engineer-day including code, tests, and documentation for the slice.

| Slice | Estimate | Risk | Notes |
| --- | ---: | --- | --- |
| Architecture decision and target contracts | 1.0 day | Medium | ADR, roadmap, package boundaries, acceptance gates. |
| Monorepo/shared package scaffold | 1.5 days | Medium | Package manager/workspace wiring, lint/build/test paths. |
| Shared domain model and navigation definitions | 1.5 days | Medium | KHH sections, copy keys, privacy constraints, workflow metadata. |
| Platform-neutral API/state client | 2.5 days | High | Auth context, request adapters, cache/state boundaries, tenant errors. |
| Shared UI primitives and feature components | 4.0 days | High | Replace web-only cards/nav/status components with cross-platform contracts. |
| Web shell migration | 2.0 days | Medium | Next.js shell consumes shared domain/state/UI packages. |
| Native target architecture contracts | 1.5 days | Medium | Auth, navigation, offline, push, device permission specs. |
| Expo/native shell proof scaffold | 2.0 days | High | Minimal shell proves package reuse without production release. |
| Validation and release gates | 1.5 days | Medium | Tests for shared packages, web shell, privacy, and native contract drift. |

Planning total: 17.5 implementation days.

Recommended sprint allocation: 18 implementation days plus review buffer.

## Milestone Plan

### M1: Native-Ready Architecture Contract

Estimate: 2.5 days.

Deliverables:

- ADR-0012 accepted.
- This roadmap/backlog exists.
- Native target contracts cover auth, navigation, offline, push, and device
  permissions.

Acceptance:

- No new KHH feature work bypasses the shared architecture path.
- Review can answer where shared domain, shared state, shared UI, and platform
  shells live.

### M2: Shared Workbench Foundation

Estimate: 5.5 days.

Status: partially implemented.

Deliverables:

- Workspace package scaffold for shared tenant workbench code. Done.
- Shared KHH domain/navigation/privacy definitions. Done.
- Platform-neutral API/state client with web adapter. Initial contract done;
  real API adapters and richer state/error coverage remain.

Acceptance:

- Web shell imports shared domain definitions.
- State client has tests for tenant context, auth errors, offline-safe failure,
  and data-minimization boundaries.

### M3: Shared UI And Web Shell Migration

Estimate: 6.0 days.

Deliverables:

- Shared UI primitives for status chips, panels, action rows, navigation
  entries, and workbench sections.
- KHH web shell migrated from web-only feature composition to shared UI/domain
  packages.

Acceptance:

- Web build and lint pass.
- KHH UI tests prove no visible foreign tenant markers and no master-data UI.
- Responsive web behavior remains intact after shared component migration.

### M4: Native Proof And Gates

Estimate: 3.5 days.

Status: partially implemented.

Deliverables:

- Minimal Expo/native shell proof that imports shared domain/state/UI contracts.
  Done for proof shell.
- Contract tests prevent web-only APIs from entering shared packages. Done for
  domain and UI import boundaries.
- Native auth/offline/push/permission contracts are linked from release gates.
  Documented in the proof shell and client contracts; production release gates
  remain open.

Acceptance:

- Native shell can render the KHH Heute surface from shared package data.
- No production native release claim is made until auth, offline, push, and
  permission contracts have implementation evidence.

## Blocking Decisions

- Select the workspace/package manager strategy for JS/TS apps.
- Decide whether the shared UI layer uses Expo/React Native for Web directly or
  an intermediate component contract with platform adapters.
- Decide whether native offline storage is scoped to read-only cached summaries
  first or includes queued write intents behind explicit approvals.

## Current Sprint Recommendation

Pull M1 and the start of M2 into the current sprint. Do not deepen KHH feature
surfaces until the shared package boundary and state client are in place.

Minimum current-sprint acceptance:

- ADR and roadmap merged.
- Shared package scaffold exists.
- KHH navigation/privacy/domain definitions are moved out of the Next.js app.
- API/state client interface is specified and has initial tests.

## Implemented Foundation Evidence

- Root npm workspaces include `packages/*` and `apps/khh-mobile-proof`.
- `packages/tenant-workbench-domain` has no React, Next.js, DOM, or lucide
  dependency.
- `packages/tenant-workbench-client` fails closed on tenant/area scope mismatch
  and denies write intents until mutations are explicitly implemented.
- `packages/tenant-workbench-ui` exposes platform-neutral view-model contracts
  without DOM or Next.js imports.
- `apps/khh-workbench` consumes the shared contracts and keeps web-specific
  routing, images, CSS, and icon rendering in the shell.
- `apps/khh-mobile-proof` typechecks as a minimal Expo/iOS proof shell.
- The tenant deploy workflow treats `auth_mode=required` public checks as
  successful only on Cloudflare Access redirect or 403.
