---
name: scas-quality-gate
version: "0.1.0"
kind: instruction
description: Instruction for deterministic SCAS quality review against task validation rules.
triggers:
  - review research
  - task quality gate
  - validation rules
  - defect class feedback
inputs:
  - task artifact
  - task validation rules
  - objective
  - section payload
outputs:
  - TaskReviewArtifact
  - accepted points
  - rejected points
  - method issue flag
  - revision instructions
required_tools: []
optional_tools: []
knowledge_scopes:
  - task_validation_rules
data_scopes:
  - current_task_payload
policies:
  - deterministic_quality_review
validators:
  - core_supporting_rule_counts
tests:
  - critic distinguishes core failures from supporting gaps
---

# Quality Gate

Run the quality-gate phase for one researched task. Review evidence quality; do not conduct research.

## Own

- Evaluate payload fields against the canonical task validation rules.
- Separate `core` rules from `supporting` rules.
- Surface missing core facts, weak evidence, placeholders, short lists, contract violations, and method defects.
- Produce actionable feedback for research and method-refinement phases.

## Defect Classes

Use these defect classes:
- `missing_core_fact`
- `weak_evidence`
- `placeholder_remaining`
- `list_too_short`
- `method_issue`
- `contract_violation`

## Decision Signal

- Approve only when rules pass and evidence is not weak.
- Treat missing sources as a supporting evidence problem unless the task contract makes sources core.
- Mark `method_issue=true` when rejected points remain and search used no credible external source path.

## Output

Return accepted points, rejected points, missing points, issue messages, evidence strength, rule counts, revision instructions, and a coding brief.
