# SCAS Execution Queue

## Purpose

This document mirrors the operational execution queue tracked in Notion for:

- `SCAS - Feature Backlog`
- `SCAS - Issues & Open Questions`

It defines a deterministic processing order and an explicit next start point.
Normative release policy remains in `docs/policies/production-readiness.md`.

## Execution Rule

Before starting each queue item:

1. Check the current status in Notion.
2. Execute the item only when status is `Not started` or `In progress`.
3. Skip items already marked `Done`.

## Next Start Point

1. `FSG-05 Add Invariant-Check Command`
2. `FSG-06 Make Invariant-Check a Required CI Gate`
3. `FSG-07 Implement Shadow-Evaluation Harness for Descriptor/Policy Versions`

## Queue Order

1. Phase 0 / 1 Foundation (`P0.*`, `P1.*`)
2. Phase 2 Runtime Core (`P2*`)
3. Phase 3 Retention (`P3.*`)
4. Phase 4 Runtime Expansion (`P4.*`, `P4.00a`, `P4.07a`)
5. Phase 5 Production Readiness (`P5.*`)
6. Phase 6 Governance (`P6.*`)
7. Formal Safety Guarantees program (`FSG-01` to `FSG-12`)

## Active Tracker Synchronization

While processing backlog items, keep the following issue trackers synchronized:

1. `Operationalize SCAS execution queue and PR monitoring loop`
2. `Track Formal Safety Guarantees rollout (FSG-01..FSG-12)`
3. `Define SCAS Production Release Readiness Gate`
4. `Complete P5.03 Production Release Evidence Workflow`
5. `Resume complete SCAS Feature Backlog execution`

## PR / CI Operating Mode

For each coherent implementation slice:

1. Open a PR.
2. Poll PR checks every 2 minutes.
3. If checks fail, push a fix and continue polling until all required checks are green.
4. Only then close queue items in Notion.
