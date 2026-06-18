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
- `docs/runbooks/schober-tenant-onboarding.md`
- `docs/runbooks/liquisto-tenant-admin-bootstrap.md`
- `docs/runbooks/liquisto-tenant-release-gate.md`
- `docs/runbooks/liquisto-tenant-rollback-deprovisioning.md`
- `docs/runbooks/streamlit-business-ui-deployment.md`
- `docs/runbooks/post-merge-lifecycle.md`
- `docs/runbooks/notion-issue-tracking.md`

## Roadmap

- `docs/roadmap/scas-execution-queue.md`
- `docs/roadmap/infrastructure-implementation-status.md`
- `docs/roadmap/production-readiness-backlog.md`

## Reference

- `docs/reference/architecture.md`
- `docs/reference/memory-architecture.md`
- `docs/reference/runtime-api.md`
- `docs/reference/registries.md`
- `docs/reference/repository-roadmap.md`
- `docs/reference/cloudflare/control-api.md`

## Apps

- `apps/streamlit_task_intake_ui/`: thin Streamlit Task Intake surface for
  creating runtime-compatible task envelopes and local fixture-backed runtime
  runs.
- `apps/streamlit_business_ui/`: tenant-aware Streamlit Business UI with a
  manual deployment path in `.github/workflows/tenant-ui-deploy.yml`.

## Roadmap

- `docs/roadmap/memory-architecture-backlog.md`
- `docs/roadmap/production-readiness-backlog.md`
- `docs/roadmap/scas-execution-queue.md`
