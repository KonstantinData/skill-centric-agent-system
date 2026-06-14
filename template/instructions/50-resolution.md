---
name: scas-resolution
version: "0.1.0"
kind: instruction
description: Instruction for deterministic SCAS resolution of ambiguous or exhausted tasks.
triggers:
  - judge decision
  - retry exhausted
  - borderline task quality
  - accepted with gaps
inputs:
  - critic review
  - task key
  - section
outputs:
  - TaskDecisionArtifact
  - task status
  - confidence
  - open questions
required_tools: []
optional_tools: []
knowledge_scopes:
  - task_validation_rules
data_scopes:
  - current_task_review
policies:
  - judge_no_skipped_status
validators:
  - three_outcome_gate
tests:
  - judge never converts no-core-evidence tasks into accepted tasks
---

# Task Resolution

Run the final deterministic resolution phase for a task after retries are exhausted or ambiguity remains.

## Outcomes

Use three practical outcomes:
- `accepted`: all core rules passed; supporting evidence determines confidence.
- `accepted_with_gaps`: partial core passed; output is usable but incomplete.
- `closed_unresolved`: no core evidence passed; preserve the gap visibly.

Map these to task status:
- `accepted` -> `accepted`
- `accepted_with_gaps` -> `degraded`
- `closed_unresolved` -> `degraded`

Do not emit `skipped`; skipped is a task-router status before execution.

## Decision Principles

- All core rules passed: accept, even when supporting evidence is incomplete.
- Some core rules passed: keep as degraded with failed core messages as open questions.
- No core rules passed: close unresolved with low confidence; do not silently promote.

## Output

Return decision, task status, reason, confidence, and bounded open questions.
