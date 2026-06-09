---
name: scas-repo-docs-consistency-governor
description: Ensure SCAS repository documentation stays consistent with code, tests, contracts, and governance changes before commit and PR merge.
---

# SCAS Repo Docs Consistency Governor

## Outcome

Prevent documentation drift in SCAS without duplicating durable technical
documentation in Notion.

## Mandatory Gate

Run this gate:
- when creating a SCAS task, subtask, follow-up, or blocker entry,
- when discovering an inline subtask during implementation,
- before commit,
- before PR creation/update,
- before merge readiness confirmation,
- before final repository handoff.

## Notion-Backed Documentation Scope

Use the active SCAS Notion task as the documentation scope and change-fact
ledger:

- `SCAS - Issues & Open Questions` records active work, blockers, and
  documentation impact decisions.
- `SCAS - Feature Backlog` records planned or completed feature slices when
  the work is backlog-backed.
- Notion records the task lifecycle, scope, acceptance criteria, branch/PR
  context, expected documentation impact, change facts, and docs
  reconciliation outcome.
- Repository files remain the durable source of truth for architecture,
  contracts, policies, runbooks, schemas, examples, release criteria, and
  operational commands.
- Do not duplicate durable technical documentation into Notion comments.

## Documentation Impact Classification

Classify documentation impact immediately when creating or discovering any
SCAS task at any level:

- main task,
- subtask,
- sub-subtask,
- follow-up,
- blocker task,
- Feature Backlog entry,
- Issues & Open Questions entry.

Use one of these values:

- `expected`: durable repo documentation is likely to change.
- `not expected`: no durable repo documentation impact is expected.
- `unknown`: impact cannot be decided yet; resolve it before implementation
  continues or treat it as `expected` for planning.

For every classification, record:

- the reason,
- candidate documentation files to update or verify,
- documentation acceptance criteria,
- whether the impact belongs to a standalone task or is merged into the parent
  task's documentation scope.

If an inline subtask stays inside the current main task, update the parent
task's documentation scope instead of creating duplicate Notion records. If a
subtask is split into its own Notion task, classify its own documentation
impact there.

## Check Scope

- `README.md`
- `docs/`
- `schemas/`
- `policies/`
- `migrations/`
- runtime/composition contract docs and runbooks
- `examples/`
- `.github/`
- `workers/control-api/`
- `src/skill_centric_agent_system/`

## Decision

- Locate the active SCAS issue/backlog task and read the initial
  Documentation Impact classification.
- Read documentation impact updates from inline subtasks, standalone subtasks,
  follow-ups, and blockers.
- Compare the branch against the PR base, usually `origin/main...HEAD`.
- Convert the Notion scope plus Git diff into concrete change facts.
- Map each change fact back to the expected candidate documentation files and
  any newly discovered durable documentation surfaces.
- If durable behavior, contracts, setup, operations, governance, roadmap
  status, or examples changed, update the affected repo docs in the same branch.
- If an expected documentation file does not need to change, reclassify it with
  a specific rationale in the Notion reconciliation comment.
- Missing required docs updates are blocking and must be handled before PR
  completion or final handoff unless the user explicitly accepts an incomplete
  PR state.

## Comment Formats

Use `docs/runbooks/notion-issue-tracking.md` as the canonical source for
Documentation Impact, Subtask Discovered, Change Fact, and Docs Reconciliation
comment formats. This skill defines when to run the gate and how to decide;
the runbook defines the exact Notion comment shape.
