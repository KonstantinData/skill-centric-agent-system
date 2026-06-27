# Documentation Index

This repository uses `docs/` as an operational documentation surface, not only as an archive.

## Folder Model

- `docs/policies/`: binding rules, contracts, governance criteria, and security boundaries.
- `docs/runbooks/`: executable process guidance for operations, gates, and lifecycle tasks.
- `docs/reference/`: technical orientation material and implementation-facing reference docs.
- `docs/roadmap/`: execution sequencing and prioritized delivery queues.
- `docs/adr/`: architecture decision records (durable decision history).
- `operations/staging-tasks/`: committed, non-secret real task files approved for
  supervised productive staging operations.

## Policies

- `docs/policies/contracts.md`
- `docs/policies/module-contracts.md`
- `docs/policies/runtime-contract.md`
- `docs/policies/tenant-access-contract.md`
- `docs/policies/intent-transition-gates.md`
- `schemas/transition-evidence.schema.json`
- `scripts/runtime/scan_transition_signals.py`
- `policies/runtime/capability-delta-transition-policy.json`
- `examples/evaluations/intent-transition-golden-traces.json`
- `policies/runtime/intent-transition-shadow-thresholds.json`
- `policies/runtime/structured-evidence-extraction-decision.json`
- `docs/policies/semantic-drift-guard.md`
- `docs/policies/hooks-usage-model.md`
- `docs/policies/skill-handler-version-policy.md`
- `docs/policies/production-skill-instruction-packs.md`
- `docs/policies/data-governance.md`
- `docs/policies/environment-separation.md`
- `docs/policies/infrastructure-boundary.md`
- `docs/policies/review-gates.md`
- `docs/policies/production-readiness.md`
- `docs/runbooks/github-governance-drift.md`
- `docs/policies/threat-model.md`
- `docs/policies/formal-safety-invariants.md`
- `docs/policies/formal-safety-change-type-matrix.md`
- `docs/policies/shadow-evaluation-harness.md`
- `docs/policies/shadow-regression-thresholds.md`
- `docs/policies/automatic-rollback-rules.md`
- `docs/policies/incident-locked-regressions.md`
- `docs/policies/error-taxonomy.md`
- `docs/policies/sota-2026-target-profile.md`

## Runbooks

- `docs/runbooks/runtime-preflight.md`
- `docs/runbooks/runtime-live-dev-e2e.md`
- `docs/runbooks/operations-runbook.md`
- `docs/runbooks/first-productive-agent-operation.md`
- `docs/runbooks/staging-provisioning-checklist.md`
- `docs/runbooks/scas-cloudflare-token-structure.md`
- `docs/runbooks/liquisto-tenant-dns-evidence.md`
- `docs/runbooks/liquisto-workbench-deployment.md`
- `docs/runbooks/daskuechenhaus-tenant-onboarding.md`
- `docs/runbooks/daskuechenhaus-tenant-admin-bootstrap.md`
- `docs/runbooks/es-daskuechenhaus-protected-site.md`
- `docs/runbooks/liquisto-tenant-admin-bootstrap.md`
- `docs/runbooks/liquisto-tenant-release-gate.md`
- `docs/runbooks/liquisto-tenant-rollback-deprovisioning.md`
- `docs/runbooks/post-merge-lifecycle.md`
- `docs/runbooks/notion-issue-tracking.md`

## Roadmap

- `docs/roadmap/scas-execution-queue.md`
- `docs/roadmap/infrastructure-implementation-status.md`
- `docs/roadmap/platform-neutral-app-readiness.md`
- `docs/roadmap/production-readiness-backlog.md`

## Reference

- `docs/reference/architecture.md`
- `docs/reference/memory-architecture.md`
- `docs/reference/runtime-api.md`
- `docs/reference/registries.md`
- `docs/reference/repository-roadmap.md`
- `docs/reference/cloudflare/control-api.md`

## Apps

- `apps/dkh-crm/`: DKH CRM Next.js app served behind Cloudflare Access at
  `es-daskuechenhaus.de` / `www.es-daskuechenhaus.de`.
- `apps/liquisto-workbench/`: Liquisto Workbench Next.js app for
  `liquisto.cloud`. It exposes product-facing Research and Admin entry points
  while keeping SCAS architecture, tenant model details, runtime composition,
  and governance evidence out of visible user copy.
- `apps/khh-workbench/`: KHH Workbench web shell for
  `kinderhaus-heuschrecken.cloud`. New KHH feature work must move through the
  platform-neutral tenant workbench architecture in ADR-0012 before deeper
  feature build-out.
- `apps/khh-mobile-proof/`: Expo Router iOS proof shell that consumes the same
  KHH shared domain, client, state, and UI contracts as the web shell. It is
  not a production native app.
- `packages/tenant-workbench-domain/`: platform-neutral tenant workbench domain,
  navigation, workflow, privacy, and route contracts.
- `packages/tenant-workbench-client/`: platform-neutral state/API client,
  Cloudflare Access header adapter, auth session abstraction, query cache,
  read-only offline summary store, native auth/offline/push/permission
  contracts, and fail-closed tenant-scope/write-intent checks.
- `packages/tenant-workbench-ui/`: platform-neutral view models, design tokens,
  headless component contracts, and web/native adapter plans for dashboards,
  navigation, and sections. Platform shells adapt these contracts to web or
  native rendering.

## Roadmap

- `docs/roadmap/memory-architecture-backlog.md`
- `docs/roadmap/platform-neutral-app-readiness.md`
- `docs/roadmap/production-readiness-backlog.md`
- `docs/roadmap/scas-execution-queue.md`
