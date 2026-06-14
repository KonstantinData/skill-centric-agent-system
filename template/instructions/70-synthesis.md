---
name: scas-synthesis
version: "0.1.0"
kind: instruction
description: Instruction for SCAS strategic synthesis after domain packages complete.
triggers:
  - strategic synthesis
  - opportunity assessment
  - negotiation relevance
  - cross-domain consistency
inputs:
  - RuntimeBrief
  - admitted domain packages
  - synthesis context
outputs:
  - synthesis payload
  - back requests
  - opportunity assessment
  - negotiation relevance
required_tools:
  - read_report_segment
  - request_department_followup
  - finalize_synthesis
optional_tools: []
knowledge_scopes:
  - synthesis_context
  - admitted_report_segments
data_scopes:
  - current_run_domain_packages
policies:
  - admitted_segments_only
  - max_one_back_request_per_domain
validators:
  - synthesis_acceptance_gate
tests:
  - synthesis uses diagnostic segments only as risk context
---

# Strategic Synthesis

Run the strategic synthesis phase after domain package work is complete.

## Own

- Read admitted report segments from Company, Market, Buyer, and Contact domain packages.
- Identify cross-domain patterns, contradictions, and gaps.
- Produce opportunity assessment, negotiation relevance, executive summary, risks, next steps, and confidence.
- Request targeted domain follow-up only when a specific segment gap changes the deal path.

## Rules

- Do not conduct new domain research yourself.
- Use `diagnostic` or non-downstream-visible segments only as gap or risk context.
- Think decision-first, not completeness-first.
- Open questions must be deal-critical validation questions, not a raw backlog.
- Next steps must read like a first-meeting playbook with owner, timing, and outcome.

## Completion

Finalize once the synthesis is concrete, specific, actionable, and grounded in admitted domain evidence.
