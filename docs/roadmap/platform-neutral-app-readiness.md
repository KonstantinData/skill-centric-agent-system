# Platform-Neutral App Readiness Backlog

## Purpose

This backlog converts the KHH workbench scope change into a delivery plan. The
goal is to prevent a future rewrite when a native iOS/Android app is introduced.

The target is platform-neutral readiness, not immediate native app shipment.

## Scope Baseline

Current state:

- `apps/khh-workbench` is a responsive Next.js web shell consuming shared KHH
  domain, client, state, and headless UI contracts while preserving desktop
  shell rendering.
- `apps/khh-mobile-proof` is an Expo Router iOS proof shell consuming the same
  shared contracts and explicit native adapter policies.
- `packages/tenant-workbench-domain`, `packages/tenant-workbench-client`, and
  `packages/tenant-workbench-ui` provide the first shared package boundary.
- KHH tenant identity, deployment, and privacy boundaries are versioned.
- UI copy and feature structure are no longer owned directly by Next.js
  components.
- `packages/tenant-workbench-client` now owns auth sessions, tenant scope
  validation, query caching, optional read-only offline summary storage, API
  transport boundaries, and fail-closed write-intent guards.
- `packages/tenant-workbench-ui` now owns design tokens, view models, headless
  component contracts, and web/native adapter plans without importing platform
  renderers.

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

Status: implemented for the KHH foundation slice.

Deliverables:

- Workspace package scaffold for shared tenant workbench code. Done.
- Shared KHH domain/navigation/privacy definitions. Done.
- Platform-neutral API/state client with auth session abstraction, tenant scope
  validation, query cache, API transport boundary, offline summary store, and
  fail-closed write-intent guard. Done for the read-only KHH foundation slice.

Acceptance:

- Web shell imports shared domain definitions.
- State client has tests for tenant context, auth errors, offline-safe failure,
  and data-minimization boundaries.

### M3: Shared UI And Web Shell Migration

Estimate: 6.0 days.

Status: partially implemented.

Deliverables:

- Shared UI design tokens, view models, headless component contracts, and
  web/native adapter plans. Done for navigation, dashboard, quick actions, and
  section surfaces.
- KHH web shell migrated from web-only feature composition to shared
  UI/domain/client contracts while keeping Next.js routing, CSS, icon, table,
  sidebar, and dense desktop layout adapters in the web shell.

Acceptance:

- Web build and lint pass.
- KHH UI tests prove no visible foreign tenant markers and no master-data UI.
- Responsive web behavior remains intact after shared component migration.

### M4: Native Proof And Gates

Estimate: 3.5 days.

Status: partially implemented.

Deliverables:

- Minimal Expo/native shell proof that imports shared domain/state/UI contracts.
  Done for an Expo Router proof shell.
- Contract tests prevent web-only APIs from entering shared packages. Done for
  domain, client, and UI import boundaries.
- Native auth/offline/push/permission adapters exist for handoff validation,
  tenant-scoped storage keys, read-only offline summaries, default-denied push
  opt-in, and default-denied permissions. Production device integration and
  simulator evidence remain release-gate work.

Acceptance:

- Native shell can render the KHH Heute surface from shared package data.
- No production native release claim is made until auth, offline, push, and
  permission contracts have implementation evidence.

Known residual risk:

- `npm audit --omit=dev` currently reports `uuid@7.0.3` through the native
  proof tooling path `expo -> @expo/config-plugins -> xcode -> uuid`. This is
  not on the KHH web cockpit production path and the web app does not ship the
  Expo/Cordova build toolchain. Treat it as `needs_review` for native build
  tooling before any real iOS production release.
- Do not use `npm audit fix --force` or a blind `uuid` override to clear this
  finding. The force fix proposes an Expo downgrade, and an override must first
  be validated with Expo prebuild, iOS build, and Simulator checks on a Mac.

## Blocking Decisions

- Select the workspace/package manager strategy for JS/TS apps.
- Decide whether production native secure storage should use Expo SecureStore
  directly or a project wrapper. The current proof uses a backend interface.
- Collect iOS Simulator visual smoke evidence for the Expo Router shell.

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
  and denies write intents until mutations are explicitly implemented. It also
  exposes auth session, query cache, API transport, and offline summary store
  contracts.
- `packages/tenant-workbench-ui` exposes platform-neutral view models, design
  tokens, headless component contracts, and web/native adapter plans without
  DOM, Next.js, Expo, or React Native imports.
- `apps/khh-workbench` consumes the shared contracts and keeps web-specific
  routing, images, CSS, and icon rendering in the shell.
- `apps/khh-mobile-proof` typechecks as an Expo Router iOS proof shell with
  explicit auth handoff, tenant-scoped storage, offline summary, push opt-in,
  and permission gate adapters.
- The tenant deploy workflow treats `auth_mode=required` public checks as
  successful only on Cloudflare Access redirect or 403.
