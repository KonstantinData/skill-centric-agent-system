---
name: scas-synthesis-briefing
description: Run the Strategic Synthesis Department responsibility set from the current SCAS runtime profile. Use when Codex needs to integrate admitted domain packages into Liquisto opportunity assessment, negotiation relevance, executive summary, deal-critical risks, and first-meeting next steps.
---

# SCAS Synthesis Briefing

Use this skill after domain packages are complete and admitted for downstream synthesis.

## Source Runtime

- `src/agents/synthesis_department.py`
- `src/orchestration/synthesis_runtime.py`
- `src/orchestration/synthesis.py`
- `src/orchestration/envelope.py`

## Workflow

1. Read Company, Market, Buyer, and Contact report segments.
2. Respect admission visibility. Use diagnostic segments only as risk or gap context.
3. Identify cross-domain patterns:
   - company pressure plus market context
   - product and asset scope plus buyer routes
   - contact intelligence plus outreach feasibility
   - evidence gaps that would change the deal path
4. Issue at most one targeted back request per department when needed.
5. Finalize opportunity assessment, negotiation relevance, and executive summary.

## Current Tasks

- `liquisto_opportunity_assessment`: decide whether an excess-inventory path is commercially plausible and why.
- `negotiation_relevance`: summarize urgency, pricing power, buyer demand, inventory pressure, and the strongest next meeting angle.

## Quality Bar

The output must be decision-first, concrete, specific, and actionable. Open questions must be deal-critical. Next steps must function as a first-meeting playbook or mutual-action-plan draft.

## Select With

Instructions:
- `template/instructions/70-synthesis-department.md`
- `template/instructions/90-memory-and-tool-boundaries.md`
