# ADR-0012: Platform-Neutral Tenant Workbench Architecture

## Status

Accepted

## Date

2026-06-27

## Context

The first KHH workbench implementation is a responsive Next.js web app. The
product direction now requires tenant workbench development to be platform
neutral from the start so that later native iOS/Android delivery does not
require a second product implementation or a full UI rewrite.

This affects all tenant-facing workbench surfaces, starting with
`tenant_kinderhaus` on `kinderhaus-heuschrecken.cloud`.

## Decision

Tenant workbench development must move to a platform-neutral app architecture
before additional KHH feature depth is added.

The target architecture is:

- a shared product domain package for tenant workbench models, copy keys,
  workflow definitions, permissions, and validation helpers;
- a shared platform-neutral API and state client consumed by web and native
  shells;
- shared UI primitives and feature components that can render on web and native
  through React Native for Web / Expo-compatible boundaries or an equivalent
  cross-platform component contract;
- thin platform shells for web and native navigation, auth handoff, storage,
  push, device permissions, and deployment/runtime wiring;
- explicit native target contracts for auth, navigation, offline behavior, push
  notifications, and device permissions before native implementation begins.

The current Next.js KHH workbench may remain as a short-lived delivery shell,
but new tenant workbench capability work should target shared packages first.

## Consequences

Positive:

- Web and native product behavior can share models, state transitions, copy
  semantics, validation, and most UI composition.
- Native migration risk is addressed before the cockpit grows deeper.
- KHH privacy and data-minimization rules can be enforced in shared product and
  state layers instead of only in web components.

Costs:

- The current KHH workbench must be refactored before more feature build-out.
- Build, lint, test, and deployment workflows must support the shared package
  boundary and at least one web shell.
- Native auth, offline, push, and device permission contracts must be specified
  even before native app code is shipped.

Non-goals:

- This does not change the SCAS runtime into a multi-agent system.
- This does not authorize broad mobile device access. Device permissions stay
  explicit, role-gated, and fail closed.
- This does not require shipping native apps in the current sprint.

## Acceptance Criteria

- A platform-neutral workbench roadmap exists in repository documentation.
- KHH workbench feature work is split into shared UI, shared API/state, and
  native target contract slices.
- The web shell consumes shared domain and state contracts.
- Native app readiness is measured by executable or reviewable contracts, not
  by claims in chat or issue text.
