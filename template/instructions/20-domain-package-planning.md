---
name: scas-domain-package-planning
version: "0.1.0"
kind: instruction
description: Instruction for SCAS domain package planning and finalization responsibilities.
triggers:
  - domain planning
  - investigation plan
  - package finalization
  - task artifact lifecycle
inputs:
  - RuntimeBrief
  - domain assignments
  - current section payload
  - domain policy
  - source profile
outputs:
  - investigation plan
  - completed task decisions
  - DomainPackage
required_tools: []
optional_tools: []
knowledge_scopes:
  - domain_sources
  - domain_policies
  - domain_query_strategies
data_scopes:
  - current_domain_workspace
policies:
  - planning_phase_owns_workflow
  - no_control_plane_inner_loop
validators:
  - domain_package_schema
  - policy_gate
tests:
  - lead starts every mandatory task before finalization
---

# Domain Package Planning

Run the domain package planning phase. Own the workflow and final package for the selected domain.

## Own

- Convert assignments into a structured investigation plan with classification frame, domain hypothesis, task sequence, source priority, and policy requirements.
- Direct research, quality-gate, resolution, and method-refinement phases.
- Ensure every mandatory task is attempted before finalization.
- Respect retry budget and accept supporting gaps when all core rules pass.
- Finalize from stored artifacts; do not silently re-judge tasks already decided.
- Assemble `DomainPackage` with section payload, completed tasks, accepted points, open questions, sources, visual focus, evidence packets, gap candidates, and answer-matrix updates.

## Workflow

1. Start each assigned task with research evidence gathering.
2. Run the quality gate on the task artifact.
3. If core rules fail and retry budget remains, request targeted rework.
4. If method defects block progress, run method refinement for query recovery.
5. If ambiguity remains after retries, run final resolution.
6. Finalize only after all mandatory tasks are accepted, degraded, skipped by condition, or explicitly unresolved.

## Guardrails

- The planning phase is not passive coordination; it owns completion.
- Do not call the control phase for domain-internal revisions.
- Do not hide unresolved gaps. Convert them into explicit open questions and gap candidates.
