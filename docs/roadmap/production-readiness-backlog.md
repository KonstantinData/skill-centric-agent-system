# Production Readiness Backlog

## Purpose

This document tracks implementation sequencing and progress notes for
production-readiness work.
Normative release gates and evidence rules remain in
`docs/policies/production-readiness.md`.
The cross-phase execution order is tracked in
`docs/roadmap/scas-execution-queue.md`.

## Prioritized Backlog

1. `P5.01 Production Release Readiness Gate`
   Define the gate, keep repository documentation aligned, and keep the gate
   testable.
2. `P5.02 Staging and Production Environment Separation`
   Maintain explicit Cloudflare and Hetzner staging/prod configuration and
   validation.
3. `P5.03 Production Release Evidence Workflow`
   Keep release checks and live gates in a reproducible workflow that writes a
   non-secret evidence summary.
4. `P5.04 Production Skill Handler Runtime`
   Maintain code-backed handler registry and version-pinned runtime dispatch.
5. `P5.05 Controlled Write-Capable Execution Path`
   Keep write adapters behind authorization, approval, policy, audit,
   validation, and rollback controls.
6. `P5.06 Scheduled Runtime Retention Cleanup Automation`
   Keep dry-run-first retention cleanup automation with report artifacts and
   failure signaling.
7. `P5.07 Production Telemetry and Alerting`
   Maintain telemetry and alert coverage for Control Plane and Runtime Plane
   failure modes.
8. `P5.08 Security Hardening and Threat Model Closure`
   Maintain threat-model closure, token-scope checks, and finding remediation
   evidence.
9. `P5.09 Analyzer, Composer, and Human Review Quality Gate`
   Maintain ambiguity handling that routes risky cases to review-required
   profiles.
10. `P5.10 Production Readiness Certification Run`
    Maintain certification against the configured target environment and record
    the release decision with non-secret evidence. Prefer consumed matching CI
    and security governance evidence for the release commit; use explicit
    recheck mode only when the release owner needs fresh broad gate execution.
11. `P5.11 Expand Production Skill Handler Coverage`
    Expand production-required skill handler coverage beyond the first slices.
12. `Post-P5: Define and govern HOOKS usage model`
    Maintain versioned, executable lifecycle hook governance for composition
    and runtime without allowing hooks to grant capabilities or mutate active
    profiles.

## Notes

- Current task lifecycle and assignment details are tracked in Notion.
- Durable release criteria remain in repository policy files.
- P5.10 staging certification-mode evidence is complete for commit
  `5bf301b8c0fdfe6d547c50890c72bbd6a0bf7648`; the certified result is
  `staging-ready`, not `production-ready`.
- First productive agent operation should start in the controlled staging mode
  defined by `docs/runbooks/first-productive-agent-operation.md`.
- Future `prod` claims require prod-specific resources, live evidence, and
  certification under `docs/policies/production-readiness.md`.
