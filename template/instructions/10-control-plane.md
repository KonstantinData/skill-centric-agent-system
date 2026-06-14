---
name: scas-control-plane
version: "0.1.0"
kind: instruction
description: Instruction for SCAS control-plane responsibilities in a composed runtime profile.
triggers:
  - intake normalization
  - runtime brief
  - domain routing
  - domain package admission
  - run follow-up routing
inputs:
  - company name
  - web domain
  - normalized domain
  - domain packages
outputs:
  - RuntimeBrief
  - task assignments
  - package admission decision
  - follow-up route
required_tools:
  - website_snapshot
  - search
optional_tools: []
knowledge_scopes:
  - SCAS_standard_scope
data_scopes:
  - current_run_intake
policies:
  - supervisor_no_domain_interpretation
validators:
  - runtime_brief_schema
  - domain_package_admission_gate
tests:
  - control phase creates a routable brief and never performs domain retry decisions
---

# Control Plane

Run the SCAS control-plane phase only for orchestration decisions inside the current single-agent runtime profile.

## Own

- Normalize intake and domain into a validated company briefing.
- Build the `RuntimeBrief` with identity confidence, industry confidence, evidence items, missing evidence, fetch audit, readiness, and routing gaps.
- Translate the standard SCAS mandate into task assignments through the task contract.
- Coordinate domain package execution order: Company and Market first, Buyer after Step 1, Contact after Buyer.
- Apply package admission decisions: `accepted`, `accepted_with_gaps`, or `rejected`.
- Route follow-up questions to the responsible domain package or synthesis path.

## Do Not Own

- Do not interpret domain facts.
- Do not review evidence quality inside a domain package workflow.
- Do not request control-plane revisions from the domain package loop.
- Do not override quality-gate or resolution decisions.

## Admission Rule

Accept a package only when it has substantive section payload, completed tasks, accepted or degraded task outcomes, and no hard policy-gate blocker. Preserve rejected packages as diagnostics but do not expose them as downstream truth.

## Output Discipline

Return structured control-plane outputs. Keep uncertainty explicit through readiness status, routing gaps, missing evidence, and admission reasons.
