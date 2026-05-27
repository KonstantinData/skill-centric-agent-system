---
name: scas-research-quality-loop
description: Execute the SCAS department-internal Lead, Researcher, Critic, Judge, and Coding Specialist loop. Use when Codex needs to transform a department assignment into artifacts, reviews, retry decisions, query refinement, judge resolution, and a finalized DepartmentPackage.
---

# SCAS Research Quality Loop

Use this skill for the department-internal artifact lifecycle.

## Loop

1. Lead builds investigation plan and selects the next mandatory task.
2. Researcher calls `run_research(task_key)` with the exact task key and produces `TaskArtifact`.
3. Critic calls `review_research(task_key)` and produces `TaskReviewArtifact`.
4. Lead decides:
   - all core rules pass: accept and move on
   - core failures and retries remain: retry with targeted revision
   - method issue: call Coding Specialist first
   - retry exhausted: call Judge
5. Coding Specialist returns a bounded query strategy token and revision focus.
6. Judge returns final accepted, degraded, or closed-unresolved decision.
7. Lead finalizes the package from stored artifacts.

## Artifact Rules

- Store every attempt, not only the latest result.
- Keep accepted points stable during revision.
- Convert unresolved task gaps into explicit open questions.
- Generate evidence packets, gap candidates, and answer-matrix updates for downstream readiness.

## Budget Rules

- Do not spend more than the configured retry budget on a single task.
- Do not skip mandatory tasks before at least one genuine attempt unless a task-router run condition blocks the task.
- Prefer complete coverage with documented gaps over perfect depth on one task.

## Select With

Instructions:
- `template/instructions/20-department-lead.md`
- `template/instructions/30-research-worker.md`
- `template/instructions/40-critic-quality-gate.md`
- `template/instructions/50-judge-resolution.md`
- `template/instructions/60-coding-specialist-query-refinement.md`
