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
    Run full certification against target environment and record final decision.
11. `P5.11 Expand Production Skill Handler Coverage`
    Expand production-required skill handler coverage beyond the first slices.

## Notes

- Current task lifecycle and assignment details are tracked in Notion.
- Durable release criteria remain in repository policy files.
